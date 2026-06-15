#!/usr/bin/env python3
"""Read-only scanner for Game Asset Hub source project candidates."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SPINE_BINARY_EXTS = {".skel", ".bin"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".pvr", ".pkm", ".ktx"}
TEXT_CONFIG_EXTS = {".json", ".csv", ".txt", ".xml", ".bytes", ".plist", ".asset"}
IGNORE_DIRS = {
    ".git",
    "node_modules",
    "Library",
    "Temp",
    "obj",
    "bin",
    ".gradle",
}
CONFIG_HINTS = re.compile(
    r"(role|hero|card|unit|knight|character|skill|action|battle|effect|eff|spine|manifest|catalog|script|formation)",
    re.IGNORECASE,
)
ROLE_HINTS = re.compile(r"(role|hero|card|unit|knight|character)", re.IGNORECASE)
SKILL_HINTS = re.compile(r"(skill|action|show|battle|script)", re.IGNORECASE)
EFFECT_HINTS = re.compile(r"(effect|eff|fx|particle)", re.IGNORECASE)


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def iter_files(root: Path, max_files: int) -> tuple[list[Path], bool]:
    files: list[Path] = []
    truncated = False
    for current_root, dirs, names in os.walk(root):
      dirs[:] = [name for name in dirs if name not in IGNORE_DIRS]
      for name in names:
          files.append(Path(current_root) / name)
          if len(files) >= max_files:
              return files, True
    return files, truncated


def read_text_sample(path: Path, limit: int = 262144) -> str:
    try:
        data = path.read_bytes()[:limit]
    except OSError:
        return ""
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return ""


def looks_like_spine_json(path: Path) -> bool:
    if path.suffix.lower() != ".json":
        return False
    text = read_text_sample(path, 524288)
    if not text:
        return False
    return all(token in text for token in ('"bones"', '"slots"')) and '"animations"' in text


def parse_atlas_pages(path: Path) -> list[str]:
    text = read_text_sample(path)
    if not text:
        return []
    pages: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or ":" in line or line.startswith("#"):
            continue
        if re.search(r"\.(png|jpg|jpeg|webp|pvr|pkm|ktx)$", line, re.IGNORECASE):
            pages.append(line.replace("\\", "/"))
    return pages


def top_items(paths: list[Path], root: Path, limit: int = 40) -> list[str]:
    return [rel(path, root) for path in sorted(paths, key=lambda p: len(str(p)))[:limit]]


def classify_config(path: Path) -> set[str]:
    value = path.as_posix()
    kinds: set[str] = set()
    if ROLE_HINTS.search(value):
        kinds.add("role")
    if SKILL_HINTS.search(value):
        kinds.add("skill_action")
    if EFFECT_HINTS.search(value):
        kinds.add("effect")
    if CONFIG_HINTS.search(value):
        kinds.add("config")
    return kinds


def build_spine_groups(root: Path, files: list[Path]) -> list[dict[str, Any]]:
    by_dir_stem: dict[tuple[Path, str], dict[str, Any]] = defaultdict(lambda: {
        "skeletons": [],
        "jsonSkeletons": [],
        "atlases": [],
        "pages": [],
    })

    image_by_dir_name = {(path.parent, path.name.lower()): path for path in files if path.suffix.lower() in IMAGE_EXTS}
    atlas_or_binary_keys: set[tuple[Path, str]] = set()

    for path in files:
        suffix = path.suffix.lower()
        key = (path.parent, path.stem)
        if suffix in SPINE_BINARY_EXTS:
            by_dir_stem[key]["skeletons"].append(path)
            atlas_or_binary_keys.add(key)
        elif suffix == ".atlas":
            by_dir_stem[key]["atlases"].append(path)
            atlas_or_binary_keys.add(key)

    for path in files:
        suffix = path.suffix.lower()
        key = (path.parent, path.stem)
        if suffix != ".json":
            continue
        path_text = path.as_posix().lower()
        likely_spine_location = any(token in path_text for token in ("/spine/", "/character/", "/characters/", "/effect/", "/effects/", "/eff/"))
        if (key in atlas_or_binary_keys or likely_spine_location) and looks_like_spine_json(path):
            by_dir_stem[key]["jsonSkeletons"].append(path)

    groups: list[dict[str, Any]] = []
    for (directory, stem), group in by_dir_stem.items():
        if not group["skeletons"] and not group["jsonSkeletons"] and not group["atlases"]:
            continue
        page_refs: list[str] = []
        missing_pages: list[str] = []
        for atlas in group["atlases"]:
            for page in parse_atlas_pages(atlas):
                page_refs.append(page)
                if (atlas.parent, Path(page).name.lower()) not in image_by_dir_name:
                    missing_pages.append(page)
        complete = bool((group["skeletons"] or group["jsonSkeletons"]) and group["atlases"] and page_refs and not missing_pages)
        groups.append({
            "stem": stem,
            "directory": rel(directory, root),
            "skeletons": top_items(group["skeletons"], root, 8),
            "jsonSkeletons": top_items(group["jsonSkeletons"], root, 8),
            "atlases": top_items(group["atlases"], root, 8),
            "atlasPageRefs": sorted(set(page_refs))[:16],
            "missingAtlasPages": sorted(set(missing_pages))[:16],
            "completeForPreview": complete,
        })

    groups.sort(key=lambda item: (not item["completeForPreview"], item["directory"], item["stem"]))
    return groups


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect a source project for Asset Hub ingest candidates.")
    parser.add_argument("source_root", help="APK export or recovered project root to inspect")
    parser.add_argument("--max-files", type=int, default=200000, help="Maximum files to scan")
    parser.add_argument("--limit", type=int, default=80, help="Maximum candidate rows to print per section")
    args = parser.parse_args()

    root = Path(args.source_root).resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Source root is not a directory: {root}")

    files, truncated = iter_files(root, args.max_files)
    suffix_counts = Counter(path.suffix.lower() or "<none>" for path in files)
    spine_groups = build_spine_groups(root, files)

    config_candidates: dict[str, list[str]] = {"role": [], "skill_action": [], "effect": [], "config": []}
    for path in files:
        if path.suffix.lower() not in TEXT_CONFIG_EXTS:
            continue
        kinds = classify_config(path)
        for kind in kinds:
            if len(config_candidates[kind]) < args.limit:
                config_candidates[kind].append(rel(path, root))

    scripts = [
        rel(path, root)
        for path in files
        if path.suffix.lower() in {".js", ".ts", ".lua", ".cs"} and CONFIG_HINTS.search(path.as_posix())
    ][: args.limit]

    image_candidates = [
        rel(path, root)
        for path in files
        if path.suffix.lower() in IMAGE_EXTS and re.search(r"(head|avatar|icon|skill|portrait|stand|role)", path.as_posix(), re.IGNORECASE)
    ][: args.limit]

    complete_spine = sum(1 for group in spine_groups if group["completeForPreview"])
    has_roles = bool(config_candidates["role"])
    has_actions = bool(config_candidates["skill_action"] or scripts)
    has_effects = bool(config_candidates["effect"] or any("effect" in group["directory"].lower() or "eff" in group["directory"].lower() for group in spine_groups))

    report = {
        "sourceRoot": root.as_posix(),
        "fileCount": len(files),
        "truncated": truncated,
        "suffixCounts": dict(sorted(suffix_counts.items(), key=lambda item: (-item[1], item[0]))[:40]),
        "spine": {
            "groupCount": len(spine_groups),
            "completeForPreviewCount": complete_spine,
            "candidates": spine_groups[: args.limit],
        },
        "configCandidates": config_candidates,
        "scriptCandidates": scripts,
        "imageCandidates": image_candidates,
        "ingestSignals": {
            "tierA_roleCatalogLikely": has_roles or bool(image_candidates),
            "tierB_spinePreviewLikely": complete_spine > 0,
            "tierC_actionEffectNeedsAdapter": has_actions and has_effects,
        },
        "recommendation": (
            "Tier C may be possible, but requires project-specific battle script/config adapter."
            if has_actions and has_effects and complete_spine
            else "Tier B may be possible if role-to-Spine mapping can be recovered."
            if complete_spine
            else "Start with Tier A discovery; no complete Spine preview groups were found."
        ),
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

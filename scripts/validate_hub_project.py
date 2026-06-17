#!/usr/bin/env python3
"""Validate Game Asset Hub SQLite rows, published files, and HTTP URLs."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


RELATIVE_FIELD_TABLES = {
    "spine_assets": ["skeleton_path", "json_path", "atlas_path", "pages_json"],
    "effect_assets": ["skeleton_path", "json_path", "atlas_path", "pages_json"],
    "role_images": ["path"],
    "skills": ["icon_path"],
    "asset_paths": ["path"],
}
OLD_PROXY_PATTERNS = ("/external-assets/", "/hub/projects/")
CUTIN_PATH_PREFIX = "spine/cutins/"


def normalize_slashes(value: str) -> str:
    return value.replace("\\", "/")


def join_url(base: str, path: str) -> str:
    return base.rstrip("/") + "/" + normalize_slashes(path).lstrip("/")


def is_http(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def fetch_status(url: str, timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(url, method="HEAD", headers={"Origin": "http://127.0.0.1:5190"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {
                "url": url,
                "ok": 200 <= response.status < 400,
                "status": response.status,
                "cors": response.headers.get("Access-Control-Allow-Origin"),
            }
    except urllib.error.HTTPError as head_error:
        if head_error.code != 405:
            return {"url": url, "ok": False, "status": head_error.code, "error": str(head_error)}
        try:
            request = urllib.request.Request(url, method="GET", headers={"Origin": "http://127.0.0.1:5190"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return {
                    "url": url,
                    "ok": 200 <= response.status < 400,
                    "status": response.status,
                    "cors": response.headers.get("Access-Control-Allow-Origin"),
                    "method": "GET",
                }
        except Exception as get_error:  # noqa: BLE001
            return {"url": url, "ok": False, "status": None, "error": str(get_error)}
    except Exception as error:  # noqa: BLE001
        return {"url": url, "ok": False, "status": None, "error": str(error)}


def fetch_json(url: str, timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            text = response.read().decode("utf-8", "replace")
            data = json.loads(text)
            return {
                "url": url,
                "ok": 200 <= response.status < 400,
                "status": response.status,
                "data": data,
            }
    except urllib.error.HTTPError as error:
        return {"url": url, "ok": False, "status": error.code, "error": str(error)}
    except Exception as error:  # noqa: BLE001
        return {"url": url, "ok": False, "status": None, "error": str(error)}


def query_one(db: sqlite3.Connection, sql: str, params: tuple[Any, ...]) -> sqlite3.Row | None:
    return db.execute(sql, params).fetchone()


def query_count(db: sqlite3.Connection, table: str, project_id: str) -> int:
    row = query_one(db, f"SELECT COUNT(*) AS count FROM {table} WHERE project_id = ?", (project_id,))
    return int(row["count"] if row else 0)


def cutin_asset_predicate(alias: str = "") -> str:
    prefix = f"{alias}." if alias else ""
    return (
        f"(lower(coalesce({prefix}json_path, '')) LIKE '{CUTIN_PATH_PREFIX}%' "
        f"OR lower(coalesce({prefix}skeleton_path, '')) LIKE '{CUTIN_PATH_PREFIX}%')"
    )


def collect_cutin_counts(db: sqlite3.Connection, project_id: str) -> dict[str, int]:
    cutin_predicate = cutin_asset_predicate()
    cutin_assets = query_one(
        db,
        f"SELECT COUNT(*) AS count FROM spine_assets WHERE project_id = ? AND {cutin_predicate}",
        (project_id,),
    )
    normal_spine_assets = query_one(
        db,
        f"SELECT COUNT(*) AS count FROM spine_assets WHERE project_id = ? AND NOT {cutin_predicate}",
        (project_id,),
    )
    cutin_animations = query_one(
        db,
        f"""
        SELECT COUNT(*) AS count
        FROM animations a
        JOIN spine_assets s ON s.project_id = a.project_id AND s.asset_id = a.asset_id
        WHERE a.project_id = ? AND {cutin_asset_predicate("s")}
        """,
        (project_id,),
    )
    cutin_asset_paths = query_one(
        db,
        "SELECT COUNT(*) AS count FROM asset_paths WHERE project_id = ? AND (lower(coalesce(path, '')) LIKE ? OR lower(coalesce(kind, '')) LIKE 'cutin-%')",
        (project_id, f"{CUTIN_PATH_PREFIX}%"),
    )
    return {
        "normalSpineAssets": int(normal_spine_assets["count"] if normal_spine_assets else 0),
        "cutinAssets": int(cutin_assets["count"] if cutin_assets else 0),
        "cutinAnimations": int(cutin_animations["count"] if cutin_animations else 0),
        "cutinAssetPaths": int(cutin_asset_paths["count"] if cutin_asset_paths else 0),
    }


def load_json_array(value: Any) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, list):
        return [str(item) for item in parsed if item]
    return []


def collect_relative_field_errors(db: sqlite3.Connection, project_id: str) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    for table, fields in RELATIVE_FIELD_TABLES.items():
        columns = ", ".join(["id", *fields])
        for row in db.execute(f"SELECT {columns} FROM {table} WHERE project_id = ?", (project_id,)):
            for field in fields:
                value = row[field]
                if not value:
                    continue
                values = load_json_array(value) if field.endswith("_json") else [str(value)]
                for item in values:
                    if is_http(item) or any(pattern in item for pattern in OLD_PROXY_PATTERNS):
                        errors.append({
                            "table": table,
                            "id": str(row["id"]),
                            "field": field,
                            "value": item,
                        })
    return errors


def collect_disk_checks(db: sqlite3.Connection, project_id: str, wwwroot: Path, limit: int) -> dict[str, Any]:
    project_root = wwwroot / project_id
    missing_assets: list[str] = []
    checked_assets = 0
    for row in db.execute("SELECT path FROM asset_paths WHERE project_id = ? ORDER BY id", (project_id,)):
        checked_assets += 1
        path = project_root / "assets" / str(row["path"]).replace("/", "\\")
        if not path.exists() and len(missing_assets) < limit:
            missing_assets.append(str(path))

    missing_catalog: list[str] = []
    checked_catalog = 0
    for table, field in (("role_images", "path"), ("skills", "icon_path")):
        for row in db.execute(f"SELECT {field} AS path FROM {table} WHERE project_id = ? AND {field} IS NOT NULL AND {field} != ''", (project_id,)):
            checked_catalog += 1
            path = project_root / "catalog" / str(row["path"]).replace("/", "\\")
            if not path.exists() and len(missing_catalog) < limit:
                missing_catalog.append(str(path))

    return {
        "projectRoot": str(project_root),
        "checkedAssetPaths": checked_assets,
        "checkedCatalogPaths": checked_catalog,
        "missingAssetPaths": missing_assets,
        "missingCatalogPaths": missing_catalog,
    }


def collect_http_checks(db: sqlite3.Connection, project_id: str, project: sqlite3.Row, origin: str, max_http: int, timeout: float) -> list[dict[str, Any]]:
    urls: list[str] = []
    for row in db.execute("SELECT url FROM asset_paths WHERE project_id = ? ORDER BY id LIMIT ?", (project_id, max_http)):
        if row["url"]:
            urls.append(str(row["url"]))

    catalog_base = str(project["catalog_base_url"] or join_url(origin, f"{project_id}/catalog"))
    remaining = max_http - len(urls)
    if remaining > 0:
        for row in db.execute(
            "SELECT path FROM role_images WHERE project_id = ? UNION ALL SELECT icon_path AS path FROM skills WHERE project_id = ? AND icon_path IS NOT NULL LIMIT ?",
            (project_id, project_id, remaining),
        ):
            if row["path"]:
                urls.append(join_url(catalog_base, str(row["path"])))

    return [fetch_status(url, timeout) for url in urls[:max_http]]


def collect_cutin_api_check(hub_base_url: str, project_id: str, timeout: float) -> dict[str, Any]:
    url = join_url(hub_base_url, f"api/projects/{project_id}/cutins")
    result = fetch_json(url, timeout)
    data = result.pop("data", None)
    if not result.get("ok"):
        return result
    if not isinstance(data, dict) or not isinstance(data.get("roles"), list):
        return {
            **result,
            "ok": False,
            "error": "Expected JSON object with roles array",
        }

    roles = data["roles"]
    asset_count = 0
    animation_count = 0
    role_samples: list[str] = []
    for role in roles:
        if not isinstance(role, dict):
            continue
        role_samples.append(str(role.get("roleSourceId") or role.get("displayName") or ""))
        assets = role.get("assets")
        if not isinstance(assets, list):
            continue
        asset_count += len(assets)
        for asset in assets:
            if isinstance(asset, dict) and isinstance(asset.get("animations"), list):
                animation_count += len(asset["animations"])

    return {
        **result,
        "roleCount": len(roles),
        "assetCount": asset_count,
        "animationCount": animation_count,
        "roleSamples": [sample for sample in role_samples[:10] if sample],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Game Asset Hub project import.")
    parser.add_argument("--db", required=True, help="Path to asset-hub.sqlite")
    parser.add_argument("--project-id", required=True, help="Project id to validate")
    parser.add_argument("--wwwroot", required=True, help="Shared web root, for example \\\\192.168.0.9\\wwwroot")
    parser.add_argument("--origin", default="http://192.168.0.9", help="Expected HTTP origin")
    parser.add_argument("--max-http", type=int, default=50, help="Maximum HTTP URLs to check")
    parser.add_argument("--timeout", type=float, default=5.0, help="HTTP timeout in seconds")
    parser.add_argument("--skip-http", action="store_true", help="Skip HTTP checks")
    parser.add_argument("--hub-base-url", default="", help="Optional Hub server base URL for API smoke checks, for example http://127.0.0.1:5190")
    parser.add_argument("--sample-limit", type=int, default=40, help="Maximum missing-path samples")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")

    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row

    project = query_one(db, "SELECT * FROM projects WHERE id = ?", (args.project_id,))
    errors: list[str] = []
    warnings: list[str] = []
    if not project:
        print(json.dumps({"ok": False, "errors": [f"Project not found: {args.project_id}"]}, indent=2))
        return 1

    expected_asset_base = join_url(args.origin, f"{args.project_id}/assets")
    expected_catalog_base = join_url(args.origin, f"{args.project_id}/catalog")
    if str(project["asset_base_url"]) != expected_asset_base:
        warnings.append(f"asset_base_url differs from default: {project['asset_base_url']}")
    if str(project["catalog_base_url"]) != expected_catalog_base:
        warnings.append(f"catalog_base_url differs from default: {project['catalog_base_url']}")

    relative_errors = collect_relative_field_errors(db, args.project_id)
    if relative_errors:
        errors.append("Relative path fields contain HTTP URLs or old proxy paths")

    disk = collect_disk_checks(db, args.project_id, Path(args.wwwroot), args.sample_limit)
    if disk["missingAssetPaths"]:
        errors.append("Some asset_paths files are missing under wwwroot")
    if disk["missingCatalogPaths"]:
        warnings.append("Some catalog image files are missing under wwwroot")

    http_checks: list[dict[str, Any]] = []
    if not args.skip_http:
        http_checks = collect_http_checks(db, args.project_id, project, args.origin, args.max_http, args.timeout)
        failed = [item for item in http_checks if not item.get("ok")]
        if failed:
            warnings.append(f"{len(failed)} HTTP checks failed")

    counts = {
        "roles": query_count(db, "roles", args.project_id),
        "roleImages": query_count(db, "role_images", args.project_id),
        "skills": query_count(db, "skills", args.project_id),
        "spineAssets": query_count(db, "spine_assets", args.project_id),
        "animations": query_count(db, "animations", args.project_id),
        "assetPaths": query_count(db, "asset_paths", args.project_id),
        "effectAssets": query_count(db, "effect_assets", args.project_id),
        "roleActions": query_count(db, "role_actions", args.project_id),
        "actorCues": query_count(db, "action_actor_cues", args.project_id),
        "motionCues": query_count(db, "action_motion_cues", args.project_id),
        "hitCues": query_count(db, "action_hit_cues", args.project_id),
        "effectCues": query_count(db, "action_effect_cues", args.project_id),
    }
    counts.update(collect_cutin_counts(db, args.project_id))

    cutin_api_check: dict[str, Any] | None = None
    if args.hub_base_url:
        cutin_api_check = collect_cutin_api_check(args.hub_base_url, args.project_id, args.timeout)
        if not cutin_api_check.get("ok"):
            errors.append("Cutins API smoke check failed")
        elif counts["cutinAssets"] > 0 and int(cutin_api_check.get("assetCount") or 0) == 0:
            errors.append("Cutins API returned no assets despite cutin DB rows")

    report = {
        "ok": not errors,
        "projectId": args.project_id,
        "project": {
            "name": project["name"],
            "assetBaseUrl": project["asset_base_url"],
            "catalogBaseUrl": project["catalog_base_url"],
        },
        "counts": counts,
        "disk": disk,
        "relativeFieldErrors": relative_errors[: args.sample_limit],
        "httpChecks": http_checks,
        "cutinApiCheck": cutin_api_check,
        "warnings": warnings,
        "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())

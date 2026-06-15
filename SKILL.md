---
name: asset-hub-project-ingest
description: Use when preparing an APK export or irregular game resource folder for Game Asset Hub ingestion, including role catalogs, Spine character assets, Spine effect assets, action/effect timelines, shared HTTP publishing under \\192.168.0.9\wwwroot, hub-ingest.json creation, SQLite path rules, and validation.
---

# Asset Hub Project Ingest

## Overview

Use this skill to turn an arbitrary game resource dump into a Game Asset Hub "deliverable package". Do not assume the source has `web-character-catalog` or `web-spine-demo`; the stable contract is the destination package, shared HTTP layout, and SQLite path model.

When working inside `H:/game_assets_rebuild/Game_Asset_Hub`, first read `ai-context/README.md` and the latest handoff notes before making ingest decisions.

## Workflow

1. Inspect the source folder without changing it. Prefer `scripts/inspect_source_project.py` to find Spine candidates, atlas/page pairings, role/skill/effect config candidates, and action-script hints.
2. Decide the ingest tier:
   - Tier A: project + role/image metadata only.
   - Tier B: Tier A plus character Spine assets and animation names.
   - Tier C: Tier B plus effect assets, role actions, battle profile, and timeline cues.
3. Build a project-specific adapter plan. Each source project may need its own extractor because APK exports, recovered configs, encryption, naming, and battle scripts vary.
4. Normalize output to `hub-ingest.json`. See `references/data-contract.md`.
5. Publish browser-loadable files to the shared destination layout. See `references/storage-and-publish.md`.
6. Write the package through the remote ingest API when the Hub service is reachable. Use direct SQLite writes only as a local fallback. See `references/api-ingest.md` and `references/db-write-contract.md`.
7. Validate database rows, disk paths, and HTTP URLs with `scripts/validate_hub_project.py`.

## Hard Rules

- Treat the source APK/export folder as read-only unless the user explicitly asks for a derived working copy.
- Do not promise one generic parser for all projects. Write small project adapters that produce the same destination contract.
- Store browser-facing published files under `\\192.168.0.9\wwwroot\<projectId>`.
- Keep `spine_assets`, `effect_assets`, `role_images`, and `skills.icon_path` paths relative. Full HTTP URLs belong in project base URL fields and optionally `asset_paths.url`.
- Do not add display-only offsets for action/effect positioning until the original battle code/config chain has been checked.
- Do not use destructive mirroring such as `robocopy /MIR` unless the target project directory is known to be disposable.

## Reference Map

- `references/data-contract.md`: `hub-ingest.json` destination-object schema.
- `references/storage-and-publish.md`: shared directory layout and HTTP URL rules.
- `references/api-ingest.md`: remote HTTP ingest API contract and examples.
- `references/db-write-contract.md`: SQLite table mapping and path invariants.
- `references/adapter-workflow.md`: source-project adapter workflow and acceptance checks.

## Useful Commands

Inspect a source project:

```powershell
python C:\Users\gaorq\.codex\skills\asset-hub-project-ingest\scripts\inspect_source_project.py H:\game_assets_rebuild\3021_huoying_muyegaoshou
```

Validate an already-ingested project:

```powershell
python C:\Users\gaorq\.codex\skills\asset-hub-project-ingest\scripts\validate_hub_project.py --db H:\game_assets_rebuild\Game_Asset_Hub\data\asset-hub.sqlite --project-id 3021 --wwwroot \\192.168.0.9\wwwroot --origin http://192.168.0.9
```

Post a complete package to a Hub service running on the database host:

```powershell
Invoke-RestMethod -Method Post -ContentType "application/json" -InFile H:\game_assets_rebuild\_hub_ingest\3001\hub-ingest.json -Uri "http://192.168.0.9:5190/api/ingest/projects/3001/replace"
```

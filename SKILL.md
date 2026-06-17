---
name: asset-hub-project-ingest
description: Use when preparing an APK export or irregular game resource folder for Game Asset Hub ingestion, including role catalogs, Spine character assets, cutin close-up Spine assets, Spine effect assets, action/effect timelines, shared HTTP publishing under \\192.168.0.9\wwwroot, hub-ingest.json creation, SQLite path rules, and validation.
---

# Asset Hub Project Ingest

## Overview

Use this skill to turn an arbitrary game resource dump into a Game Asset Hub "deliverable package". Do not assume the source has `web-character-catalog` or `web-spine-demo`; the stable contract is the destination package, shared HTTP layout, and SQLite path model.

For 特写动画, use the English code/API/path term `cutin` / `cutins`. Cutin assets are role-bound Spine preview assets stored with normal `spineAssets` rows and separated by the `spine/cutins/` path prefix.

When working inside `H:/game_assets_rebuild/Game_Asset_Hub`, first read `ai-context/README.md` and the latest handoff notes before making ingest decisions.

## Workflow

1. Inspect the source folder without changing it. Prefer `scripts/inspect_source_project.py` to find character Spine candidates, cutin/tips Spine candidates, atlas/page pairings, role/skill/effect config candidates, and action-script hints.
2. Decide the ingest tier:
   - Tier A: project + role/image metadata only.
   - Tier B: Tier A plus character Spine assets, cutin Spine assets, and animation names.
   - Tier C: Tier B plus effect assets, role actions, battle profile, and timeline cues.
   - Keep character Spine, cutin Spine, reusable effect Spine, and action/effect timeline data as separate decisions even when they come from the same source dump.
3. Build a project-specific adapter plan. Each source project may need its own extractor because APK exports, recovered configs, encryption, naming, and battle scripts vary.
4. Normalize output to `hub-ingest.json` in a unique short-lived workspace under `<sourceRoot>/_temp/asset-hub-ingest/<projectId>-<timestamp>`. See `references/data-contract.md`.
5. Publish browser-loadable files to the shared destination layout. See `references/storage-and-publish.md`.
6. Write the package through the remote ingest API when the Hub service is reachable. Use direct SQLite writes only as a local fallback. See `references/api-ingest.md` and `references/db-write-contract.md`. For Hub replace API implementations, compute normal Spine statistics and cutin Spine statistics separately; never let cutin-only assets affect normal role Spine flags or normal animation summaries.
7. Validate database rows, disk paths, and HTTP URLs with `scripts/validate_hub_project.py`.
8. Delete the ingest workspace only after publishing, writing, and validation all succeed. If any step fails, keep it and report the path for debugging.

## Hard Rules

- Treat source APK/export contents as read-only except for the dedicated `<sourceRoot>/_temp/asset-hub-ingest` workspace, unless the user explicitly asks for another derived working copy.
- Do not promise one generic parser for all projects. Write small project adapters that produce the same destination contract.
- Put temporary ingest packages under `<sourceRoot>/_temp/asset-hub-ingest/<projectId>-<timestamp>` with a unique directory per run.
- Before deleting an ingest workspace, resolve its absolute path and confirm it is inside `<sourceRoot>/_temp/asset-hub-ingest`. Never delete source resources, published `wwwroot` files, or a failed ingest workspace.
- Store browser-facing published files under `\\192.168.0.9\wwwroot\<projectId>`.
- Store cutin Spine files under `\\192.168.0.9\wwwroot\<projectId>\assets\spine\cutins\<cutinAssetId>\` and write relative paths as `spine/cutins/<cutinAssetId>/...`.
- Use `cutin` / `cutins` for English code, API, path, and field explanations; Chinese UI copy may say `特写动画`.
- Represent cutin data as `spineAssets` / `spine_assets` rows with the `spine/cutins/` prefix. Do not introduce another top-level ingest array for cutin data.
- Identify cutin assets by the `spine/cutins/` prefix in `spineAssets` / `spine_assets` paths, even though they share the normal Spine asset table.
- Do not set `roles.has_spine` to true for a role that is only bound to cutin assets.
- Do not count cutin animations in `roles.animation_count`, `projects.spine_role_count`, or the normal `projects.animation_count`; count only non-cutin character/actor Spine assets for those fields.
- The normal `/api/projects/:projectId/animations` response must exclude `spine/cutins/` assets; cutin assets should be returned only by `/api/projects/:projectId/cutins`.
- Use `cutin-json`, `cutin-skeleton`, `cutin-atlas`, and `cutin-page` for cutin `asset_paths.kind` rows. Do not write cutin files with the generic `json`, `skeleton`, `atlas`, or `page` kinds.
- For cutin-only projects or cutin-only appends, keep normal role lists and normal animation pages clean: cutin rows may be searchable through cutin APIs, but they must not imply ordinary character Spine coverage.
- When directly appending or replacing cutins in SQLite, delete and rebuild only the targeted cutin rows in `spine_assets`, `animations`, `animations_fts`, and `asset_paths`; leave existing roles, catalog images, normal character Spine assets, effects, actions, and battle profiles intact.
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
$sourceRoot = "H:\game_assets_rebuild\3001_example"
$projectId = "3001"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$ingestDir = Join-Path $sourceRoot "_temp\asset-hub-ingest\$projectId-$timestamp"
$hubIngestJson = Join-Path $ingestDir "hub-ingest.json"

Invoke-RestMethod -Method Post -ContentType "application/json" -InFile $hubIngestJson -Uri "http://192.168.0.9:5190/api/ingest/projects/$projectId/replace"
```

# Remote Ingest API

Use the remote ingest API when the source project is prepared on another machine and cannot safely write the Hub SQLite file directly.

The API only writes database rows. It does not upload or copy binary resources. Publish files to `\\192.168.0.9\wwwroot\<projectId>` first, or accept missing-file warnings and publish them before browser validation.

## Start the Hub for LAN Access

On the database host:

```powershell
$env:HOST = "0.0.0.0"
$env:PORT = "5190"
npm run dev
```

The v1 write API has no authentication. Use it only on a trusted LAN and do not expose it to the public internet.

## Endpoint

```text
POST /api/ingest/projects/<projectId>/replace
Content-Type: application/json
```

Request body is the complete `hub-ingest.json` package. `body.project.id` must equal `<projectId>`.

Example:

```powershell
$sourceRoot = "H:\game_assets_rebuild\3001_example"
$projectId = "3001"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$ingestDir = Join-Path $sourceRoot "_temp\asset-hub-ingest\$projectId-$timestamp"
$hubIngestJson = Join-Path $ingestDir "hub-ingest.json"

Invoke-RestMethod `
  -Method Post `
  -ContentType "application/json" `
  -InFile $hubIngestJson `
  -Uri "http://192.168.0.9:5190/api/ingest/projects/$projectId/replace"
```

Equivalent curl:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  --data-binary @hub-ingest.json \
  http://192.168.0.9:5190/api/ingest/projects/3001/replace
```

## Write Behavior

- The API performs a full project replacement in one SQLite transaction.
- It deletes old rows for the target `project_id` and rebuilds project, role, image, skill, Spine, animation, asset path, effect, action, cue, FTS, and battle profile rows.
- `source_catalog_json` and `source_spine_manifest` are stored as `api://hub-ingest/<projectId>`.
- Entity path fields remain relative. Full HTTP URLs are written only to base URL fields and `asset_paths.url`.
- Complete packages may include `actions[].remark`; the Hub ingest normalizes `remark`, `remarks`, `note`, `notes`, `comment`, and `comments` into the stored action remark.
- The JSON request body limit is 50 MB.
- Incremental upsert is not supported in v1.
- The replace API is not a patch API. Do not send a partial `hub-ingest.json` to update a few records in an existing project.

## Item-Level Updates

For small updates such as one role animation, several catalog roles, a few skill icons, or a handful of cutins, choose one of these strategies:

```text
complete replace package      Use the replace API only if the JSON contains the full current project state plus the changes.
local targeted script         Run a transaction on the Hub database host that touches only the target rows.
module-specific API           Design and implement a new targeted endpoint first, then call it remotely.
```

If the source work happens on another machine and there is no targeted API yet, do not fake a partial full-project package. Either move the targeted script to the database host or implement the dedicated API.

## Existing Project Cutin Appends

The v1 replace API is a full-project write. Do not use it to append a few cutin assets to an already curated project unless the package intentionally contains the complete project state.

For existing projects, prefer a project-specific script or a local SQLite transaction that deletes and rebuilds only the targeted cutin rows in:

```text
spine_assets
animations
animations_fts
asset_paths
```

The script should match cutins by stable asset ids and `spine/cutins/` paths, leaving existing roles, catalog images, normal character animations, effects, and action data intact.

## Success Response

```json
{
  "ok": true,
  "projectId": "3001",
  "importedAt": "2026-06-15T00:00:00.000Z",
  "stats": {
    "roles": 1,
    "spineAssets": 1,
    "animations": 3,
    "effectAssets": 0,
    "roleActions": 0
  },
  "missingFiles": {
    "asset": { "checked": 3, "missing": 0, "samples": [] },
    "catalog": { "checked": 1, "missing": 0, "samples": [] }
  },
  "warnings": []
}
```

Missing published files are warnings, not write failures, because adapters may write DB rows before the final publish copy finishes.

## Error Responses

Project id mismatch:

```json
{
  "error": "project id mismatch: route=3001, body=3002",
  "details": [{ "routeProjectId": "3001", "bodyProjectId": "3002" }]
}
```

Invalid relative path:

```json
{
  "error": "Invalid hub-ingest package",
  "details": ["spineAssets[0].skeletonPath must be a relative path, got http://..."]
}
```

## Validation After POST

Run:

```powershell
python C:\Users\gaorq\.codex\skills\asset-hub-project-ingest\scripts\validate_hub_project.py --db H:\game_assets_rebuild\Game_Asset_Hub\data\asset-hub.sqlite --project-id <projectId> --wwwroot \\192.168.0.9\wwwroot --origin http://192.168.0.9
```

Then smoke:

```text
GET /api/projects/<projectId>
GET /api/projects/<projectId>/roles
GET /api/projects/<projectId>/animations
GET /api/projects/<projectId>/cutins
GET /api/projects/<projectId>/spine/<assetId>
```

# Adapter Workflow

Every source project can be different. The adapter's job is not to make the source tidy; it is to produce the stable Hub destination contract.

## 1. Inspect

Run the read-only scanner first:

```powershell
python C:\Users\gaorq\.codex\skills\asset-hub-project-ingest\scripts\inspect_source_project.py <sourceRoot>
```

Look for:

- Spine skeletons, JSON skeletons, atlas files, and page textures.
- Role-like config files: role, hero, card, unit, knight, character.
- Skill/action config files: skill, action, show, battle.
- Effect config files: effect, eff, eff_node.
- Runtime clues: recovered scripts, Cocos/Unity resources, web demos, binary skeleton versions.

## 2. Choose Ingest Tier

Tier A: roles and catalog images.

Use when character identity and images are available but no reliable Spine pairing exists.

Tier B: roles plus character Spine preview.

Use when skeleton, atlas, pages, role mapping, and animation names can be recovered or safely inferred.

Tier C: action and effect playback.

Use only when timing, anchors, actor motion, hit timing, and effect placement can be traced to project config or recovered battle code.

## 3. Build the Destination Package

Create a derived workspace outside the source folder:

```text
H:/game_assets_rebuild/_hub_ingest/<projectId>
```

Recommended files:

```text
hub-ingest.json
source-map.json
notes.md
```

`source-map.json` can map each destination file/object back to the original extracted path. It is for traceability and does not need to be imported.

## 4. Publish Files

Copy only browser-loadable files to `\\192.168.0.9\wwwroot\<projectId>`.

Before copying, decide whether the target directory is new, replaceable, or contains hand-curated files. Do not mirror-delete unless it is explicitly disposable.

## 5. Write Database

If the Hub service is reachable, post the complete package to the remote ingest API:

```powershell
Invoke-RestMethod -Method Post -ContentType "application/json" -InFile H:\game_assets_rebuild\_hub_ingest\<projectId>\hub-ingest.json -Uri "http://192.168.0.9:5190/api/ingest/projects/<projectId>/replace"
```

See `api-ingest.md` for the full contract. Use the database contract in `db-write-contract.md` only for local fallback writes.

If direct SQL is used, wrap the whole project import in `BEGIN IMMEDIATE` and `COMMIT`, and roll back on error.

## 6. Validate

Run:

```powershell
python C:\Users\gaorq\.codex\skills\asset-hub-project-ingest\scripts\validate_hub_project.py --db H:\game_assets_rebuild\Game_Asset_Hub\data\asset-hub.sqlite --project-id <projectId> --wwwroot \\192.168.0.9\wwwroot --origin http://192.168.0.9
```

Then smoke the Hub API:

```text
/api/projects
/api/projects/<projectId>/roles
/api/projects/<projectId>/animations
/api/projects/<projectId>/spine/<assetId>
/api/projects/<projectId>/actions
/api/projects/<projectId>/actions/<actionId>/timeline
```

Acceptance criteria:

- The project appears in the project list.
- Role images and skill icons use `http://192.168.0.9/...` URLs.
- Character Spine assets load from HTTP URLs.
- No relative path field contains an HTTP URL.
- No API response depends on `/external-assets/` or `/hub/projects/`.
- Tier C projects have action cue counts that match source expectations.

# Targeted Item Update Workflow

Use this reference when the user wants to add, replace, or fix a small number of items inside an existing Game Asset Hub module. Examples: add one role animation to the animation player, update several character catalog records, replace a few cutin assets, fix skill icons/text, or patch a single action/effect timeline.

Do not treat item-level work as a full project ingest unless the user provides a complete project snapshot and explicitly wants replacement.

## 1. Classify the Target Module

Choose exactly one primary module before writing:

- Character catalog: `roles`, `role_images`, `skills`, `roles_fts`, `skills_fts`.
- Normal character animation: `spine_assets`, `animations`, `animations_fts`, `asset_paths`, visible through `/api/projects/<projectId>/animations`.
- Cutin animation: same Spine tables, but paths must use `spine/cutins/` and `asset_paths.kind` must use `cutin-*`, visible through `/api/projects/<projectId>/cutins`.
- Action/effect playback: `role_actions`, `effect_assets`, action cue tables, `asset_paths`, `project_battle_profiles` only when needed.
- File-only replacement: published files under `\\192.168.0.9\wwwroot`; database writes are needed only when paths, file names, atlas pages, animation names, or metadata change.

If the request changes UI behavior, API response shape, schema, or importer code rather than just data rows, handle it as a Hub code feature, not a targeted item update.

## 2. Identify Stable Keys

Resolve these before editing:

- `projectId`
- target `role_source_id` for role-bound updates
- target `asset_id` / `effect_asset_id` / `action_id`
- destination relative paths under `assets` or `catalog`
- whether the update is add, replace, or delete-and-rebuild

For replacements, prefer keeping stable IDs so existing URLs and UI selections continue to work. Change IDs only when the old ID is wrong or collides with another item.

## 3. Prepare a Temporary Workspace

Use a unique short-lived workspace:

```text
<sourceRoot>/_temp/asset-hub-ingest/<projectId>-<timestamp>
```

Keep a `notes.md` or small JSON manifest with:

- source file paths
- target IDs
- target published paths
- old values that will be replaced
- validation commands

Delete this workspace only after publish, write, and validation all pass.

## 4. Publish Browser Files

Copy only browser-loadable files to `\\192.168.0.9\wwwroot\<projectId>`.

Common targets:

```text
assets/spine/characters/<assetId>/
assets/spine/cutins/<cutinAssetId>/
assets/spine/effects/<effectId>/
catalog/images/roles/avatars/
catalog/images/roles/portraits/
catalog/images/skills/
```

If only the bytes of an existing file change and the relative path is unchanged, database rows may not need to change. Still validate HTTP accessibility and browser playback.

## 5. Write the Minimum Database Rows

Always use a transaction. For direct SQLite writes:

```sql
BEGIN IMMEDIATE;
-- targeted delete/update/insert
COMMIT;
```

For remote machines, the current `POST /api/ingest/projects/<projectId>/replace` endpoint is full-project replacement only. Do not send a partial package to patch a few rows. Use one of these instead:

- send a complete project snapshot through the replace API
- run a targeted script on the Hub database host
- design and implement a module-specific targeted API first

## 6. Table Scopes by Item Type

Character catalog add/update:

- Upsert `roles` by `(project_id, source_id)`.
- Replace or upsert that role's `role_images` rows by `(project_id, role_source_id, kind)`.
- Replace or upsert that role's `skills` rows by `(project_id, role_source_id, source_id, slot)`.
- Rebuild matching `roles_fts` and `skills_fts` rows.
- Recompute `roles.has_spine` and `roles.animation_count` only if normal, non-cutin Spine coverage changed.

Normal character animation add/replace:

- Publish files under `assets/spine/characters/<assetId>/`.
- Delete and rebuild targeted `spine_assets` row by `(project_id, asset_id)`.
- Delete and rebuild targeted `animations` and `animations_fts` rows for that asset.
- Delete and rebuild targeted `asset_paths` rows for that asset using generic `skeleton`, `json`, `atlas`, and `page` kinds.
- Update the bound role's `has_spine` and `animation_count`.
- Update project `spine_role_count` and `animation_count` if the project summary should reflect the change.

Cutin add/replace:

- Publish files under `assets/spine/cutins/<cutinAssetId>/`.
- Delete and rebuild only targeted cutin rows in `spine_assets`, `animations`, `animations_fts`, and `asset_paths`.
- Use `cutin-json`, `cutin-skeleton`, `cutin-atlas`, and `cutin-page` kinds.
- Do not update normal role `has_spine`, role `animation_count`, project `spine_role_count`, or normal project `animation_count`.
- Verify `/api/projects/<projectId>/cutins`; normal `/animations` must not include the cutin.

Action/effect timeline item:

- First trace the original battle config/code chain for timing, anchors, movement, hit, effect placement, scale, and layer.
- Replace the target `role_actions` row and its cue rows by stable `action_id`.
- Preserve or write `role_actions.remark` when replacing the action row; map source `remark`, `remarks`, `note`, `notes`, `comment`, or `comments` to the normalized `remark` field and include it in action `search_text`.
- Add or update referenced `effect_assets` and `asset_paths` only for newly introduced effect files.
- Avoid `effect_overrides` unless the original source chain cannot explain the needed correction.

File-only replacement:

- If target relative paths and DB metadata do not change, replace only the published file.
- Recheck HTTP HEAD/GET, CORS, and the relevant Hub page.
- If atlas pages, animation names, skeleton file type, or file names change, treat it as a normal character/cutin/effect data update instead.

## 7. Validate

Run the general validator:

```powershell
python C:\Users\gaorq\.codex\skills\asset-hub-project-ingest\scripts\validate_hub_project.py --db H:\game_assets_rebuild\Game_Asset_Hub\data\asset-hub.sqlite --project-id <projectId> --wwwroot \\192.168.0.9\wwwroot --origin http://192.168.0.9
```

Smoke the affected API/module only:

```text
GET /api/projects/<projectId>/roles
GET /api/projects/<projectId>/roles/<roleSourceId>
GET /api/projects/<projectId>/animations
GET /api/projects/<projectId>/cutins
GET /api/projects/<projectId>/spine/<assetId>
GET /api/projects/<projectId>/actions/<actionId>/timeline
```

For frontend-visible item changes, open the relevant page and verify selection, playback, images, filtering, and mobile layout if UI content length changed.

## Examples

Add one role animation to the animation player:

1. Publish the Spine files to `assets/spine/characters/<assetId>/`.
2. Insert or replace one `spine_assets` row.
3. Insert that asset's `animations` and `animations_fts` rows.
4. Insert `asset_paths` rows for skeleton/json, atlas, and pages.
5. Update the role's normal `has_spine` / `animation_count` and project normal animation summary.
6. Validate `/animations` and `/spine/<assetId>`.

Add or update several character catalog records:

1. Publish changed avatar, portrait, or skill icons under `catalog/images/...`.
2. Upsert target `roles` rows.
3. Replace affected `role_images` and `skills` rows for those roles.
4. Rebuild matching `roles_fts` and `skills_fts` rows.
5. Validate `/roles`, role detail modal data, images, search, and filters.

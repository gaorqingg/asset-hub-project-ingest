# SQLite Write Contract

Prefer the remote ingest API for projects prepared on other machines. Use direct SQLite writes only when running on the Hub database host or when the API is unavailable.

The Hub database is usually:

```text
H:/game_assets_rebuild/Game_Asset_Hub/data/asset-hub.sqlite
```

For full project ingest, write in one transaction per project. Delete and reinsert rows for the target `project_id` only; never clear unrelated projects.

For item-level updates, write in one transaction per targeted item group and touch only the minimum affected rows. See `item-update-workflow.md`.

## Project Base URLs

`projects.asset_base_url` and `projects.catalog_base_url` contain HTTP base URLs:

```text
projects.asset_base_url   = http://192.168.0.9/<projectId>/assets
projects.catalog_base_url = http://192.168.0.9/<projectId>/catalog
```

For API-written projects, `projects.source_catalog_json` and `projects.source_spine_manifest` are stored as `api://hub-ingest/<projectId>`. For local direct writes, they may both point to the normalized `hub-ingest.json` if there is no original catalog or manifest.

## Relative Path Fields

These fields must stay relative, never full HTTP URLs:

```text
spine_assets.skeleton_path
spine_assets.json_path
spine_assets.atlas_path
spine_assets.pages_json
effect_assets.skeleton_path
effect_assets.json_path
effect_assets.atlas_path
effect_assets.pages_json
role_images.path
skills.icon_path
asset_paths.path
```

Good:

```text
spine/characters/Naruto/Naruto.skel
```

Bad:

```text
http://192.168.0.9/3001/assets/spine/characters/Naruto/Naruto.skel
```

## asset_paths

`asset_paths` is the audit and validation table for browser-loadable asset files.

```text
project_id      = <projectId>
asset_id        = character assetId or effectAssetId
role_source_id  = role id for character assets, null for effects
kind            = skeleton | json | atlas | page | cutin-skeleton | cutin-json | cutin-atlas | cutin-page | effect-skeleton | effect-json | effect-atlas | effect-page
path            = relative path under <projectId>/assets
url             = full HTTP URL
exists_on_disk  = 1 when present under \\192.168.0.9\wwwroot\<projectId>\assets
```

`asset_paths.url` may be a full HTTP URL. It should not use old local proxy patterns such as `/external-assets/` or `/hub/projects/`.

## Cutin Spine Assets

Cutin (特写动画) assets are written to the normal Spine tables and separated by path prefix.

Required writes:

```text
spine_assets       one row per cutin asset, with json_path or skeleton_path under spine/cutins/
animations         one row per cutin animation
animations_fts     matching FTS rows for direct SQLite writes
asset_paths        runtime file rows using cutin-* kinds
```

Path rules:

```text
spine_assets.json_path      = spine/cutins/<cutinAssetId>/<file>.json
spine_assets.skeleton_path  = spine/cutins/<cutinAssetId>/<file>.skel
spine_assets.atlas_path     = spine/cutins/<cutinAssetId>/<file>.atlas
spine_assets.pages_json     = ["spine/cutins/<cutinAssetId>/<page>.png"]
asset_paths.kind            = cutin-json | cutin-skeleton | cutin-atlas | cutin-page
```

Do not update `roles.has_spine` or normal project animation summaries just because a role has only cutin assets. The Hub's `/cutins` API derives cutin counts from the `spine/cutins/` prefix.

## FTS Tables

When writing directly to SQLite, keep FTS rows in sync:

```text
roles_fts
skills_fts
animations_fts
```

The simplest safe approach is to follow the existing Hub importer pattern: delete target project rows from FTS tables first, insert normal rows, then insert matching FTS rows with the inserted rowid.

## Targeted Item Updates

Use targeted writes for small changes to an existing curated project. Do not run a full project replace unless the package contains complete project state.

Minimum scopes:

```text
catalog role update      roles, role_images, skills, roles_fts, skills_fts
normal Spine item        spine_assets, animations, animations_fts, asset_paths, roles summary, projects summary
cutin Spine item         spine_assets, animations, animations_fts, asset_paths only for targeted cutins
action/effect item       role_actions, action_*_cues, effect_assets/asset_paths only if new effects are introduced
file-only replacement    wwwroot files only when paths and metadata are unchanged
```

For targeted FTS updates, delete only the FTS rowids that correspond to the changed rows, then insert the replacement FTS rows with the new rowids. Do not clear project-wide FTS tables for a small item update.

## Action/Effect Tables

Only write action/effect rows when the adapter can explain timing and placement from the original project chain.

Required table groups:

```text
role_actions
effect_assets
action_actor_cues
action_motion_cues
action_hit_cues
action_effect_cues
project_battle_profiles
```

When writing `role_actions` directly, store normalized optional action notes in `role_actions.remark`. Map source `remark`, `remarks`, `note`, `notes`, `comment`, or `comments` to `remark`; leave it `NULL` when empty. Include the remark text in `role_actions.search_text` so action filtering can match remark keywords.

Use `effect_overrides` only as a last-resort manual layer after documenting the missing original source chain.

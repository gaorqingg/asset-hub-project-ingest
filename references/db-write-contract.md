# SQLite Write Contract

The Hub database is usually:

```text
H:/game_assets_rebuild/Game_Asset_Hub/data/asset-hub.sqlite
```

Write in one transaction per project. Delete and reinsert rows for the target `project_id` only; never clear unrelated projects.

## Project Base URLs

`projects.asset_base_url` and `projects.catalog_base_url` contain HTTP base URLs:

```text
projects.asset_base_url   = http://192.168.0.9/<projectId>/assets
projects.catalog_base_url = http://192.168.0.9/<projectId>/catalog
```

`projects.source_catalog_json` and `projects.source_spine_manifest` may both point to the normalized `hub-ingest.json` if there is no original catalog or manifest.

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
kind            = skeleton | json | atlas | page | effect-skeleton | effect-json | effect-atlas | effect-page
path            = relative path under <projectId>/assets
url             = full HTTP URL
exists_on_disk  = 1 when present under \\192.168.0.9\wwwroot\<projectId>\assets
```

`asset_paths.url` may be a full HTTP URL. It should not use old local proxy patterns such as `/external-assets/` or `/hub/projects/`.

## FTS Tables

When writing directly to SQLite, keep FTS rows in sync:

```text
roles_fts
skills_fts
animations_fts
```

The simplest safe approach is to follow the existing Hub importer pattern: delete target project rows from FTS tables first, insert normal rows, then insert matching FTS rows with the inserted rowid.

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

Use `effect_overrides` only as a last-resort manual layer after documenting the missing original source chain.

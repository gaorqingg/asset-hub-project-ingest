# hub-ingest.json Contract

`hub-ingest.json` is the normalized destination package for a source project. It describes what should be written to Game Asset Hub after source-specific extraction has already happened.

The file should be kept with the derived ingest workspace, for example:

```text
H:/game_assets_rebuild/_hub_ingest/<projectId>/hub-ingest.json
```

## Top-Level Shape

```json
{
  "project": {},
  "roles": [],
  "spineAssets": [],
  "effectAssets": [],
  "actions": [],
  "battleProfile": null,
  "sources": {}
}
```

Only `project` is required for every package. `roles`, `spineAssets`, `effectAssets`, and `actions` may be empty arrays.

## project

Required fields:

```json
{
  "id": "3001",
  "name": "Project display name",
  "runtime": "pixi-spine-3.8",
  "sourceRoot": "H:/game_assets_rebuild/3001_example"
}
```

Optional fields:

```json
{
  "createdAt": "2026-06-15T00:00:00+08:00",
  "tags": ["character", "animation", "Spine 3.8"],
  "iconPath": "images/roles/avatars/1001.png",
  "assetBaseUrl": "http://192.168.0.9/3001/assets",
  "catalogBaseUrl": "http://192.168.0.9/3001/catalog"
}
```

Supported runtime values should match Hub code. Current known values are `pixi-spine-3.8` and `spine-webgl-3.6`.

## roles

Each role represents a searchable character identity.

```json
{
  "sourceId": "1001",
  "displayName": "Naruto",
  "fallbackName": "role_1001",
  "model": "Naruto",
  "career": "attack",
  "rarity": "SSR",
  "category": "ninja",
  "source": "hero_config",
  "images": [
    {
      "kind": "avatar",
      "path": "images/roles/avatars/1001.png",
      "sourcePath": "H:/source/icon_1001.png"
    }
  ],
  "skills": [
    {
      "sourceId": "2001",
      "slot": "active",
      "slotLabel": "Active",
      "name": "Skill name",
      "iconPath": "images/skills/2001.png",
      "summary": "",
      "description": ""
    }
  ],
  "raw": {}
}
```

`images[].path` and `skills[].iconPath` are relative to `<projectId>/catalog`.

## spineAssets

Each item is a character or actor Spine asset.

```json
{
  "assetId": "Naruto",
  "sourceAssetId": "Naruto",
  "roleSourceId": "1001",
  "runtime": "pixi-spine-3.8",
  "name": "Naruto",
  "skeletonPath": "spine/characters/Naruto/Naruto.skel",
  "jsonPath": null,
  "atlasPath": "spine/characters/Naruto/Naruto.atlas",
  "pages": ["spine/characters/Naruto/Naruto.png"],
  "version": null,
  "animations": [
    {
      "name": "Stand01",
      "duration": null,
      "frameRate": 24,
      "isDefault": true
    }
  ],
  "raw": {}
}
```

All paths are relative to `<projectId>/assets`. Include either `skeletonPath` for binary Spine or `jsonPath` for JSON Spine. Include all atlas page textures in `pages`.

## effectAssets

Each item is a reusable Spine effect.

```json
{
  "effectAssetId": "HitSpark",
  "effectName": "HitSpark",
  "runtime": "pixi-spine-3.8",
  "skeletonPath": "spine/effects/HitSpark/HitSpark.skel",
  "jsonPath": null,
  "atlasPath": "spine/effects/HitSpark/HitSpark.atlas",
  "pages": ["spine/effects/HitSpark/HitSpark.png"],
  "animations": ["Skill01"],
  "defaultAnimation": "Skill01",
  "bounds": {},
  "raw": {}
}
```

## actions

Actions are optional and should only be created when the source battle code/config chain is understood well enough to explain timing and placement.

```json
{
  "roleSourceId": "1001",
  "actionId": "1001:2001",
  "skillId": "2001",
  "slot": "active",
  "slotLabel": "Active",
  "actionName": "Skill01",
  "label": "Skill name",
  "sourceKind": "project_adapter",
  "roleAnimation": "Skill01",
  "scriptName": "Skill_2001",
  "durationMs": 1800,
  "isPrimary": true,
  "actorCues": [],
  "motionCues": [],
  "hitCues": [],
  "effectCues": [],
  "raw": {}
}
```

Cue field names should mirror the existing Hub normalized structures: actor cues switch animations, motion cues move actors, hit cues describe target hit timing, and effect cues spawn effect assets.

## battleProfile

Use `null` for projects without action/effect playback.

```json
{
  "defaultEnemyRoleSourceId": "default-enemy",
  "defaultEnemyAssetId": "DefaultEnemy",
  "battleCoordScale": 1,
  "casterX": -260,
  "casterY": 0,
  "targetX": 260,
  "targetY": 0,
  "casterScale": 0.45,
  "targetScale": 0.45,
  "coordinateMode": "custom",
  "idleAnimation": "Stand01",
  "hitAnimation": "Hit01",
  "anchorRules": {},
  "raw": {}
}
```

Use a project-specific `coordinateMode` when the adapter has recovered the original battle coordinate rules.

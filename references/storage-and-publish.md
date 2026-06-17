# Storage and Publishing

The shared publishing root is:

```text
\\192.168.0.9\wwwroot
```

The browser-facing origin is:

```text
http://192.168.0.9
```

Each project gets exactly one published project root:

```text
\\192.168.0.9\wwwroot\<projectId>
```

## Destination Layout

Use this layout for browser-loadable output:

```text
\\192.168.0.9\wwwroot\<projectId>\
  assets\
    spine\
      characters\
        <assetId>\
          <assetId>.skel
          <assetId>.json
          <assetId>.atlas
          <page files>
      cutins\
        <cutinAssetId>\
          <cutinAssetId>.skel
          <cutinAssetId>.json
          <cutinAssetId>.atlas
          <page files>
      effects\
        <effectId>\
          <effectId>.skel
          <effectId>.json
          <effectId>.atlas
          <page files>
  catalog\
    images\
      roles\
        avatars\
          <roleId>.png
        portraits\
          <roleId>.png
      skills\
        <skillId>.png
```

Only include files the Hub needs to load or show in the browser. Keep full APK dumps and analysis artifacts outside `wwwroot`.

## HTTP URL Mapping

For project `3001`, the default base URLs are:

```text
asset_base_url   = http://192.168.0.9/3001/assets
catalog_base_url = http://192.168.0.9/3001/catalog
```

Relative path:

```text
spine/characters/Naruto/Naruto.skel
```

Full URL:

```text
http://192.168.0.9/3001/assets/spine/characters/Naruto/Naruto.skel
```

Cutin relative path:

```text
spine/cutins/cutin_liluoke_renjiedazhan_tips/liluoke_renjiedazhan_tips.json
```

Cutin full URL:

```text
http://192.168.0.9/3001/assets/spine/cutins/cutin_liluoke_renjiedazhan_tips/liluoke_renjiedazhan_tips.json
```

Catalog relative path:

```text
images/roles/avatars/1001.png
```

Full URL:

```text
http://192.168.0.9/3001/catalog/images/roles/avatars/1001.png
```

## Copying Rules

- Normalize paths to forward slashes in JSON and database fields.
- Keep file names stable and URL-safe: letters, digits, underscore, hyphen, dot.
- Preserve atlas page names when the atlas references exact texture names.
- Do not flatten all assets into one folder if names collide; use one folder per character asset, cutin asset, or effect.
- Publish cutin runtime files to `assets/spine/cutins/<cutinAssetId>/` and keep every cutin database path under `spine/cutins/<cutinAssetId>/`.
- Do not use `robocopy /MIR` unless the target project directory is known to be disposable.
- If replacing a project publish, create or confirm a backup when the target contains hand-curated files.

## CORS Checks

Current nginx should return `Access-Control-Allow-Origin: *` for GET and HEAD. Check representative files:

```powershell
Invoke-WebRequest "http://192.168.0.9/<projectId>/assets/spine/characters/<assetId>/<assetId>.skel" -Method Head -Headers @{ Origin = "http://127.0.0.1:5190" } -UseBasicParsing
```

If future code triggers preflight, nginx must return a 204-style response for OPTIONS.

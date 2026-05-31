# JianYing Folder Picker Design

## Problem

Both `VoiceWorkflowView.vue` and `SrtExportModal.vue` require users to manually paste a full JianYing project directory path (e.g., `/Users/xxx/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/工程ID`). This is error-prone and inconvenient.

## Goal

Replace the manual path input with a server-side folder browser, keeping manual input as a fallback for edge cases.

## Constraints

- Web app (Flask + Vue), not Electron — no native folder dialog with path access
- Backend runs locally, can access filesystem directly
- JianYing drafts are typically at `~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/`
- Two files need updating: `VoiceWorkflowView.vue` and `SrtExportModal.vue`

## Design

### Backend: `GET /api/system/ls`

New blueprint `server/routes/system.py` with a single endpoint.

**Request:** `GET /api/system/ls?path=<path>`
- `path` is optional; defaults to `~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/`
- Can be absolute or relative (resolved against home dir)

**Response:**
```json
{
  "current": "/absolute/path",
  "parent": "/absolute/parent/path",
  "entries": [
    { "name": "ProjectFolder", "path": "/absolute/path/ProjectFolder" }
  ]
}
```

- Only lists directories (not files), sorted alphabetically
- `parent` is `null` if at filesystem root
- Returns 400 for invalid/nonexistent paths, 403 for permission errors

**Registration:** Add `system_bp` blueprint to `app.py`.

### Frontend: `FolderBrowser.vue`

New component: `web/src/components/FolderBrowser.vue`

**Props:**
- `open` — v-model boolean for modal visibility
- `startPath` — optional initial path (falls back to last used path from localStorage, then default)

**Behavior:**
- Opens as an `a-modal`
- Top: breadcrumb trail (each segment clickable to navigate)
- Middle: scrollable list of subdirectories (clickable rows)
  - First row: `..` (go up), unless at root
  - Each row shows folder name
- Bottom: "选择此文件夹" confirm button (enabled when a valid directory is displayed)
- Loads directory listing from `GET /api/system/ls?path=...`
- Loading state while fetching, error state with retry on failure

**Emits:**
- `@select(path: string)` — the selected absolute path

### Integration

In both `VoiceWorkflowView.vue` and `SrtExportModal.vue`:

1. Keep existing `<a-input v-model:value="jianyingDraftDir">` as-is
2. Add a button (📁 icon) next to the input using `a-input-group` / flex layout
3. Button click opens `<FolderBrowser>` component
4. On `@select`, set `jianyingDraftDir` to the selected path

Layout change (both files):
```html
<div style="display: flex; gap: 8px;">
  <a-input v-model:value="jianyingDraftDir" placeholder="..." style="flex: 1" />
  <a-button @click="showFolderBrowser = true">📁</a-button>
</div>
<FolderBrowser v-model:open="showFolderBrowser" @select="jianyingDraftDir = $event" />
```

### localStorage

Existing `jianying_draft_dir` key continues to work. The FolderBrowser also reads this as its initial path when no `startPath` prop is given.

## Files to change

| File | Change |
|---|---|
| `server/routes/system.py` | **New** — `system_bp` with `/api/system/ls` |
| `server/app.py` | Register `system_bp` |
| `web/src/components/FolderBrowser.vue` | **New** — folder browser modal component |
| `web/src/views/VoiceWorkflowView.vue` | Add folder button + FolderBrowser to Jianying export modal |
| `web/src/components/SrtExportModal.vue` | Add folder button + FolderBrowser to Jianying import section |

## Testing

- Manual: start servers, open Jianying export modal, click folder button, navigate, select
- Unit: add test for `/api/system/ls` endpoint in `server/tests/`

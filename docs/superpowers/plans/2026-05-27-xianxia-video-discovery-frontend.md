# Xianxia Video Discovery Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the frontend MVP for the xianxia short-video discovery workspace described in `docs/superpowers/specs/2026-05-27-xianxia-video-discovery-ui-design.md`.

**Architecture:** Add a `/discovery` route with a three-panel Vue workspace: search/sidebar, result list, and analysis panel. Keep real API integration minimal by using local mock discovery data and existing `textsApi.create` for the handoff into the text library, while adding a `prefill` path into the existing video generation modal.

**Tech Stack:** Vue 3, Vite, Pinia, Ant Design Vue, Node built-in test runner for pure discovery helpers.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `web/src/utils/discovery.js` | Pure helpers: scoring, filtering, sorting, script draft generation, video prefill generation |
| `web/src/utils/discovery.test.js` | Node tests for helper behavior |
| `web/src/stores/discovery.js` | Pinia store for mock search, selection, analysis, script draft, favorite state |
| `web/src/views/Discovery.vue` | Main three-panel discovery workspace and video modal handoff |
| `web/src/components/discovery/DiscoverySearchBar.vue` | Platform/keyword/filter controls and manual URL parse entry |
| `web/src/components/discovery/DiscoverySidebar.vue` | Keyword packs, history, favorite/status filters |
| `web/src/components/discovery/DiscoveryResultList.vue` | Search result list shell, loading/empty states, sorting summary |
| `web/src/components/discovery/DiscoveryResultItem.vue` | Single candidate row with thumbnail, metrics, scores, status, actions |
| `web/src/components/discovery/DiscoveryAnalysisPanel.vue` | Right-side tabs for overview, structure, script, suggestions, source record |
| `web/src/components/discovery/DiscoveryScoreBadge.vue` | Shared score tag component |
| `web/src/components/discovery/DiscoveryScriptEditor.vue` | Script style/length controls, editable title/body, import action |
| `web/src/components/discovery/DiscoveryVideoSuggestion.vue` | Recommended template/audio/subtitle/scene keyword display |
| `web/src/router/index.js` | Register `/discovery` route |
| `web/src/App.vue` | Add “热点采集” navigation item and selected route handling |
| `web/src/api/index.js` | Add discovery API placeholders for future backend endpoints |
| `web/src/components/video/VideoGenerateModal.vue` | Accept `prefill` prop and include `voice_description` / subtitle options / source context in job request |
| `web/src/components/video/VideoTemplateStep.vue` | Accept preferred template key and select matching template on load |

## Tasks

### Task 1: Discovery Helper Tests

- [ ] Write failing Node tests in `web/src/utils/discovery.test.js` for score labels, result filtering/sorting, script draft generation, and video prefill generation.
- [ ] Run `cd web && node --test src/utils/discovery.test.js` and confirm it fails because `src/utils/discovery.js` does not exist.
- [ ] Implement `web/src/utils/discovery.js`.
- [ ] Re-run `cd web && node --test src/utils/discovery.test.js` and confirm it passes.

### Task 2: Store And Mock Data

- [ ] Create `web/src/stores/discovery.js`.
- [ ] Seed representative mock items across YouTube, Bilibili, Douyin, and Kuaishou.
- [ ] Implement `search`, `resolveUrl`, `selectItem`, `analyzeItem`, `generateScript`, `toggleFavorite`, and `markImported`.
- [ ] Keep async delays short and deterministic enough for UI feedback.

### Task 3: Discovery Components

- [ ] Create the discovery component directory.
- [ ] Implement search bar, sidebar, result list, result item, score badge, analysis panel, script editor, and video suggestion components.
- [ ] Use the current theme variables and avoid nested cards or marketing layouts.
- [ ] Implement loading, empty, no-result, analysis failure-ready, generated script, and imported states.

### Task 4: Page Integration

- [ ] Create `web/src/views/Discovery.vue`.
- [ ] Wire store actions to components.
- [ ] Import generated scripts through `textsApi.create`, creating/reusing tags where possible through `tagsApi`.
- [ ] Open `VideoGenerateModal` with the created text and discovery prefill after import.

### Task 5: Navigation And Video Prefill

- [ ] Register `/discovery` in `web/src/router/index.js`.
- [ ] Add “热点采集” to `web/src/App.vue`.
- [ ] Extend `VideoGenerateModal.vue` with optional `prefill`.
- [ ] Extend `VideoTemplateStep.vue` with optional `preferredTemplateKey`.
- [ ] Add placeholder `discoveryApi` functions in `web/src/api/index.js` for future backend replacement.

### Task 6: Verification

- [ ] Run `cd web && node --test src/utils/discovery.test.js`.
- [ ] Run `cd web && pnpm run build`.
- [ ] Run `uv run pytest` from repo root if frontend build passes.
- [ ] Start the dev server and verify `/discovery` renders.
- [ ] Use browser validation for desktop and mobile widths: search, select, analyze, generate script, import, open video modal.

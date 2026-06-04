# Novel Obsidian Graph Refactor - Implementation Plan

## Context

The novel continuation module's character/event graphs use Vue Flow (`@vue-flow/core`) which renders large white rectangular cards — more like a flowchart editor than a knowledge network explorer. The goal is to replace this with an Obsidian-style graph view: dark borderless canvas, force-directed layout (d3-force), dot-style nodes, zoom/pan, search/filter, neighbor highlighting, and click-to-inspect.

This plan covers **Phase 1 + Phase 2** of the refactor plan:
- **Phase 1**: Frontend visual replacement — swap Vue Flow for d3-force SVG canvas
- **Phase 2**: Explore and filter — search, type/edge/importance filters, neighbor highlight, legend, inspector panel

Phase 3+ (backend projection API, edit mode, mixed graph) will be a follow-up.

---

## Step 1: Install d3 dependencies

**File:** `web/package.json`

```bash
cd web && pnpm add d3-force d3-zoom d3-drag d3-selection
```

---

## Step 2: Add `graphView` state to novels store

**File:** `web/src/stores/novels.js`

Add a `graphView` object to state for UI state management (mode, query, selection, filters, zoom):

```js
// Add to state():
graphView: {
  mode: 'explore',        // 'explore' | 'edit'
  query: '',
  selectedId: null,        // 'entity:12' or 'event:34'
  hoveredId: null,
  focusedId: null,
  neighborIds: [],
  filters: {
    nodeTypes: [],         // ['character', 'location', 'item', 'faction']
    edgeTypes: [],         // ['ally', 'enemy', 'mentor', ...]
    importanceRange: [0, 10],
    chapterRange: null,
  },
  layout: {
    running: false,
    pinned: {},            // { 'entity:12': { x, y } }
    zoom: 1,
    center: [0, 0],
  },
  stats: null,             // { nodeCount, edgeCount, degreeMap, ... }
  legend: null,            // { nodeTypes: [...], edgeTypes: [...] }
},
```

Add actions: `setGraphViewMode`, `setGraphViewQuery`, `setGraphViewFilter`, `clearGraphView`.

---

## Step 3: Create `useForceGraph.js` composable

**File:** `web/src/components/novel/useForceGraph.js`

A Vue composable that encapsulates d3-force simulation lifecycle. Accepts reactive `nodes`, `edges`, `options` and returns:
- `svgRef` — template ref for the SVG element
- `simulation` — the d3-force simulation instance
- `zoomTransform` — current zoom state
- `restart()` — restart simulation
- `pinNode(id, x, y)` / `unpinNode(id)`
- `focusNode(id)` — zoom/pan to center on a node
- `highlightNeighbors(id)` — highlight connected nodes
- `clearHighlight()`

Key behaviors:
- Dark background (#0d1117)
- `forceManyBody` strength -180 to -420 based on node count
- Link distance inversely proportional to relationship strength (220px at 0.0 → 80px at 1.0)
- Node radius 4–11px based on importance
- Zoom/pan via d3-zoom
- Drag nodes via d3-drag (pins on drag end)
- Edge colors by relation type (reuse existing color map from current components)

---

## Step 4: Create `ObsidianGraphCanvas.vue`

**File:** `web/src/components/novel/ObsidianGraphCanvas.vue`

The shared canvas component replacing both VueFlow instances. Props:

```js
props: {
  nodes: Array,          // [{ id, name, type, importance, ... }]
  edges: Array,          // [{ id, source, target, type, label, ... }]
  graphType: String,     // 'characters' | 'events'
  selectedId: String,
  hoveredId: String,
  neighborIds: Array,
  mode: String,          // 'explore' | 'edit'
  query: String,
}
```

Emits: `select`, `hover`, `unhover`, `dblclick`, `drag-end`, `canvas-click`, `create-edge`

SVG structure:
```
<svg>
  <defs>  <!-- arrow markers, glow filters -->
  <g class="edges">  <!-- thin colored lines -->
  <g class="nodes">  <!-- circles with optional labels -->
  <g class="labels"> <!-- visible on hover/select -->
</svg>
```

Node rendering:
- Normal: filled circle, color by type, radius by importance
- Hovered: slightly larger, show label
- Selected: bright ring, show label
- Neighbor of selected: normal; non-neighbors dimmed (opacity 0.2)
- Query match: bright glow

Edge rendering:
- Normal: thin line (1px), color by relation type
- Connected to selected: thicker (2px), full opacity
- Non-connected: dimmed (opacity 0.1)

---

## Step 5: Create auxiliary components

### `GraphToolbar.vue`
**File:** `web/src/components/novel/GraphToolbar.vue`

Top toolbar with:
- Search input (filters nodes by name/alias/summary)
- Mode toggle: Explore ↔ Edit
- Graph type toggle: 人物 ↔ 事件 (only in explore mode)
- "Save Layout" button (edit mode only)
- Zoom controls (+, -, fit)

### `GraphFilters.vue`
**File:** `web/src/components/novel/GraphFilters.vue`

Left sidebar filter panel:
- Node type checkboxes (character, location, item, faction)
- Edge type checkboxes (ally, enemy, mentor, family, lover, betrayal)
- Importance range slider (0–10)
- Chapter range selector
- "Current chapter only" toggle
- "Pending AI changes only" toggle

### `GraphLegend.vue`
**File:** `web/src/components/novel/GraphLegend.vue`

Bottom-left legend showing:
- Node type → color mapping
- Edge type → color mapping
- Node size → importance mapping

### `GraphInspector.vue`
**File:** `web/src/components/novel/GraphInspector.vue`

Right-side detail panel (replaces NovelEntityInspector/NovelRelationInspector/NovelEventInspector for graph mode):
- Shows full details of selected node/edge
- Node: name, type, aliases, summary, importance, attributes, recent chapter
- Edge: type, label, description, strength, evidence
- "Focus" button — zoom to node
- "Edit" button (edit mode only)

---

## Step 6: Rewrite graph wrapper components

### `NovelCharacterGraph.vue` — rewrite as data-loading wrapper
**File:** `web/src/components/novel/NovelCharacterGraph.vue`

Replace VueFlow with ObsidianGraphCanvas. This component:
1. Calls `store.loadCharacterGraph(pid)` on mount
2. Maps `store.entities` → nodes with namespaced IDs (`entity:${id}`)
3. Maps `store.relations` → edges with namespaced source/target
4. Passes data to `<ObsidianGraphCanvas>`
5. Handles events: select → `store.selectedEntityId`, hover → highlight, drag-end → update position

### `NovelEventGraph.vue` — rewrite as data-loading wrapper
**File:** `web/src/components/novel/NovelEventGraph.vue`

Same pattern:
1. Calls `store.loadEventGraph(pid)` on mount
2. Maps `store.events` → nodes with namespaced IDs (`event:${id}`)
3. Maps `store.eventRelations` → edges
4. Passes to `<ObsidianGraphCanvas>`
5. Handles events

---

## Step 7: Update NovelWorkspace.vue

**File:** `web/src/views/NovelWorkspace.vue`

Replace the graph section with:
```html
<div v-else-if="store.activeMode === 'graph'" class="workspace-main">
  <GraphToolbar />
  <GraphFilters />
  <div class="workspace-graph">
    <NovelCharacterGraph v-if="store.graphType === 'characters'" />
    <NovelEventGraph v-else />
  </div>
  <GraphLegend />
  <GraphInspector />
</div>
```

Import the new components. Remove old VueFlow-related CSS. Add new dark-theme graph styles.

---

## Step 8: Install & verify

```bash
cd web && pnpm install
cd web && pnpm run dev
```

Navigate to a novel project → 图谱 tab → verify:
- Dark canvas with dot nodes
- Force-directed layout converges
- Zoom/pan/drag works
- Node hover shows label, highlights neighbors
- Node click shows details in inspector
- Search filters nodes
- Type/edge filters work
- Mode toggle (explore/edit) visible
- Save layout works in edit mode

---

## Files to create (new)
- `web/src/components/novel/useForceGraph.js`
- `web/src/components/novel/ObsidianGraphCanvas.vue`
- `web/src/components/novel/GraphToolbar.vue`
- `web/src/components/novel/GraphFilters.vue`
- `web/src/components/novel/GraphLegend.vue`
- `web/src/components/novel/GraphInspector.vue`

## Files to modify
- `web/package.json` (add d3-force, d3-zoom, d3-drag, d3-selection)
- `web/src/stores/novels.js` (add graphView state)
- `web/src/components/novel/NovelCharacterGraph.vue` (rewrite)
- `web/src/components/novel/NovelEventGraph.vue` (rewrite)
- `web/src/views/NovelWorkspace.vue` (update graph section)

## Files to delete (after migration)
- None in Phase 1-2. Old VueFlow components are rewritten in-place.

## Dependencies
- `d3-force` — force-directed layout simulation
- `d3-zoom` — zoom/pan behavior
- `d3-drag` — node dragging
- `d3-selection` — DOM selection utilities

## Verification
1. `cd web && pnpm run dev` — no build errors
2. Navigate to novel project → 图谱 tab
3. Character graph: nodes appear as dots, force layout converges, zoom/pan works
4. Event graph: same behavior, timeline bias via forceX
5. Hover a node → neighbors highlight, label appears
6. Click a node → inspector shows details
7. Type "角色名" in search → matching nodes glow
8. Toggle filters → nodes/edges show/hide
9. Switch to edit mode → drag a node → save layout → reload → position preserved
10. `uv run pytest` — no regressions

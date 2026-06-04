// useForceGraph.js — Vue composable wrapping d3-force for Obsidian-style graph
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { forceSimulation, forceLink, forceManyBody, forceCenter, forceX, forceY, forceCollide } from 'd3-force'
import { zoom, zoomIdentity } from 'd3-zoom'
import { select } from 'd3-selection'
import { drag } from 'd3-drag'

// Color maps (reuse from existing components)
export const NODE_TYPE_COLORS = {
  character: '#58a6ff',
  location: '#7ee787',
  item: '#d2a8ff',
  faction: '#f0883e',
  default: '#8b949e',
}

export const EDGE_TYPE_COLORS = {
  mentor: '#58a6ff',
  ally: '#7ee787',
  enemy: '#f85149',
  family: '#d2a8ff',
  lover: '#f778ba',
  betrayal: '#f0883e',
  causes: '#7ee787',
  drives: '#58a6ff',
  blocks: '#f85149',
  reverses: '#f0883e',
  reveals: '#d2a8ff',
  escalates: '#f778ba',
  default: '#484f58',
}

export function getNodeColor(type) {
  return NODE_TYPE_COLORS[type] || NODE_TYPE_COLORS.default
}

export function getEdgeColor(type) {
  return EDGE_TYPE_COLORS[type] || EDGE_TYPE_COLORS.default
}

export function useForceGraph(options = {}) {
  const {
    nodeRadius = (d) => 4 + (d.importance || 5) * 0.7,
    linkDistance = (d) => 220 - (d.strength || 0.5) * 140,
    chargeStrength = -250,
    graphType = 'characters', // 'characters' | 'events'
  } = options

  const svgRef = ref(null)
  const simulation = ref(null)
  const zoomTransform = ref({ x: 0, y: 0, k: 1 })

  let svgEl = null
  let gEdges = null
  let gNodes = null
  let gLabels = null
  let zoomBehavior = null
  let width = 800
  let height = 600

  // Internal data copies (d3 mutates them)
  let _nodes = []
  let _edges = []

  function init(svgElement, nodes, edges) {
    svgEl = svgElement
    _nodes = nodes.map(n => ({ ...n }))
    _edges = edges.map(e => ({ ...e }))

    const rect = svgEl.getBoundingClientRect()
    width = rect.width || 800
    height = rect.height || 600

    const svg = select(svgEl)

    // Clear previous
    svg.selectAll('*').remove()

    // Defs: arrow markers
    const defs = svg.append('defs')
    Object.entries(EDGE_TYPE_COLORS).forEach(([type, color]) => {
      defs.append('marker')
        .attr('id', `arrow-${type}`)
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 20)
        .attr('refY', 0)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', color)
        .attr('opacity', 0.6)
    })

    // Glow filter for selected/hovered
    const glowFilter = defs.append('filter').attr('id', 'glow')
    glowFilter.append('feGaussianBlur').attr('stdDeviation', '3').attr('result', 'coloredBlur')
    const feMerge = glowFilter.append('feMerge')
    feMerge.append('feMergeNode').attr('in', 'coloredBlur')
    feMerge.append('feMergeNode').attr('in', 'SourceGraphic')

    // Groups
    gEdges = svg.append('g').attr('class', 'graph-edges')
    gNodes = svg.append('g').attr('class', 'graph-nodes')
    gLabels = svg.append('g').attr('class', 'graph-labels')

    // Zoom
    zoomBehavior = zoom()
      .scaleExtent([0.1, 8])
      .on('zoom', (event) => {
        const t = event.transform
        zoomTransform.value = { x: t.x, y: t.y, k: t.k }
        gEdges.attr('transform', t)
        gNodes.attr('transform', t)
        gLabels.attr('transform', t)
      })

    svg.call(zoomBehavior)

    // Drag behavior
    const dragBehavior = drag()
      .on('start', (event, d) => {
        if (!event.active) simulation.value.alphaTarget(0.3).restart()
        d.fx = d.x
        d.fy = d.y
      })
      .on('drag', (event, d) => {
        d.fx = event.x
        d.fy = event.y
      })
      .on('end', (event, d) => {
        if (!event.active) simulation.value.alphaTarget(0)
        // Keep pinned (user dragged)
        // d.fx and d.fy stay set → pinned
        if (options.onDragEnd) {
          options.onDragEnd(d)
        }
      })

    // Build simulation
    const forceLinkObj = forceLink(_edges)
      .id(d => d.id)
      .distance(linkDistance)

    simulation.value = forceSimulation(_nodes)
      .force('link', forceLinkObj)
      .force('charge', forceManyBody().strength(chargeStrength))
      .force('center', forceCenter(width / 2, height / 2))
      .force('collide', forceCollide().radius(d => nodeRadius(d) + 2))

    // For event graph, bias X toward timeline position
    if (graphType === 'events') {
      simulation.value.force('x', forceX(d => {
        // Map timeline_order to x position
        const order = d.timeline_order || 0
        return 100 + order * 60
      }).strength(0.15))
      simulation.value.force('y', forceY(height / 2).strength(0.05))
    }

    simulation.value.on('tick', () => {
      render(dragBehavior)
    })

    // Apply saved zoom if any
    if (options.initialZoom) {
      svg.call(zoomBehavior.transform, zoomIdentity
        .translate(options.initialZoom.x, options.initialZoom.y)
        .scale(options.initialZoom.k))
    }
  }

  function render(dragBehavior) {
    // Edges
    const edgeSel = gEdges.selectAll('line')
      .data(_edges, d => d.id)

    edgeSel.exit().remove()

    // Invisible hit area for easier clicking
    const edgeHitSel = gEdges.selectAll('.edge-hit')
      .data(_edges, d => d.id)
    edgeHitSel.exit().remove()
    const edgeHitEnter = edgeHitSel.enter().append('line')
      .attr('class', 'edge-hit')
      .attr('stroke', 'transparent')
      .attr('stroke-width', 12)
      .attr('cursor', 'pointer')
      .on('click', (event, d) => {
        event.stopPropagation()
        if (options.onEdgeSelect) options.onEdgeSelect(d)
      })
    edgeHitSel.merge(edgeHitEnter)
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y)

    const edgeEnter = edgeSel.enter().append('line')
      .attr('stroke', d => getEdgeColor(d.type || d.relation_type))
      .attr('stroke-width', 1)
      .attr('stroke-opacity', 0.4)
      .attr('pointer-events', 'none')
      .attr('marker-end', d => `url(#arrow-${d.type || d.relation_type || 'default'})`)

    edgeSel.merge(edgeEnter)
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y)

    // Nodes
    const nodeSel = gNodes.selectAll('circle')
      .data(_nodes, d => d.id)

    nodeSel.exit().remove()

    const nodeEnter = nodeSel.enter().append('circle')
      .attr('r', nodeRadius)
      .attr('fill', d => getNodeColor(d.type))
      .attr('stroke', '#0d1117')
      .attr('stroke-width', 1.5)
      .attr('cursor', 'pointer')
      .on('mouseenter', (event, d) => {
        if (options.onHover) options.onHover(d)
      })
      .on('mouseleave', (event, d) => {
        if (options.onUnhover) options.onUnhover(d)
      })
      .on('click', (event, d) => {
        event.stopPropagation()
        if (options.onSelect) options.onSelect(d)
      })
      .on('dblclick', (event, d) => {
        event.stopPropagation()
        if (options.onDblClick) options.onDblClick(d)
      })
      .call(dragBehavior)

    nodeSel.merge(nodeEnter)
      .attr('cx', d => d.x)
      .attr('cy', d => d.y)

    // Labels (visible on hover/select)
    const labelSel = gLabels.selectAll('text')
      .data(_nodes, d => d.id)

    labelSel.exit().remove()

    const labelEnter = labelSel.enter().append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', d => -nodeRadius(d) - 4)
      .attr('fill', '#c9d1d9')
      .attr('font-size', '11px')
      .attr('pointer-events', 'none')
      .attr('opacity', 0)

    labelSel.merge(labelEnter)
      .text(d => d.name || d.title || '')
      .attr('x', d => d.x)
      .attr('y', d => d.y)
  }

  // Public API: highlight a node and its neighbors
  function highlightNode(nodeId) {
    if (!gNodes || !gEdges) return
    const neighborSet = new Set()
    _edges.forEach(e => {
      const sid = typeof e.source === 'object' ? e.source.id : e.source
      const tid = typeof e.target === 'object' ? e.target.id : e.target
      if (sid === nodeId) neighborSet.add(tid)
      if (tid === nodeId) neighborSet.add(sid)
    })
    neighborSet.add(nodeId)

    gNodes.selectAll('circle')
      .attr('opacity', d => neighborSet.has(d.id) ? 1 : 0.15)
      .attr('filter', d => d.id === nodeId ? 'url(#glow)' : null)

    gEdges.selectAll('line')
      .attr('stroke-opacity', d => {
        const sid = typeof d.source === 'object' ? d.source.id : d.source
        const tid = typeof d.target === 'object' ? d.target.id : d.target
        return (sid === nodeId || tid === nodeId) ? 0.8 : 0.08
      })
      .attr('stroke-width', d => {
        const sid = typeof d.source === 'object' ? d.source.id : d.source
        const tid = typeof d.target === 'object' ? d.target.id : d.target
        return (sid === nodeId || tid === nodeId) ? 2 : 1
      })

    gLabels.selectAll('text')
      .attr('opacity', d => neighborSet.has(d.id) ? 1 : 0)

    return Array.from(neighborSet).filter(id => id !== nodeId)
  }

  function clearHighlight() {
    if (!gNodes || !gEdges) return
    gNodes.selectAll('circle')
      .attr('opacity', 1)
      .attr('filter', null)
    gEdges.selectAll('line')
      .attr('stroke-opacity', 0.4)
      .attr('stroke-width', 1)
    gLabels.selectAll('text')
      .attr('opacity', 0)
  }

  function selectNode(nodeId) {
    if (!gNodes || !gEdges) return
    clearHighlight()
    const neighbors = highlightNode(nodeId)
    return neighbors
  }

  function highlightQuery(query) {
    if (!gNodes || !gLabels) return
    if (!query) {
      clearHighlight()
      return
    }
    const q = query.toLowerCase()
    const matches = new Set()
    _nodes.forEach(n => {
      const name = (n.name || n.title || '').toLowerCase()
      const aliases = (n.aliases || []).map(a => a.toLowerCase())
      const summary = (n.summary || '').toLowerCase()
      if (name.includes(q) || aliases.some(a => a.includes(q)) || summary.includes(q)) {
        matches.add(n.id)
      }
    })

    gNodes.selectAll('circle')
      .attr('opacity', d => matches.has(d.id) ? 1 : 0.1)
      .attr('filter', d => matches.has(d.id) ? 'url(#glow)' : null)

    gLabels.selectAll('text')
      .attr('opacity', d => matches.has(d.id) ? 1 : 0)
  }

  function focusNode(nodeId) {
    const node = _nodes.find(n => n.id === nodeId)
    if (!node || !svgEl) return
    const svg = select(svgEl)
    const t = zoomIdentity
      .translate(width / 2, height / 2)
      .scale(2)
      .translate(-node.x, -node.y)
    svg.transition().duration(500).call(zoomBehavior.transform, t)
  }

  function fitAll() {
    if (!svgEl || !_nodes.length) return
    const svg = select(svgEl)
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity
    _nodes.forEach(n => {
      if (n.x < minX) minX = n.x
      if (n.x > maxX) maxX = n.x
      if (n.y < minY) minY = n.y
      if (n.y > maxY) maxY = n.y
    })
    const pad = 60
    const dx = (maxX - minX) + pad * 2
    const dy = (maxY - minY) + pad * 2
    const scale = Math.min(width / dx, height / dy, 2)
    const cx = (minX + maxX) / 2
    const cy = (minY + maxY) / 2
    const t = zoomIdentity
      .translate(width / 2, height / 2)
      .scale(scale)
      .translate(-cx, -cy)
    svg.transition().duration(500).call(zoomBehavior.transform, t)
  }

  function restart() {
    if (simulation.value) {
      simulation.value.alpha(0.8).restart()
    }
  }

  function updateData(nodes, edges) {
    _nodes = nodes.map(n => ({ ...n }))
    _edges = edges.map(e => ({ ...e }))

    if (simulation.value) {
      simulation.value.nodes(_nodes)
      simulation.value.force('link').links(_edges)
      simulation.value.alpha(0.5).restart()
    }
  }

  function getPositions() {
    return _nodes.map(n => {
      // Strip namespaced prefix (e.g. 'entity:12' → 12) for backend compatibility
      const rawId = n._rawId != null ? n._rawId : (typeof n.id === 'string' && n.id.includes(':') ? Number(n.id.split(':')[1]) : n.id)
      return {
        id: rawId,
        x: n.x,
        y: n.y,
      }
    })
  }

  function pinNode(id, x, y) {
    const node = _nodes.find(n => n.id === id)
    if (node) {
      node.fx = x
      node.fy = y
    }
  }

  function unpinNode(id) {
    const node = _nodes.find(n => n.id === id)
    if (node) {
      node.fx = null
      node.fy = null
    }
  }

  function destroy() {
    if (simulation.value) {
      simulation.value.stop()
      simulation.value = null
    }
  }

  return {
    svgRef,
    simulation,
    zoomTransform,
    init,
    render,
    highlightNode,
    clearHighlight,
    selectNode,
    highlightQuery,
    focusNode,
    fitAll,
    restart,
    updateData,
    getPositions,
    pinNode,
    unpinNode,
    destroy,
    getNodeColor,
    getEdgeColor,
    NODE_TYPE_COLORS,
    EDGE_TYPE_COLORS,
  }
}

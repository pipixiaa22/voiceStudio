# server/services/novel/narrative_state.py
from dataclasses import dataclass, field
from server.models.novel.project import NovelProject
from server.models.novel.outline import NovelOutlineNode
from server.models.novel.chapter import NovelChapter
from server.models.novel.entity import NovelEntity, NovelRelation
from server.models.novel.event import NovelEvent, NovelEventRelation
from server.models.novel.memory import NovelMemory


@dataclass
class NarrativeState:
    project: NovelProject
    overall_outline: dict = field(default_factory=dict)
    current_volume: NovelOutlineNode | None = None
    current_chapter_outline: NovelOutlineNode | None = None
    characters: list = field(default_factory=list)
    relations: list = field(default_factory=list)
    events: list = field(default_factory=list)
    event_relations: list = field(default_factory=list)
    memories: list = field(default_factory=list)
    open_foreshadowing: list = field(default_factory=list)
    recent_chapters: list = field(default_factory=list)
    world_settings: dict = field(default_factory=dict)


def load_state(project_id, chapter_id=None):
    """Load all narrative context from the database."""
    project = NovelProject.query.get_or_404(project_id)
    settings = project.settings or {}

    # Overall outline
    overall_outline = settings.get('overall_outline') or {}

    # Current chapter outline and volume
    current_chapter_outline = None
    current_volume = None
    chapter = None
    if chapter_id:
        chapter = NovelChapter.query.get(chapter_id)
    else:
        # Auto-detect: get the latest confirmed chapter
        chapter = NovelChapter.query.filter(
            NovelChapter.project_id == project_id,
            NovelChapter.status == 'confirmed',
        ).order_by(NovelChapter.order_index.desc()).first()

    if chapter and chapter.outline_node_id:
        current_chapter_outline = NovelOutlineNode.query.get(chapter.outline_node_id)
        if current_chapter_outline and current_chapter_outline.parent_id:
            parent = NovelOutlineNode.query.get(current_chapter_outline.parent_id)
            if parent and parent.node_type == 'volume':
                current_volume = parent

    # Characters (top 10 by importance)
    characters = NovelEntity.query.filter_by(
        project_id=project_id, entity_type='character',
    ).order_by(NovelEntity.importance.desc()).limit(10).all()

    # Relations (active, up to 20)
    relations = NovelRelation.query.filter_by(
        project_id=project_id, status='active',
    ).limit(20).all()

    # Events (up to 10 by timeline)
    events = NovelEvent.query.filter_by(
        project_id=project_id,
    ).order_by(NovelEvent.timeline_order.desc()).limit(10).all()

    # Event relations (up to 10)
    event_relations = NovelEventRelation.query.filter_by(
        project_id=project_id,
    ).limit(10).all()

    # Memories (active, up to 15 by importance)
    memories = NovelMemory.query.filter_by(
        project_id=project_id, status='active',
    ).order_by(NovelMemory.importance.desc()).limit(15).all()

    # Open foreshadowing from outline nodes
    open_foreshadowing = []
    nodes = NovelOutlineNode.query.filter_by(project_id=project_id).all()
    for node in nodes:
        if node.foreshadowing:
            open_foreshadowing.extend(node.foreshadowing)

    # Recent confirmed chapters (up to 5)
    recent_chapters = NovelChapter.query.filter(
        NovelChapter.project_id == project_id,
        NovelChapter.status == 'confirmed',
    ).order_by(NovelChapter.order_index.desc()).limit(5).all()

    # World settings (excluding overall_outline which is handled separately)
    world_settings = {k: v for k, v in settings.items() if k != 'overall_outline'}

    return NarrativeState(
        project=project,
        overall_outline=overall_outline,
        current_volume=current_volume,
        current_chapter_outline=current_chapter_outline,
        characters=characters,
        relations=relations,
        events=events,
        event_relations=event_relations,
        memories=memories,
        open_foreshadowing=open_foreshadowing,
        recent_chapters=recent_chapters,
        world_settings=world_settings,
    )

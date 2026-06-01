# Voice Workflow Studio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a first-version linear voice workflow studio where users can create, save, edit, audition, and export per-sentence TTS narration workflows.

**Architecture:** Add a persisted voice workflow layer beside the existing TTS sync-package flow. The backend owns workflow validation, segment planning, emotional TTS export, and ZIP packaging; the frontend owns the visual editor, inspector, timeline, and API state. The existing `VoiceSynthModal.vue` and `/api/tts/sync-package-v2` remain compatible.

**Tech Stack:** Python 3.13, Flask, Flask-SQLAlchemy, pytest, Vue 3, Pinia, Vite, Ant Design Vue, `@vue-flow/core`, `@vue-flow/background`, `@vue-flow/controls`.

---

## Scope

This plan implements the first version from `docs/superpowers/specs/2026-05-29-voice-workflow-studio-design.md`.

Included:

- Linear workflows only.
- Workflow CRUD.
- Segment planning from text.
- Segment emotion and voice settings.
- Single-segment audition.
- Full workflow ZIP export.
- Frontend workbench page with canvas, inspector, source panel, toolbar, and timeline.

Deferred:

- Branching workflows.
- Async export jobs.
- Video generation integration.
- Multi-track audio editing.
- LUFS normalization and waveform editing.

## File Map

Backend creates:

- `server/models/voice_workflow.py` - SQLAlchemy models and serializers for workflows, segments, and edges.
- `server/services/voice_workflow_service.py` - workflow snapshot saving, linear validation, ordering, manifest building, and cache fingerprinting.
- `server/services/emotion_planner.py` - emotion presets, `EmotionSegment`, rule-based workflow segment planning, and delivery instructions.
- `server/services/audio_postprocess.py` - per-segment WAV gain, pause insertion, clipping prevention, and emotional timeline building.
- `server/services/emotional_tts.py` - segment-level TTS synthesis using voice profile prompts and emotion instructions.
- `server/routes/voice_workflows.py` - REST API for workflow CRUD, segment planning, audition, and export.
- `server/tests/test_voice_workflow_service.py` - service tests.
- `server/tests/test_voice_workflows_routes.py` - route tests.
- `server/tests/test_emotion_planner.py` - planner tests.
- `server/tests/test_audio_postprocess.py` - audio postprocess tests.

Backend modifies:

- `server/models/__init__.py` - export new models.
- `server/app.py` - register the new blueprint.
- `server/services/tts_provider.py` - accept optional `emotion_options` for future adapter compatibility.

Frontend creates:

- `web/src/views/VoiceWorkflowView.vue` - main workbench page.
- `web/src/views/VoiceWorkflowList.vue` - minimal project list and new-project entry.
- `web/src/components/voice-workflow/WorkflowToolbar.vue`
- `web/src/components/voice-workflow/SourcePanel.vue`
- `web/src/components/voice-workflow/VoiceFlowCanvas.vue`
- `web/src/components/voice-workflow/VoiceSegmentNode.vue`
- `web/src/components/voice-workflow/SegmentInspector.vue`
- `web/src/components/voice-workflow/TimelineAuditionBar.vue`
- `web/src/stores/voiceWorkflows.js`

Frontend modifies:

- `web/package.json` and `web/pnpm-lock.yaml` - add `@vue-flow/core`, `@vue-flow/background`, and `@vue-flow/controls`.
- `web/src/api/index.js` - add `voiceWorkflowsApi`.
- `web/src/router/index.js` - add voice workflow routes.
- `web/src/App.vue` - add navigation entry.

---

### Task 1: Backend Models And Serializers

**Files:**

- Create: `server/models/voice_workflow.py`
- Modify: `server/models/__init__.py`
- Test: `server/tests/test_voice_workflow_service.py`

- [ ] **Step 1: Write failing model serialization tests**

Create `server/tests/test_voice_workflow_service.py` with:

```python
from server.models import db
from server.models.voice_workflow import VoiceWorkflow, VoiceWorkflowEdge, VoiceWorkflowSegment


def test_voice_workflow_to_dict_includes_segments_and_edges(app):
    workflow = VoiceWorkflow(title='试音工程', source_content='我知道了。')
    db.session.add(workflow)
    db.session.flush()
    first = VoiceWorkflowSegment(
        workflow_id=workflow.id,
        order_index=1,
        text='我知道了。',
        node_x=80,
        node_y=120,
        emotion='calm',
        intensity=0.3,
        rate=0.95,
        pitch=-1,
        volume_db=0,
        pause_before_ms=0,
        pause_after_ms=250,
        transition='normal',
        audio_status='missing',
    )
    second = VoiceWorkflowSegment(
        workflow_id=workflow.id,
        order_index=2,
        text='可是你为什么现在才告诉我！',
        node_x=320,
        node_y=180,
        emotion='angry_burst',
        intensity=1.6,
        rate=1.15,
        pitch=2,
        volume_db=3,
        pause_before_ms=80,
        pause_after_ms=180,
        transition='burst',
        audio_status='missing',
    )
    db.session.add_all([first, second])
    db.session.flush()
    db.session.add(VoiceWorkflowEdge(
        workflow_id=workflow.id,
        source_segment_id=first.id,
        target_segment_id=second.id,
        order_index=1,
    ))
    db.session.commit()

    data = workflow.to_dict(include_children=True)

    assert data['title'] == '试音工程'
    assert data['source_content'] == '我知道了。'
    assert [item['text'] for item in data['segments']] == [
        '我知道了。',
        '可是你为什么现在才告诉我！',
    ]
    assert data['segments'][1]['emotion'] == 'angry_burst'
    assert data['edges'][0]['source_segment_id'] == first.id
    assert data['edges'][0]['target_segment_id'] == second.id
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
uv run pytest server/tests/test_voice_workflow_service.py::test_voice_workflow_to_dict_includes_segments_and_edges -v
```

Expected: FAIL with `ModuleNotFoundError` or import error for `server.models.voice_workflow`.

- [ ] **Step 3: Implement the models**

Create `server/models/voice_workflow.py`:

```python
import json
from datetime import datetime, timezone

from server.models.base import db


def _now():
    return datetime.now(timezone.utc)


def _json_loads(value, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def _json_dumps(value):
    return json.dumps(value or {}, ensure_ascii=False)


class VoiceWorkflow(db.Model):
    __tablename__ = 'voice_workflows'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, default='未命名配音工程')
    source_text_id = db.Column(db.Integer, db.ForeignKey('texts.id'), nullable=True)
    source_content = db.Column(db.Text, nullable=False, default='')
    default_voice_profile_id = db.Column(db.Integer, nullable=True)
    settings_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    segments = db.relationship(
        'VoiceWorkflowSegment',
        backref='workflow',
        lazy=True,
        cascade='all, delete-orphan',
        order_by='VoiceWorkflowSegment.order_index',
    )
    edges = db.relationship(
        'VoiceWorkflowEdge',
        backref='workflow',
        lazy=True,
        cascade='all, delete-orphan',
        order_by='VoiceWorkflowEdge.order_index',
    )

    @property
    def settings(self):
        return _json_loads(self.settings_json, {})

    @settings.setter
    def settings(self, value):
        self.settings_json = _json_dumps(value)

    def to_dict(self, include_children=False):
        data = {
            'id': self.id,
            'title': self.title,
            'source_text_id': self.source_text_id,
            'source_content': self.source_content,
            'default_voice_profile_id': self.default_voice_profile_id,
            'settings': self.settings,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_children:
            data['segments'] = [segment.to_dict() for segment in self.segments]
            data['edges'] = [edge.to_dict() for edge in self.edges]
        return data


class VoiceWorkflowSegment(db.Model):
    __tablename__ = 'voice_workflow_segments'

    id = db.Column(db.Integer, primary_key=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey('voice_workflows.id'), nullable=False)
    order_index = db.Column(db.Integer, nullable=False, default=1)
    text = db.Column(db.Text, nullable=False, default='')
    node_x = db.Column(db.Float, nullable=False, default=0)
    node_y = db.Column(db.Float, nullable=False, default=0)
    emotion = db.Column(db.String(50), nullable=False, default='neutral')
    intensity = db.Column(db.Float, nullable=False, default=0.5)
    rate = db.Column(db.Float, nullable=False, default=1.0)
    pitch = db.Column(db.Float, nullable=False, default=0.0)
    volume_db = db.Column(db.Float, nullable=False, default=0.0)
    pause_before_ms = db.Column(db.Integer, nullable=False, default=0)
    pause_after_ms = db.Column(db.Integer, nullable=False, default=250)
    transition = db.Column(db.String(50), nullable=False, default='normal')
    delivery_instruction = db.Column(db.Text, nullable=False, default='')
    voice_profile_id = db.Column(db.Integer, nullable=True)
    audio_status = db.Column(db.String(30), nullable=False, default='missing')
    audio_path = db.Column(db.Text, nullable=True)
    audio_fingerprint = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=_now)
    updated_at = db.Column(db.DateTime, default=_now, onupdate=_now)

    def to_dict(self):
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'order_index': self.order_index,
            'text': self.text,
            'node_x': self.node_x,
            'node_y': self.node_y,
            'emotion': self.emotion,
            'intensity': self.intensity,
            'rate': self.rate,
            'pitch': self.pitch,
            'volume_db': self.volume_db,
            'pause_before_ms': self.pause_before_ms,
            'pause_after_ms': self.pause_after_ms,
            'transition': self.transition,
            'delivery_instruction': self.delivery_instruction,
            'voice_profile_id': self.voice_profile_id,
            'audio_status': self.audio_status,
            'audio_path': self.audio_path,
            'audio_fingerprint': self.audio_fingerprint,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class VoiceWorkflowEdge(db.Model):
    __tablename__ = 'voice_workflow_edges'

    id = db.Column(db.Integer, primary_key=True)
    workflow_id = db.Column(db.Integer, db.ForeignKey('voice_workflows.id'), nullable=False)
    source_segment_id = db.Column(db.Integer, db.ForeignKey('voice_workflow_segments.id'), nullable=False)
    target_segment_id = db.Column(db.Integer, db.ForeignKey('voice_workflow_segments.id'), nullable=False)
    order_index = db.Column(db.Integer, nullable=False, default=1)

    def to_dict(self):
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'source_segment_id': self.source_segment_id,
            'target_segment_id': self.target_segment_id,
            'order_index': self.order_index,
        }
```

Modify `server/models/__init__.py`:

```python
from server.models.voice_workflow import VoiceWorkflow, VoiceWorkflowSegment, VoiceWorkflowEdge
```

Add these names to `__all__`:

```python
'VoiceWorkflow', 'VoiceWorkflowSegment', 'VoiceWorkflowEdge',
```

- [ ] **Step 4: Run the model test**

Run:

```bash
uv run pytest server/tests/test_voice_workflow_service.py::test_voice_workflow_to_dict_includes_segments_and_edges -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add server/models/voice_workflow.py server/models/__init__.py server/tests/test_voice_workflow_service.py
git commit -m "feat: add voice workflow models"
```

---

### Task 2: Emotion Planner And Linear Workflow Service

**Files:**

- Create: `server/services/emotion_planner.py`
- Create: `server/services/voice_workflow_service.py`
- Modify: `server/tests/test_voice_workflow_service.py`
- Test: `server/tests/test_emotion_planner.py`

- [ ] **Step 1: Write failing emotion planner tests**

Create `server/tests/test_emotion_planner.py`:

```python
from server.services.emotion_planner import (
    build_segment_delivery_instruction,
    plan_workflow_segments,
)


def test_plan_workflow_segments_detects_burst_from_punctuation():
    segments = plan_workflow_segments('我知道了。可是你为什么现在才告诉我！', max_chars=80)

    assert [segment['text'] for segment in segments] == [
        '我知道了。',
        '可是你为什么现在才告诉我！',
    ]
    assert segments[0]['emotion'] == 'calm'
    assert segments[1]['emotion'] == 'angry_burst'
    assert segments[1]['pause_before_ms'] == 80


def test_delivery_instruction_mentions_same_speaker_and_emotion():
    instruction = build_segment_delivery_instruction({
        'emotion': 'angry_burst',
        'intensity': 1.6,
        'rate': 1.15,
        'pitch': 2,
        'volume_db': 3,
        'transition': 'burst',
        'delivery_instruction': '',
    })

    assert '同一个说话人音色' in instruction
    assert '突然爆发' in instruction
    assert '语速加快' in instruction
    assert '不要像换了一个人' in instruction
```

- [ ] **Step 2: Extend service tests for validation and snapshot saving**

Append to `server/tests/test_voice_workflow_service.py`:

```python
import pytest

from server.models.voice_workflow import VoiceWorkflow
from server.services.voice_workflow_service import (
    build_audio_fingerprint,
    save_workflow_snapshot,
    validate_linear_edges,
)


def test_validate_linear_edges_rejects_branching():
    segments = [{'id': 1}, {'id': 2}, {'id': 3}]
    edges = [
        {'source_segment_id': 1, 'target_segment_id': 2},
        {'source_segment_id': 1, 'target_segment_id': 3},
    ]

    with pytest.raises(ValueError, match='最多只能连接一个后继'):
        validate_linear_edges(segments, edges)


def test_save_workflow_snapshot_replaces_segments_and_edges(app):
    workflow = VoiceWorkflow(title='旧工程', source_content='旧内容')
    db.session.add(workflow)
    db.session.commit()

    data = save_workflow_snapshot(workflow.id, {
        'workflow': {
            'title': '新工程',
            'source_content': '我知道了。可是你为什么现在才告诉我！',
            'settings': {'subtitle_max_chars': 20},
        },
        'segments': [
            {'order_index': 1, 'text': '我知道了。', 'emotion': 'calm', 'node_x': 80, 'node_y': 120},
            {'order_index': 2, 'text': '可是你为什么现在才告诉我！', 'emotion': 'angry_burst', 'node_x': 320, 'node_y': 180},
        ],
        'edges': [
            {'source_client_id': 0, 'target_client_id': 1, 'order_index': 1},
        ],
    })

    assert data['title'] == '新工程'
    assert len(data['segments']) == 2
    assert len(data['edges']) == 1
    assert data['segments'][1]['audio_status'] == 'missing'


def test_audio_fingerprint_changes_when_parameters_change():
    first = build_audio_fingerprint({
        'text': '我知道了。',
        'emotion': 'calm',
        'intensity': 0.3,
        'rate': 0.95,
        'volume_db': 0,
        'voice_profile_id': 9,
        'model': 'mimo-v2.5-tts-voicedesign',
    })
    second = build_audio_fingerprint({
        'text': '我知道了。',
        'emotion': 'angry_burst',
        'intensity': 1.6,
        'rate': 1.15,
        'volume_db': 3,
        'voice_profile_id': 9,
        'model': 'mimo-v2.5-tts-voicedesign',
    })

    assert first.startswith('sha256:')
    assert first != second
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
uv run pytest server/tests/test_emotion_planner.py server/tests/test_voice_workflow_service.py -v
```

Expected: FAIL because `emotion_planner.py` and `voice_workflow_service.py` do not exist.

- [ ] **Step 4: Implement `emotion_planner.py`**

Create `server/services/emotion_planner.py`:

```python
from dataclasses import dataclass, field
import re

from splitter import split_text


EMOTION_PRESETS = {
    'neutral': {'intensity': 0.5, 'rate': 1.0, 'pitch': 0, 'volume_db': 0, 'pause_after_ms': 250},
    'calm': {'intensity': 0.25, 'rate': 0.95, 'pitch': -1, 'volume_db': -1, 'pause_after_ms': 250},
    'suppressed': {'intensity': 0.55, 'rate': 0.9, 'pitch': -1, 'volume_db': -2, 'pause_after_ms': 350},
    'angry_burst': {'intensity': 1.6, 'rate': 1.15, 'pitch': 2, 'volume_db': 3, 'pause_after_ms': 180},
    'sad': {'intensity': 0.8, 'rate': 0.85, 'pitch': -2, 'volume_db': -1, 'pause_after_ms': 500},
    'cold': {'intensity': 0.7, 'rate': 0.8, 'pitch': -2, 'volume_db': -2, 'pause_after_ms': 450},
    'excited': {'intensity': 1.2, 'rate': 1.12, 'pitch': 1, 'volume_db': 2, 'pause_after_ms': 180},
    'whisper': {'intensity': 0.4, 'rate': 0.85, 'pitch': -2, 'volume_db': -4, 'pause_after_ms': 420},
}


@dataclass
class EmotionSegment:
    index: int
    text: str
    subtitle_indices: list[int] = field(default_factory=list)
    emotion: str = 'neutral'
    intensity: float = 0.5
    rate: float = 1.0
    pitch: float = 0.0
    volume_db: float = 0.0
    pause_before_ms: int = 0
    pause_after_ms: int = 250
    transition: str = 'normal'
    delivery_instruction: str = ''
    voice_profile_id: int | None = None


def _detect_emotion(text: str) -> str:
    if re.search(r'[!！]{1,}|[?？][!！]|[!！][?？]', text):
        return 'angry_burst'
    if any(word in text for word in ('为什么', '凭什么', '你怎么敢')):
        return 'angry_burst'
    if any(word in text for word in ('算了', '不必了', '我没事')):
        return 'cold'
    if '……' in text or text.count('.') >= 3:
        return 'suppressed'
    return 'calm'


def _preset_payload(emotion: str) -> dict:
    preset = EMOTION_PRESETS.get(emotion, EMOTION_PRESETS['neutral'])
    return {
        'emotion': emotion,
        'intensity': preset['intensity'],
        'rate': preset['rate'],
        'pitch': preset['pitch'],
        'volume_db': preset['volume_db'],
        'pause_before_ms': 80 if emotion == 'angry_burst' else 0,
        'pause_after_ms': preset['pause_after_ms'],
        'transition': 'burst' if emotion == 'angry_burst' else 'normal',
        'delivery_instruction': '',
    }


def plan_workflow_segments(content: str, max_chars: int = 80) -> list[dict]:
    segments = []
    for index, text in enumerate(split_text(content or '', max_chars=max_chars), 1):
        clean_text = text.strip()
        if not clean_text:
            continue
        emotion = _detect_emotion(clean_text)
        payload = _preset_payload(emotion)
        payload.update({
            'order_index': index,
            'text': clean_text,
            'node_x': 80 + (index - 1) * 240,
            'node_y': 120 + ((index - 1) % 2) * 80,
            'voice_profile_id': None,
            'audio_status': 'missing',
        })
        segments.append(payload)
    return segments


def build_segment_delivery_instruction(segment: EmotionSegment | dict) -> str:
    get = segment.get if isinstance(segment, dict) else lambda key, default=None: getattr(segment, key, default)
    emotion = get('emotion', 'neutral')
    transition = get('transition', 'normal')
    rate = float(get('rate', 1.0))
    volume_db = float(get('volume_db', 0.0))
    custom = (get('delivery_instruction', '') or '').strip()

    emotion_text = {
        'calm': '平静、克制、自然',
        'suppressed': '压抑、低声、保留情绪',
        'angry_burst': '情绪突然爆发，重音更强',
        'sad': '悲伤、放慢、带停顿',
        'cold': '冷漠、疏离、压低声音',
        'excited': '兴奋、明亮、节奏更快',
        'whisper': '接近耳语，气声更明显',
    }.get(emotion, '自然中性')
    transition_text = '这句话紧接上一句，仍使用同一个说话人音色。'
    if transition == 'burst':
        transition_text = '这句话从上一句突然爆发，但仍使用同一个说话人音色。'

    rate_text = '语速保持自然。'
    if rate > 1.05:
        rate_text = '语速加快，但吐字保持清楚。'
    elif rate < 0.95:
        rate_text = '语速放慢，停顿更明显。'

    volume_text = '音量保持自然。'
    if volume_db > 1:
        volume_text = '音量提高，重音更强。'
    elif volume_db < -1:
        volume_text = '音量压低，表达更内收。'

    lines = [
        transition_text,
        f'表演方式：{emotion_text}。',
        rate_text,
        volume_text,
        '边界：不要破音，不要像换了一个人，不要夸张到卡通化。',
    ]
    if custom:
        lines.append(f'用户补充：{custom}')
    return '\n'.join(lines)
```

- [ ] **Step 5: Implement `voice_workflow_service.py`**

Create `server/services/voice_workflow_service.py`:

```python
import hashlib
import json

from server.models import db
from server.models.voice_workflow import VoiceWorkflow, VoiceWorkflowEdge, VoiceWorkflowSegment


def _clamp_float(value, minimum, maximum, default):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _clamp_int(value, minimum, maximum, default):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def validate_linear_edges(segments, edges) -> list[int]:
    ids = {item['id'] for item in segments if item.get('id') is not None}
    outgoing = {}
    incoming = {}
    for edge in edges:
        source = edge.get('source_segment_id')
        target = edge.get('target_segment_id')
        if source not in ids or target not in ids:
            raise ValueError('连线引用了不存在的语句节点')
        outgoing[source] = outgoing.get(source, 0) + 1
        incoming[target] = incoming.get(target, 0) + 1
        if outgoing[source] > 1:
            raise ValueError('每个语句节点最多只能连接一个后继')
        if incoming[target] > 1:
            raise ValueError('每个语句节点最多只能连接一个前驱')
    return [item['id'] for item in sorted(segments, key=lambda item: item.get('order_index', 0))]


def build_audio_fingerprint(segment: dict) -> str:
    payload = {
        'text': segment.get('text', ''),
        'emotion': segment.get('emotion', 'neutral'),
        'intensity': segment.get('intensity', 0.5),
        'rate': segment.get('rate', 1.0),
        'pitch': segment.get('pitch', 0),
        'volume_db': segment.get('volume_db', 0),
        'pause_before_ms': segment.get('pause_before_ms', 0),
        'pause_after_ms': segment.get('pause_after_ms', 250),
        'transition': segment.get('transition', 'normal'),
        'delivery_instruction': segment.get('delivery_instruction', ''),
        'voice_profile_id': segment.get('voice_profile_id'),
        'model': segment.get('model', 'mimo-v2.5-tts-voicedesign'),
    }
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()
    return f'sha256:{digest}'


def _segment_from_payload(workflow_id: int, payload: dict, index: int) -> VoiceWorkflowSegment:
    return VoiceWorkflowSegment(
        workflow_id=workflow_id,
        order_index=_clamp_int(payload.get('order_index'), 1, 100000, index + 1),
        text=(payload.get('text') or '').strip(),
        node_x=_clamp_float(payload.get('node_x'), -100000, 100000, 80 + index * 240),
        node_y=_clamp_float(payload.get('node_y'), -100000, 100000, 120),
        emotion=payload.get('emotion') or 'neutral',
        intensity=_clamp_float(payload.get('intensity'), 0.0, 2.0, 0.5),
        rate=_clamp_float(payload.get('rate'), 0.5, 2.0, 1.0),
        pitch=_clamp_float(payload.get('pitch'), -12.0, 12.0, 0.0),
        volume_db=_clamp_float(payload.get('volume_db'), -12.0, 12.0, 0.0),
        pause_before_ms=_clamp_int(payload.get('pause_before_ms'), 0, 10000, 0),
        pause_after_ms=_clamp_int(payload.get('pause_after_ms'), 0, 10000, 250),
        transition=payload.get('transition') or 'normal',
        delivery_instruction=payload.get('delivery_instruction') or '',
        voice_profile_id=payload.get('voice_profile_id'),
        audio_status='missing',
    )


def save_workflow_snapshot(workflow_id: int, payload: dict) -> dict:
    workflow = VoiceWorkflow.query.get_or_404(workflow_id)
    workflow_data = payload.get('workflow') or {}
    workflow.title = workflow_data.get('title') or workflow.title
    workflow.source_content = workflow_data.get('source_content', workflow.source_content)
    workflow.source_text_id = workflow_data.get('source_text_id', workflow.source_text_id)
    workflow.default_voice_profile_id = workflow_data.get('default_voice_profile_id', workflow.default_voice_profile_id)
    workflow.settings = workflow_data.get('settings', workflow.settings)

    for segment in list(workflow.segments):
        db.session.delete(segment)
    for edge in list(workflow.edges):
        db.session.delete(edge)
    db.session.flush()

    created_segments = []
    for index, segment_payload in enumerate(payload.get('segments') or []):
        segment = _segment_from_payload(workflow.id, segment_payload, index)
        if not segment.text:
            raise ValueError('语句文本不能为空')
        db.session.add(segment)
        created_segments.append(segment)
    db.session.flush()

    edge_payloads = []
    for edge_payload in payload.get('edges') or []:
        source_client_id = edge_payload.get('source_client_id')
        target_client_id = edge_payload.get('target_client_id')
        source = created_segments[source_client_id] if isinstance(source_client_id, int) else None
        target = created_segments[target_client_id] if isinstance(target_client_id, int) else None
        if not source or not target:
            continue
        edge_payloads.append({
            'source_segment_id': source.id,
            'target_segment_id': target.id,
            'order_index': edge_payload.get('order_index', len(edge_payloads) + 1),
        })

    validate_linear_edges([segment.to_dict() for segment in created_segments], edge_payloads)
    for edge_payload in edge_payloads:
        db.session.add(VoiceWorkflowEdge(workflow_id=workflow.id, **edge_payload))

    db.session.commit()
    return workflow.to_dict(include_children=True)


def ordered_segments(workflow: VoiceWorkflow) -> list[VoiceWorkflowSegment]:
    return sorted(workflow.segments, key=lambda segment: segment.order_index)


def build_workflow_manifest(workflow: VoiceWorkflow, segments: list[dict], timeline: list[dict]) -> dict:
    return {
        'title': workflow.title,
        'source': 'voice_workflow',
        'workflow_id': workflow.id,
        'segments': segments,
        'edges': [edge.to_dict() for edge in workflow.edges],
        'subtitles': timeline,
        'total_duration': round(timeline[-1]['end'], 3) if timeline else 0,
    }
```

- [ ] **Step 6: Run service and planner tests**

Run:

```bash
uv run pytest server/tests/test_emotion_planner.py server/tests/test_voice_workflow_service.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add server/services/emotion_planner.py server/services/voice_workflow_service.py server/tests/test_emotion_planner.py server/tests/test_voice_workflow_service.py
git commit -m "feat: add voice workflow planning services"
```

---

### Task 3: Workflow CRUD And Segment Planning Routes

**Files:**

- Create: `server/routes/voice_workflows.py`
- Modify: `server/app.py`
- Test: `server/tests/test_voice_workflows_routes.py`

- [ ] **Step 1: Write failing route tests**

Create `server/tests/test_voice_workflows_routes.py`:

```python
def test_create_voice_workflow_from_content(client):
    response = client.post('/api/voice-workflows', json={
        'title': '试音工程',
        'source_content': '我知道了。可是你为什么现在才告诉我！',
        'default_voice_profile_id': 9,
    })

    assert response.status_code == 201
    data = response.get_json()
    assert data['title'] == '试音工程'
    assert len(data['segments']) == 2
    assert data['segments'][1]['emotion'] == 'angry_burst'
    assert len(data['edges']) == 1


def test_update_voice_workflow_snapshot(client):
    created = client.post('/api/voice-workflows', json={
        'title': '旧工程',
        'source_content': '旧内容。',
    }).get_json()

    response = client.put(f"/api/voice-workflows/{created['id']}", json={
        'workflow': {'title': '新工程', 'source_content': '新内容。'},
        'segments': [
            {'order_index': 1, 'text': '新内容。', 'emotion': 'calm', 'node_x': 80, 'node_y': 120},
        ],
        'edges': [],
    })

    assert response.status_code == 200
    data = response.get_json()
    assert data['title'] == '新工程'
    assert data['segments'][0]['text'] == '新内容。'


def test_plan_segments_endpoint_returns_rule_segments(client):
    created = client.post('/api/voice-workflows', json={'title': '空工程'}).get_json()

    response = client.post(f"/api/voice-workflows/{created['id']}/segments/plan", json={
        'content': '算了，不必解释。可是你为什么现在才告诉我！',
        'max_chars': 80,
    })

    assert response.status_code == 200
    data = response.get_json()
    assert [segment['emotion'] for segment in data['segments']] == ['cold', 'angry_burst']


def test_delete_voice_workflow(client):
    created = client.post('/api/voice-workflows', json={'title': '待删除'}).get_json()

    response = client.delete(f"/api/voice-workflows/{created['id']}")

    assert response.status_code == 204
    assert client.get(f"/api/voice-workflows/{created['id']}").status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest server/tests/test_voice_workflows_routes.py -v
```

Expected: FAIL with 404 responses because the blueprint is not registered.

- [ ] **Step 3: Implement routes**

Create `server/routes/voice_workflows.py`:

```python
from flask import Blueprint, jsonify, request

from server.models import db
from server.models.voice_workflow import VoiceWorkflow, VoiceWorkflowEdge, VoiceWorkflowSegment
from server.services.emotion_planner import plan_workflow_segments
from server.services.voice_workflow_service import save_workflow_snapshot

voice_workflows_bp = Blueprint('voice_workflows', __name__)


def _create_edges_for_segments(workflow_id, segments):
    edges = []
    for index in range(len(segments) - 1):
        edge = VoiceWorkflowEdge(
            workflow_id=workflow_id,
            source_segment_id=segments[index].id,
            target_segment_id=segments[index + 1].id,
            order_index=index + 1,
        )
        db.session.add(edge)
        edges.append(edge)
    return edges


@voice_workflows_bp.route('/api/voice-workflows', methods=['GET'])
def list_voice_workflows():
    workflows = VoiceWorkflow.query.order_by(VoiceWorkflow.updated_at.desc()).all()
    return jsonify([workflow.to_dict(include_children=False) for workflow in workflows])


@voice_workflows_bp.route('/api/voice-workflows', methods=['POST'])
def create_voice_workflow():
    data = request.get_json() or {}
    workflow = VoiceWorkflow(
        title=data.get('title') or '未命名配音工程',
        source_text_id=data.get('source_text_id'),
        source_content=data.get('source_content') or '',
        default_voice_profile_id=data.get('default_voice_profile_id'),
    )
    workflow.settings = data.get('settings') or {'subtitle_max_chars': 20, 'segment_max_chars': 80}
    db.session.add(workflow)
    db.session.flush()

    created_segments = []
    for segment_data in plan_workflow_segments(workflow.source_content, max_chars=workflow.settings.get('segment_max_chars', 80)):
        segment = VoiceWorkflowSegment(workflow_id=workflow.id, **segment_data)
        db.session.add(segment)
        created_segments.append(segment)
    db.session.flush()
    _create_edges_for_segments(workflow.id, created_segments)
    db.session.commit()
    return jsonify(workflow.to_dict(include_children=True)), 201


@voice_workflows_bp.route('/api/voice-workflows/<int:workflow_id>', methods=['GET'])
def get_voice_workflow(workflow_id):
    workflow = VoiceWorkflow.query.get_or_404(workflow_id)
    return jsonify(workflow.to_dict(include_children=True))


@voice_workflows_bp.route('/api/voice-workflows/<int:workflow_id>', methods=['PUT'])
def update_voice_workflow(workflow_id):
    data = request.get_json() or {}
    try:
        result = save_workflow_snapshot(workflow_id, data)
    except ValueError as exc:
        db.session.rollback()
        return jsonify({'error': str(exc)}), 400
    return jsonify(result)


@voice_workflows_bp.route('/api/voice-workflows/<int:workflow_id>', methods=['DELETE'])
def delete_voice_workflow(workflow_id):
    workflow = VoiceWorkflow.query.get_or_404(workflow_id)
    db.session.delete(workflow)
    db.session.commit()
    return '', 204


@voice_workflows_bp.route('/api/voice-workflows/<int:workflow_id>/segments/plan', methods=['POST'])
def plan_voice_workflow_segments(workflow_id):
    VoiceWorkflow.query.get_or_404(workflow_id)
    data = request.get_json() or {}
    content = data.get('content') or ''
    max_chars = int(data.get('max_chars', 80))
    return jsonify({'segments': plan_workflow_segments(content, max_chars=max_chars)})
```

Modify `server/app.py` inside `create_app()` after the TTS blueprint import:

```python
from server.routes.voice_workflows import voice_workflows_bp
app.register_blueprint(voice_workflows_bp)
```

- [ ] **Step 4: Run route tests**

Run:

```bash
uv run pytest server/tests/test_voice_workflows_routes.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add server/routes/voice_workflows.py server/app.py server/tests/test_voice_workflows_routes.py
git commit -m "feat: add voice workflow routes"
```

---

### Task 4: Audio Postprocess, Emotional TTS, Audition, And Export

**Files:**

- Create: `server/services/audio_postprocess.py`
- Create: `server/services/emotional_tts.py`
- Modify: `server/services/tts_provider.py`
- Modify: `server/routes/voice_workflows.py`
- Test: `server/tests/test_audio_postprocess.py`
- Test: `server/tests/test_voice_workflows_routes.py`

- [ ] **Step 1: Write audio postprocess tests**

Create `server/tests/test_audio_postprocess.py`:

```python
import io
import wave

from server.services.audio_package import read_wav_info
from server.services.audio_postprocess import concat_emotional_wavs, build_emotional_subtitle_timeline


def _make_wav(duration_ms=100, sample_rate=8000, amplitude=1000):
    frames = int(sample_rate * duration_ms / 1000)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        sample = int(amplitude).to_bytes(2, byteorder='little', signed=True)
        wav.writeframes(sample * frames)
    return buf.getvalue()


def test_concat_emotional_wavs_applies_individual_pauses():
    wav1 = read_wav_info(_make_wav(100))
    wav2 = read_wav_info(_make_wav(100))

    audio = concat_emotional_wavs([
        {'wav_info': wav1, 'segment': {'pause_before_ms': 0, 'pause_after_ms': 250, 'volume_db': 0}},
        {'wav_info': wav2, 'segment': {'pause_before_ms': 80, 'pause_after_ms': 0, 'volume_db': 0}},
    ])

    info = read_wav_info(audio)
    assert info['frames'] == 800 + 2000 + 640 + 800


def test_build_emotional_subtitle_timeline_uses_pauses():
    timeline = build_emotional_subtitle_timeline([
        {'id': 1, 'text': '我知道了。', 'pause_before_ms': 0, 'pause_after_ms': 250},
        {'id': 2, 'text': '可是你为什么现在才告诉我！', 'pause_before_ms': 80, 'pause_after_ms': 180},
    ], [1.0, 2.0])

    assert timeline[0]['start'] == 0
    assert timeline[0]['end'] == 1
    assert timeline[1]['start'] == 1.33
    assert timeline[1]['end'] == 3.33
```

- [ ] **Step 2: Add route tests for audition and export**

Append to `server/tests/test_voice_workflows_routes.py`:

```python
import base64
import io
import json
import wave
import zipfile


def _make_wav(duration_seconds=1.0, framerate=8000):
    frame_count = int(duration_seconds * framerate)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(framerate)
        wav.writeframes(b'\x00\x00' * frame_count)
    return buf.getvalue()


def test_audition_segment_returns_audio(client, monkeypatch):
    created = client.post('/api/voice-workflows', json={
        'title': '试听工程',
        'source_content': '我知道了。',
    }).get_json()
    segment_id = created['segments'][0]['id']

    monkeypatch.setattr('server.routes.voice_workflows.repo.get_profile_by_id', lambda profile_id: None)

    class FakeProvider:
        def __init__(self, api_key):
            self.api_key = api_key

        def synthesize(self, **kwargs):
            return base64.b64encode(_make_wav()).decode('ascii')

    monkeypatch.setattr('server.services.emotional_tts.TTSProvider', FakeProvider)

    response = client.post(f"/api/voice-workflows/{created['id']}/segments/{segment_id}/audition", json={
        'api_key': 'test-key',
        'voice_description': '温柔女声',
    })

    assert response.status_code == 200
    data = response.get_json()
    assert data['audio_base64']
    assert data['duration'] == 1.0
    assert data['fingerprint'].startswith('sha256:')


def test_export_voice_workflow_zip(client, monkeypatch):
    created = client.post('/api/voice-workflows', json={
        'title': '导出工程',
        'source_content': '我知道了。可是你为什么现在才告诉我！',
    }).get_json()

    monkeypatch.setattr('server.routes.voice_workflows.repo.get_profile_by_id', lambda profile_id: None)

    class FakeProvider:
        def __init__(self, api_key):
            self.api_key = api_key

        def synthesize(self, **kwargs):
            return base64.b64encode(_make_wav()).decode('ascii')

    monkeypatch.setattr('server.services.emotional_tts.TTSProvider', FakeProvider)

    response = client.post(f"/api/voice-workflows/{created['id']}/export", json={
        'api_key': 'test-key',
        'voice_description': '温柔女声',
        'export_options': {'include_segment_wavs': True},
    })

    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.data)) as zf:
        names = zf.namelist()
        assert 'manifest.json' in names
        assert any(name.endswith('_完整音频.wav') for name in names)
        assert any(name.endswith('_同步字幕.srt') for name in names)
        assert 'segments/001.wav' in names
        manifest = json.loads(zf.read('manifest.json').decode('utf-8'))
        assert manifest['source'] == 'voice_workflow'
        assert len(manifest['segments']) == 2
```

- [ ] **Step 3: Run tests to verify they fail**

Run:

```bash
uv run pytest server/tests/test_audio_postprocess.py server/tests/test_voice_workflows_routes.py -v
```

Expected: FAIL because postprocess, emotional TTS, and export routes are not implemented.

- [ ] **Step 4: Implement audio postprocess**

Create `server/services/audio_postprocess.py`:

```python
import audioop
import io
import math
import wave


def _silence(info: dict, duration_ms: int) -> bytes:
    frames = round(info['framerate'] * duration_ms / 1000)
    return b'\x00' * frames * info['channels'] * info['sample_width']


def _apply_gain(frame_bytes: bytes, sample_width: int, volume_db: float) -> bytes:
    if not volume_db:
        return frame_bytes
    factor = math.pow(10, volume_db / 20)
    return audioop.mul(frame_bytes, sample_width, factor)


def concat_emotional_wavs(items: list[dict]) -> bytes:
    if not items:
        return b''
    base = items[0]['wav_info']
    for item in items[1:]:
        info = item['wav_info']
        if info['channels'] != base['channels'] or info['sample_width'] != base['sample_width'] or info['framerate'] != base['framerate']:
            raise ValueError('音频参数不一致，无法拼接')

    output = io.BytesIO()
    with wave.open(output, 'wb') as wav:
        wav.setnchannels(base['channels'])
        wav.setsampwidth(base['sample_width'])
        wav.setframerate(base['framerate'])
        for item in items:
            info = item['wav_info']
            segment = item['segment']
            wav.writeframes(_silence(info, int(segment.get('pause_before_ms') or 0)))
            frames = _apply_gain(info['frame_bytes'], info['sample_width'], float(segment.get('volume_db') or 0))
            wav.writeframes(frames)
            wav.writeframes(_silence(info, int(segment.get('pause_after_ms') or 0)))
    return output.getvalue()


def build_emotional_subtitle_timeline(segments: list[dict], durations: list[float]) -> list[dict]:
    timeline = []
    current_time = 0.0
    for index, (segment, duration) in enumerate(zip(segments, durations), 1):
        current_time += int(segment.get('pause_before_ms') or 0) / 1000
        start = current_time
        end = start + duration
        timeline.append({
            'index': index,
            'segment_id': segment.get('id'),
            'text': segment.get('text', ''),
            'start': round(start, 3),
            'end': round(end, 3),
        })
        current_time = end + int(segment.get('pause_after_ms') or 0) / 1000
    return timeline
```

- [ ] **Step 5: Extend TTSProvider signature**

Modify `server/services/tts_provider.py` so `synthesize()` accepts:

```python
emotion_options: dict | None = None,
```

Do not send `emotion_options` to MiMo yet. Keep the payload shape unchanged.

- [ ] **Step 6: Implement emotional TTS**

Create `server/services/emotional_tts.py`:

```python
import base64

from server.services.audio_package import read_wav_info
from server.services.emotion_planner import build_segment_delivery_instruction
from server.services.tts_provider import TTSProvider
from server.services.voice_prompt import build_voice_prompt
from server.services.voice_workflow_service import build_audio_fingerprint


def synthesize_emotion_segment(
    api_key: str,
    segment: dict,
    *,
    voice_profile: dict | None = None,
    fallback_voice_description: str = '',
    style_tags: str | None = None,
    model: str = 'mimo-v2.5-tts-voicedesign',
    voice: str | None = None,
) -> dict:
    base_prompt = build_voice_prompt(voice_profile, fallback_description=fallback_voice_description)
    instruction = build_segment_delivery_instruction(segment)
    voice_description = '\n'.join([base_prompt, '本段表演：', instruction]).strip()
    provider = TTSProvider(api_key)
    audio_b64 = provider.synthesize(
        voice_description=voice_description,
        text=segment['text'],
        style_tags=style_tags,
        model=model,
        voice=voice,
        optimize_text_preview=False,
        emotion_options=segment,
    )
    audio_bytes = base64.b64decode(audio_b64)
    info = read_wav_info(audio_bytes)
    duration = info['frames'] / info['framerate']
    fingerprint = build_audio_fingerprint({**segment, 'model': model})
    return {
        'audio_base64': audio_b64,
        'audio_bytes': audio_bytes,
        'wav_info': info,
        'duration': duration,
        'fingerprint': fingerprint,
    }
```

- [ ] **Step 7: Add audition and export routes**

Modify `server/routes/voice_workflows.py`:

```python
import io
from urllib.parse import quote

from flask import send_file
from server.services import voice_profile_repository as repo
from server.services.audio_package import build_srt, build_zip_package
from server.services.audio_postprocess import concat_emotional_wavs, build_emotional_subtitle_timeline
from server.services.emotional_tts import synthesize_emotion_segment
from server.services.voice_workflow_service import build_workflow_manifest, ordered_segments
```

Add helper:

```python
def _profile_audio_voice(profile):
    if not profile:
        return None
    if profile.get('source_type') == 'voice_clone':
        return profile.get('voice_sample_data_uri')
    return profile.get('builtin_voice')
```

Add routes:

```python
@voice_workflows_bp.route('/api/voice-workflows/<int:workflow_id>/segments/<int:segment_id>/audition', methods=['POST'])
def audition_voice_workflow_segment(workflow_id, segment_id):
    workflow = VoiceWorkflow.query.get_or_404(workflow_id)
    segment = VoiceWorkflowSegment.query.filter_by(id=segment_id, workflow_id=workflow.id).first_or_404()
    data = request.get_json() or {}
    api_key = data.get('api_key')
    if not api_key:
        return jsonify({'error': '请填写 API Key'}), 400
    profile_id = segment.voice_profile_id or workflow.default_voice_profile_id
    profile = repo.get_profile_by_id(int(profile_id)) if profile_id else None
    model = (profile or {}).get('model') or 'mimo-v2.5-tts-voicedesign'
    result = synthesize_emotion_segment(
        api_key,
        segment.to_dict(),
        voice_profile=profile,
        fallback_voice_description=data.get('voice_description', ''),
        style_tags=(profile or {}).get('style_tags'),
        model=model,
        voice=_profile_audio_voice(profile),
    )
    return jsonify({
        'audio_base64': result['audio_base64'],
        'duration': round(result['duration'], 3),
        'fingerprint': result['fingerprint'],
    })


@voice_workflows_bp.route('/api/voice-workflows/<int:workflow_id>/export', methods=['POST'])
def export_voice_workflow(workflow_id):
    workflow = VoiceWorkflow.query.get_or_404(workflow_id)
    data = request.get_json() or {}
    api_key = data.get('api_key')
    if not api_key:
        return jsonify({'error': '请填写 API Key'}), 400

    chunk_files = []
    audio_items = []
    manifest_segments = []
    durations = []

    for index, segment in enumerate(ordered_segments(workflow), 1):
        profile_id = segment.voice_profile_id or workflow.default_voice_profile_id
        profile = repo.get_profile_by_id(int(profile_id)) if profile_id else None
        model = (profile or {}).get('model') or 'mimo-v2.5-tts-voicedesign'
        result = synthesize_emotion_segment(
            api_key,
            segment.to_dict(),
            voice_profile=profile,
            fallback_voice_description=data.get('voice_description', ''),
            style_tags=(profile or {}).get('style_tags'),
            model=model,
            voice=_profile_audio_voice(profile),
        )
        filename = f'segments/{index:03d}.wav'
        chunk_files.append((filename, result['audio_bytes']))
        audio_items.append({'wav_info': result['wav_info'], 'segment': segment.to_dict()})
        durations.append(result['duration'])
        manifest_segments.append({**segment.to_dict(), 'filename': filename, 'duration': round(result['duration'], 3)})

    full_audio = concat_emotional_wavs(audio_items)
    timeline = build_emotional_subtitle_timeline([segment.to_dict() for segment in ordered_segments(workflow)], durations)
    srt_content = build_srt(timeline)
    manifest = build_workflow_manifest(workflow, manifest_segments, timeline)
    zip_bytes = build_zip_package(workflow.title, full_audio, srt_content, manifest, chunk_files)
    download_name = f'{workflow.title}_配音工作流.zip'
    response = send_file(
        io.BytesIO(zip_bytes),
        mimetype='application/zip',
        as_attachment=True,
        download_name=download_name,
    )
    response.headers['Content-Disposition'] = f"attachment; filename*=UTF-8''{quote(download_name)}"
    return response
```

- [ ] **Step 8: Run backend tests**

Run:

```bash
uv run pytest server/tests/test_audio_postprocess.py server/tests/test_voice_workflows_routes.py server/tests/test_tts_provider.py -v
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add server/services/audio_postprocess.py server/services/emotional_tts.py server/services/tts_provider.py server/routes/voice_workflows.py server/tests/test_audio_postprocess.py server/tests/test_voice_workflows_routes.py
git commit -m "feat: add voice workflow audition and export"
```

---

### Task 5: Frontend API, Store, Routes, And Navigation

**Files:**

- Modify: `web/package.json`
- Modify: `web/pnpm-lock.yaml`
- Modify: `web/src/api/index.js`
- Create: `web/src/stores/voiceWorkflows.js`
- Create: `web/src/views/VoiceWorkflowList.vue`
- Create: `web/src/views/VoiceWorkflowView.vue`
- Modify: `web/src/router/index.js`
- Modify: `web/src/App.vue`

- [ ] **Step 1: Add Vue Flow dependency**

Run:

```bash
cd web && pnpm add @vue-flow/core @vue-flow/background @vue-flow/controls
```

Expected: `web/package.json` and `web/pnpm-lock.yaml` change.

- [ ] **Step 2: Add API client**

Modify `web/src/api/index.js`:

```js
export const voiceWorkflowsApi = {
  list: () => api.get('/voice-workflows'),
  create: (data) => api.post('/voice-workflows', data),
  get: (id) => api.get(`/voice-workflows/${id}`),
  update: (id, data) => api.put(`/voice-workflows/${id}`, data),
  delete: (id) => api.delete(`/voice-workflows/${id}`),
  planSegments: (id, data) => api.post(`/voice-workflows/${id}/segments/plan`, data),
  auditionSegment: (id, segmentId, data) => api.post(`/voice-workflows/${id}/segments/${segmentId}/audition`, data),
  exportPackage: (id, data) => api.post(`/voice-workflows/${id}/export`, data, { responseType: 'blob' }),
}
```

- [ ] **Step 3: Create Pinia store**

Create `web/src/stores/voiceWorkflows.js`:

```js
import { defineStore } from 'pinia'
import { voiceWorkflowsApi } from '../api'

const defaultWorkflow = () => ({
  id: null,
  title: '未命名配音工程',
  source_text_id: null,
  source_content: '',
  default_voice_profile_id: null,
  settings: { subtitle_max_chars: 20, segment_max_chars: 80 },
})

export const useVoiceWorkflowsStore = defineStore('voiceWorkflows', {
  state: () => ({
    workflows: [],
    workflow: defaultWorkflow(),
    segments: [],
    edges: [],
    selectedSegmentId: null,
    loading: false,
    saving: false,
    exporting: false,
  }),
  getters: {
    selectedSegment(state) {
      return state.segments.find(segment => segment.id === state.selectedSegmentId) || null
    },
    orderedSegments(state) {
      return Array.from(state.segments).sort((a, b) => a.order_index - b.order_index)
    },
  },
  actions: {
    applySnapshot(data) {
      this.workflow = {
        id: data.id,
        title: data.title,
        source_text_id: data.source_text_id,
        source_content: data.source_content || '',
        default_voice_profile_id: data.default_voice_profile_id,
        settings: data.settings || { subtitle_max_chars: 20, segment_max_chars: 80 },
      }
      this.segments = data.segments || []
      this.edges = data.edges || []
      this.selectedSegmentId = this.segments[0]?.id || null
    },
    async fetchList() {
      const { data } = await voiceWorkflowsApi.list()
      this.workflows = data
      return data
    },
    async create(payload) {
      const { data } = await voiceWorkflowsApi.create(payload)
      this.applySnapshot(data)
      return data
    },
    async fetch(id) {
      this.loading = true
      try {
        const { data } = await voiceWorkflowsApi.get(id)
        this.applySnapshot(data)
        return data
      } finally {
        this.loading = false
      }
    },
    async save() {
      this.saving = true
      try {
        const { data } = await voiceWorkflowsApi.update(this.workflow.id, {
          workflow: this.workflow,
          segments: this.segments,
          edges: this.edges,
        })
        this.applySnapshot(data)
        return data
      } finally {
        this.saving = false
      }
    },
    updateSegment(id, patch) {
      const index = this.segments.findIndex(segment => segment.id === id)
      if (index !== -1) {
        this.segments[index] = Object.assign({}, this.segments[index], patch, {
          audio_status: patch.audio_status || 'missing',
        })
      }
    },
    selectSegment(id) {
      this.selectedSegmentId = id
    },
  },
})
```

- [ ] **Step 4: Add minimal list and workbench views**

Create `web/src/views/VoiceWorkflowList.vue`:

```vue
<template>
  <div class="voice-workflow-list">
    <div class="page-header">
      <h1 class="page-title">配音工作台</h1>
      <a-button type="primary" @click="$router.push('/voice-workflows/new')">新建配音工程</a-button>
    </div>
    <div class="workflow-grid">
      <button
        v-for="workflow in store.workflows"
        :key="workflow.id"
        class="workflow-item"
        @click="$router.push(`/voice-workflows/${workflow.id}`)"
      >
        <strong>{{ workflow.title }}</strong>
        <span>{{ workflow.updated_at }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useVoiceWorkflowsStore } from '../stores/voiceWorkflows'

const store = useVoiceWorkflowsStore()
onMounted(() => store.fetchList())
</script>

<style scoped>
.voice-workflow-list { max-width: 1180px; margin: 0 auto; padding: var(--space-xl); }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-lg); }
.page-title { margin: 0; font-size: 28px; font-weight: 650; }
.workflow-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: var(--space-md); }
.workflow-item { text-align: left; border: 1px solid var(--surface-border); background: var(--surface); border-radius: var(--radius-md); padding: var(--space-md); cursor: pointer; }
.workflow-item span { display: block; margin-top: 8px; color: var(--text-muted); font-size: 12px; }
</style>
```

Create initial `web/src/views/VoiceWorkflowView.vue`:

```vue
<template>
  <div class="voice-workflow-view">
    <div class="workflow-loading" v-if="store.loading">加载中</div>
    <div v-else class="workflow-shell">
      <div class="workflow-top">配音工作台</div>
      <div class="workflow-left">素材区</div>
      <div class="workflow-canvas">画布区</div>
      <div class="workflow-right">参数区</div>
      <div class="workflow-bottom">时间线</div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useVoiceWorkflowsStore } from '../stores/voiceWorkflows'

const route = useRoute()
const router = useRouter()
const store = useVoiceWorkflowsStore()

onMounted(async () => {
  if (route.params.id && route.params.id !== 'new') {
    await store.fetch(route.params.id)
    return
  }
  const data = await store.create({ title: '未命名配音工程', source_content: '' })
  router.replace(`/voice-workflows/${data.id}`)
})
</script>

<style scoped>
.voice-workflow-view { height: calc(100vh - 64px); padding: var(--space-md); }
.workflow-shell { display: grid; grid-template-columns: 260px 1fr 340px; grid-template-rows: 56px 1fr 126px; gap: 12px; height: 100%; }
.workflow-top, .workflow-left, .workflow-canvas, .workflow-right, .workflow-bottom { border: 1px solid var(--surface-border); border-radius: var(--radius-md); background: var(--surface); padding: var(--space-md); }
.workflow-top, .workflow-bottom { grid-column: 1 / 4; }
.workflow-loading { padding: var(--space-xl); }
</style>
```

- [ ] **Step 5: Add routes and navigation**

Modify `web/src/router/index.js` imports:

```js
import VoiceWorkflowList from '../views/VoiceWorkflowList.vue'
import VoiceWorkflowView from '../views/VoiceWorkflowView.vue'
```

Add routes:

```js
{ path: '/voice-workflows', component: VoiceWorkflowList },
{ path: '/voice-workflows/new', component: VoiceWorkflowView },
{ path: '/voice-workflows/:id', component: VoiceWorkflowView },
```

Modify `web/src/App.vue` to add a menu item:

```vue
<a-menu-item key="/voice-workflows">
  <template #icon>
    <SoundOutlined />
  </template>
  <span>配音工作台</span>
</a-menu-item>
```

Add import in `App.vue`:

```js
import { SoundOutlined } from '@ant-design/icons-vue'
```

Update selected keys:

```js
if (route.path.startsWith('/voice-workflows')) return ['/voice-workflows']
```

- [ ] **Step 6: Build frontend**

Run:

```bash
cd web && pnpm run build
```

Expected: build succeeds and writes `server/static/`.

- [ ] **Step 7: Commit**

```bash
git add web/package.json web/pnpm-lock.yaml web/src/api/index.js web/src/stores/voiceWorkflows.js web/src/views/VoiceWorkflowList.vue web/src/views/VoiceWorkflowView.vue web/src/router/index.js web/src/App.vue server/static
git commit -m "feat: add voice workflow frontend shell"
```

---

### Task 6: Workbench Components And Canvas

**Files:**

- Create: `web/src/components/voice-workflow/WorkflowToolbar.vue`
- Create: `web/src/components/voice-workflow/SourcePanel.vue`
- Create: `web/src/components/voice-workflow/VoiceFlowCanvas.vue`
- Create: `web/src/components/voice-workflow/VoiceSegmentNode.vue`
- Create: `web/src/components/voice-workflow/SegmentInspector.vue`
- Create: `web/src/components/voice-workflow/TimelineAuditionBar.vue`
- Modify: `web/src/views/VoiceWorkflowView.vue`

- [ ] **Step 1: Create toolbar component**

Create `web/src/components/voice-workflow/WorkflowToolbar.vue`:

```vue
<template>
  <div class="workflow-toolbar">
    <div class="title-block">
      <a-input v-model:value="localTitle" class="title-input" @blur="emitTitle" />
      <span class="save-state">{{ saving ? '保存中' : '已保存' }}</span>
    </div>
    <a-space>
      <a-button @click="$emit('import-text')">导入文本</a-button>
      <a-button @click="$emit('auto-layout')">自动重排</a-button>
      <a-button :loading="saving" @click="$emit('save')">保存</a-button>
      <a-button type="primary" :loading="exporting" @click="$emit('export')">导出</a-button>
    </a-space>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  title: { type: String, required: true },
  saving: Boolean,
  exporting: Boolean,
})
const emit = defineEmits(['update:title', 'save', 'export', 'import-text', 'auto-layout'])
const localTitle = ref(props.title)

watch(() => props.title, value => {
  localTitle.value = value
})

const emitTitle = () => emit('update:title', localTitle.value || '未命名配音工程')
</script>

<style scoped>
.workflow-toolbar { display: flex; align-items: center; justify-content: space-between; height: 100%; }
.title-block { display: flex; align-items: center; gap: 10px; }
.title-input { width: 260px; font-weight: 650; }
.save-state { color: var(--text-muted); font-size: 12px; }
</style>
```

- [ ] **Step 2: Create source panel component**

Create `web/src/components/voice-workflow/SourcePanel.vue` with a textarea bound to source content and a button that emits `plan`:

```vue
<template>
  <div class="source-panel">
    <div class="panel-title">素材与节点</div>
    <a-tabs v-model:activeKey="activeTab" size="small">
      <a-tab-pane key="text" tab="文本">
        <a-textarea
          :value="sourceContent"
          @update:value="$emit('update:sourceContent', $event)"
          :autoSize="{ minRows: 8, maxRows: 14 }"
          placeholder="粘贴旁白文本"
        />
        <a-button block type="primary" class="plan-btn" @click="$emit('plan')">自动切句</a-button>
      </a-tab-pane>
      <a-tab-pane key="nodes" tab="节点">
        <button class="node-preset" @click="$emit('add-segment')">+ 语句节点</button>
        <button class="node-preset" @click="$emit('add-pause')">+ 停顿节点</button>
      </a-tab-pane>
      <a-tab-pane key="presets" tab="预设">
        <button v-for="preset in presets" :key="preset.value" class="node-preset" @click="$emit('apply-emotion', preset.value)">
          {{ preset.label }}
        </button>
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'

defineProps({ sourceContent: { type: String, default: '' } })
defineEmits(['update:sourceContent', 'plan', 'add-segment', 'add-pause', 'apply-emotion'])

const activeTab = ref('text')
const presets = [
  { label: '平静', value: 'calm' },
  { label: '压抑', value: 'suppressed' },
  { label: '爆发愤怒', value: 'angry_burst' },
  { label: '冷漠', value: 'cold' },
]
</script>

<style scoped>
.source-panel { height: 100%; display: flex; flex-direction: column; }
.panel-title { font-weight: 650; margin-bottom: var(--space-sm); }
.plan-btn { margin-top: var(--space-sm); }
.node-preset { width: 100%; text-align: left; padding: 9px; border: 1px solid var(--surface-border); background: var(--surface-muted); border-radius: var(--radius-sm); margin-bottom: 8px; cursor: pointer; }
</style>
```

- [ ] **Step 3: Create Vue Flow canvas and node**

Create `web/src/components/voice-workflow/VoiceSegmentNode.vue`:

```vue
<template>
  <div class="voice-node" :class="`emotion-${data.emotion || 'neutral'}`">
    <div class="node-header">
      <strong>{{ data.order_index }}</strong>
      <span>{{ data.audio_status === 'ready' ? '已生成' : '需生成' }}</span>
    </div>
    <p>{{ data.text }}</p>
    <div class="node-meta">{{ emotionLabel }} · {{ data.voice_profile_id ? `音色 ${data.voice_profile_id}` : '默认音色' }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ data: { type: Object, required: true } })
const emotionLabel = computed(() => ({
  calm: '平静',
  suppressed: '压抑',
  angry_burst: '爆发',
  cold: '冷漠',
  neutral: '中性',
}[props.data.emotion] || '中性')
</script>

<style scoped>
.voice-node { width: 190px; border: 2px solid var(--surface-border-strong); border-radius: var(--radius-md); background: var(--surface); padding: 10px; box-shadow: var(--shadow-sm); }
.node-header { display: flex; justify-content: space-between; font-size: 12px; }
.voice-node p { margin: 8px 0; font-size: 13px; line-height: 1.5; }
.node-meta { font-size: 11px; color: var(--text-muted); }
.emotion-angry_burst { border-color: #a6533f; }
.emotion-cold { border-color: #5d6875; }
.emotion-calm { border-color: #8e7f67; }
.emotion-suppressed { border-color: #6f665c; }
</style>
```

Create `web/src/components/voice-workflow/VoiceFlowCanvas.vue`:

```vue
<template>
  <div class="voice-flow-canvas">
    <VueFlow
      :nodes="flowNodes"
      :edges="flowEdges"
      fit-view-on-init
      @node-click="handleNodeClick"
      @nodes-change="handleNodesChange"
    >
      <template #node-segment="nodeProps">
        <VoiceSegmentNode v-bind="nodeProps" />
      </template>
      <Background />
      <Controls />
    </VueFlow>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import VoiceSegmentNode from './VoiceSegmentNode.vue'

const props = defineProps({
  segments: { type: Array, default: () => [] },
  edges: { type: Array, default: () => [] },
})
const emit = defineEmits(['select', 'move'])
const { onNodesChange } = useVueFlow()

const flowNodes = computed(() => props.segments.map(segment => ({
  id: String(segment.id),
  type: 'segment',
  position: { x: segment.node_x || 0, y: segment.node_y || 0 },
  data: segment,
})))

const flowEdges = computed(() => props.edges.map(edge => ({
  id: String(edge.id || `${edge.source_segment_id}-${edge.target_segment_id}`),
  source: String(edge.source_segment_id),
  target: String(edge.target_segment_id),
  animated: false,
})))

const handleNodeClick = ({ node }) => emit('select', Number(node.id))

const handleNodesChange = changes => {
  changes.forEach(change => {
    if (change.type === 'position' && change.position) {
      emit('move', Number(change.id), { node_x: change.position.x, node_y: change.position.y })
    }
  })
}

onNodesChange(handleNodesChange)
</script>

<style scoped>
.voice-flow-canvas { height: 100%; background: var(--paper-soft); border-radius: var(--radius-md); overflow: hidden; }
</style>
```

- [ ] **Step 4: Create inspector and timeline components**

Create `web/src/components/voice-workflow/SegmentInspector.vue`:

```vue
<template>
  <div class="segment-inspector" v-if="segment">
    <div class="panel-title">语句参数</div>
    <a-form layout="vertical">
      <a-form-item label="文本">
        <a-textarea :value="segment.text" @update:value="patch({ text: $event })" :autoSize="{ minRows: 3, maxRows: 6 }" />
      </a-form-item>
      <a-form-item label="情绪">
        <a-select :value="segment.emotion" @change="value => patch({ emotion: value })">
          <a-select-option value="calm">平静</a-select-option>
          <a-select-option value="suppressed">压抑</a-select-option>
          <a-select-option value="angry_burst">爆发愤怒</a-select-option>
          <a-select-option value="cold">冷漠</a-select-option>
        </a-select>
      </a-form-item>
      <a-form-item label="强度">
        <a-slider :value="segment.intensity" :min="0" :max="2" :step="0.05" @change="value => patch({ intensity: value })" />
      </a-form-item>
      <a-form-item label="语速">
        <a-slider :value="segment.rate" :min="0.5" :max="2" :step="0.05" @change="value => patch({ rate: value })" />
      </a-form-item>
      <a-form-item label="音量 dB">
        <a-slider :value="segment.volume_db" :min="-12" :max="12" :step="1" @change="value => patch({ volume_db: value })" />
      </a-form-item>
      <div class="pause-grid">
        <a-form-item label="段前 ms">
          <a-input-number :value="segment.pause_before_ms" :min="0" :max="10000" @change="value => patch({ pause_before_ms: value })" />
        </a-form-item>
        <a-form-item label="段后 ms">
          <a-input-number :value="segment.pause_after_ms" :min="0" :max="10000" @change="value => patch({ pause_after_ms: value })" />
        </a-form-item>
      </div>
      <a-button block @click="$emit('audition', segment)">试听这一句</a-button>
    </a-form>
  </div>
  <div v-else class="empty-inspector">选择一个语句节点</div>
</template>

<script setup>
const props = defineProps({ segment: { type: Object, default: null } })
const emit = defineEmits(['update', 'audition'])
const patch = patch => emit('update', props.segment.id, patch)
</script>

<style scoped>
.panel-title { font-weight: 650; margin-bottom: var(--space-sm); }
.pause-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--space-sm); }
.empty-inspector { color: var(--text-muted); }
</style>
```

Create `web/src/components/voice-workflow/TimelineAuditionBar.vue`:

```vue
<template>
  <div class="timeline-bar">
    <div class="timeline-actions">
      <span>{{ segments.length }} 句旁白</span>
      <a-space>
        <a-button @click="$emit('audition-selected')">试听选中</a-button>
        <a-button @click="$emit('export')">导出同步包</a-button>
      </a-space>
    </div>
    <div class="timeline-track">
      <button
        v-for="segment in segments"
        :key="segment.id"
        class="timeline-segment"
        :class="{ active: segment.id === selectedSegmentId }"
        @click="$emit('select', segment.id)"
      >
        {{ segment.order_index }} · {{ segment.emotion }}
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  segments: { type: Array, default: () => [] },
  selectedSegmentId: { type: Number, default: null },
})
defineEmits(['select', 'audition-selected', 'export'])
</script>

<style scoped>
.timeline-bar { height: 100%; display: flex; flex-direction: column; gap: var(--space-sm); }
.timeline-actions { display: flex; align-items: center; justify-content: space-between; }
.timeline-track { display: grid; grid-auto-flow: column; grid-auto-columns: minmax(140px, 1fr); gap: 6px; overflow-x: auto; }
.timeline-segment { border: 1px solid var(--surface-border); background: var(--surface-muted); border-radius: var(--radius-sm); padding: 9px; cursor: pointer; }
.timeline-segment.active { border-color: var(--text-primary); background: var(--surface-active); }
</style>
```

- [ ] **Step 5: Compose the workbench view**

Modify `web/src/views/VoiceWorkflowView.vue` to use the components. Keep the grid from Task 5 and replace placeholder divs with:

```vue
<WorkflowToolbar
  v-model:title="store.workflow.title"
  :saving="store.saving"
  :exporting="store.exporting"
  @save="store.save"
  @export="handleExport"
  @auto-layout="handleAutoLayout"
/>
<SourcePanel
  v-model:sourceContent="store.workflow.source_content"
  @plan="handlePlanSegments"
/>
<VoiceFlowCanvas
  :segments="store.segments"
  :edges="store.edges"
  @select="store.selectSegment"
  @move="store.updateSegment"
/>
<SegmentInspector
  :segment="store.selectedSegment"
  @update="store.updateSegment"
  @audition="handleAudition"
/>
<TimelineAuditionBar
  :segments="store.orderedSegments"
  :selectedSegmentId="store.selectedSegmentId"
  @select="store.selectSegment"
  @audition-selected="handleAuditionSelected"
  @export="handleExport"
/>
```

Add handlers:

```js
const handleAutoLayout = () => {
  store.segments.forEach((segment, index) => {
    store.updateSegment(segment.id, {
      node_x: 80 + index * 240,
      node_y: 120 + (index % 2) * 80,
      audio_status: segment.audio_status,
    })
  })
}
```

Leave `handlePlanSegments`, `handleAudition`, and `handleExport` wired in Task 7.

- [ ] **Step 6: Build frontend**

Run:

```bash
cd web && pnpm run build
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add web/src/components/voice-workflow web/src/views/VoiceWorkflowView.vue server/static
git commit -m "feat: build voice workflow workbench UI"
```

---

### Task 7: Frontend Planning, Audition, Save, And Export Integration

**Files:**

- Modify: `web/src/stores/voiceWorkflows.js`
- Modify: `web/src/views/VoiceWorkflowView.vue`

- [ ] **Step 1: Add store actions for planning, audition, and export**

Modify `web/src/stores/voiceWorkflows.js`:

```js
async planSegments() {
  const { data } = await voiceWorkflowsApi.planSegments(this.workflow.id, {
    content: this.workflow.source_content,
    max_chars: this.workflow.settings.segment_max_chars || 80,
  })
  this.segments = data.segments.map((segment, index) => Object.assign({}, segment, {
    id: `tmp-${Date.now()}-${index}`,
  }))
  this.edges = this.segments.slice(0, -1).map((segment, index) => ({
    id: `tmp-edge-${index}`,
    source_client_id: index,
    target_client_id: index + 1,
    source_segment_id: segment.id,
    target_segment_id: this.segments[index + 1].id,
    order_index: index + 1,
  }))
  this.selectedSegmentId = this.segments[0]?.id || null
},
async auditionSegment(segment, apiKey, voiceDescription) {
  if (typeof segment.id === 'string') {
    await this.save()
    segment = this.selectedSegment
  }
  const { data } = await voiceWorkflowsApi.auditionSegment(this.workflow.id, segment.id, {
    api_key: apiKey,
    voice_description: voiceDescription,
  })
  this.updateSegment(segment.id, {
    audio_status: 'ready',
    audio_fingerprint: data.fingerprint,
  })
  return data
},
async exportPackage(apiKey, voiceDescription) {
  this.exporting = true
  try {
    await this.save()
    return await voiceWorkflowsApi.exportPackage(this.workflow.id, {
      api_key: apiKey,
      voice_description: voiceDescription,
      export_options: { include_segment_wavs: true, reuse_cache: true },
    })
  } finally {
    this.exporting = false
  }
}
```

Update `save()` so edges sent to the backend use client indices when IDs are temporary:

```js
const segmentIndexById = new Map(this.segments.map((segment, index) => [segment.id, index]))
const payloadEdges = this.edges.map(edge => Object.assign({}, edge, {
  source_client_id: segmentIndexById.get(edge.source_segment_id),
  target_client_id: segmentIndexById.get(edge.target_segment_id),
}))
const { data } = await voiceWorkflowsApi.update(this.workflow.id, {
  workflow: this.workflow,
  segments: this.segments,
  edges: payloadEdges,
})
```

- [ ] **Step 2: Wire view handlers**

Modify `web/src/views/VoiceWorkflowView.vue` imports:

```js
import { message } from 'ant-design-vue'
import { useSettings } from '../stores/settings'
```

Add:

```js
const { ttsKey } = useSettings()
const fallbackVoiceDescription = '稳定自然的中文旁白声线，吐字清晰，情绪服从每句设置。'

const handlePlanSegments = async () => {
  if (!store.workflow.source_content.trim()) {
    message.warning('请先输入源文本')
    return
  }
  await store.planSegments()
  message.success('已生成语句节点')
}

const playBase64Audio = audioBase64 => {
  const binary = atob(audioBase64)
  const bytes = new Uint8Array(binary.length)
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index)
  const url = URL.createObjectURL(new Blob([bytes], { type: 'audio/wav' }))
  const audio = new Audio(url)
  audio.onended = () => URL.revokeObjectURL(url)
  audio.play()
}

const handleAudition = async segment => {
  if (!ttsKey.value) {
    message.warning('请先配置 TTS API Key')
    return
  }
  const data = await store.auditionSegment(segment, ttsKey.value, fallbackVoiceDescription)
  playBase64Audio(data.audio_base64)
}

const handleAuditionSelected = async () => {
  if (store.selectedSegment) await handleAudition(store.selectedSegment)
}

const handleExport = async () => {
  if (!ttsKey.value) {
    message.warning('请先配置 TTS API Key')
    return
  }
  const response = await store.exportPackage(ttsKey.value, fallbackVoiceDescription)
  const url = URL.createObjectURL(new Blob([response.data], { type: 'application/zip' }))
  const link = document.createElement('a')
  link.href = url
  link.download = `${store.workflow.title || '配音工作流'}_配音工作流.zip`
  link.click()
  URL.revokeObjectURL(url)
  message.success('导出完成')
}
```

- [ ] **Step 3: Build frontend**

Run:

```bash
cd web && pnpm run build
```

Expected: PASS.

- [ ] **Step 4: Run focused backend tests**

Run:

```bash
uv run pytest server/tests/test_voice_workflows_routes.py server/tests/test_voice_workflow_service.py server/tests/test_audio_postprocess.py server/tests/test_emotion_planner.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/src/stores/voiceWorkflows.js web/src/views/VoiceWorkflowView.vue server/static
git commit -m "feat: wire voice workflow generation actions"
```

---

### Task 8: Full Verification And Polish

**Files:**

- Modify only files needed to fix verification failures.

- [ ] **Step 1: Run all Python tests**

Run:

```bash
uv run pytest
```

Expected: PASS.

- [ ] **Step 2: Build frontend**

Run:

```bash
cd web && pnpm run build
```

Expected: PASS.

- [ ] **Step 3: Start the app**

Run:

```bash
./start.sh restart
./start.sh status
```

Expected: Flask is on `:5002` and Vue dev server is on `:3000`.

- [ ] **Step 4: Manual browser verification**

Open `http://localhost:3000/voice-workflows/new`.

Verify:

- Navigation contains `配音工作台`.
- New workflow auto-creates and redirects to `/voice-workflows/<id>`.
- Source panel accepts text.
- Auto cut creates nodes.
- Selecting a node updates the inspector.
- Editing emotion updates the node label and marks audio as missing.
- Save persists data after refresh.
- Export button shows missing API key warning if no key exists.

- [ ] **Step 5: Stop dev servers if they were not already running before the task**

Run:

```bash
./start.sh stop
```

Expected: local dev servers stop.

- [ ] **Step 6: Commit verification fixes**

If any fixes were needed:

```bash
git add server web/src server/static
git commit -m "fix: polish voice workflow studio"
```

If no fixes were needed, do not create an empty commit.

---

## Self-Review Checklist

- Spec coverage: Tasks 1-4 cover backend models, services, audition, export, and manifest. Tasks 5-7 cover routes, store, workbench UI, inspector, canvas, timeline, save, audition, and export. Task 8 covers full verification.
- Placeholder scan: This plan uses concrete file paths, commands, expected results, and code snippets for each implementation step.
- Type consistency: Segment fields match the spec and model names: `order_index`, `node_x`, `node_y`, `emotion`, `intensity`, `rate`, `pitch`, `volume_db`, `pause_before_ms`, `pause_after_ms`, `transition`, `delivery_instruction`, `voice_profile_id`, `audio_status`, `audio_fingerprint`.
- Scope check: The plan keeps workflows linear and does not implement branching, async jobs, video integration, waveform editing, or multi-track editing.

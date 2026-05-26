# Video Generation Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the video generation module from static-image合成 to a full xianxia short video production pipeline with templates, BGM mixing, motion effects, multi-scene support, and CapCut-friendly export.

**Architecture:** New service layer in `server/services/` handles templates, scene planning, audio mixing, video rendering, and packaging. Routes in `server/routes/video.py` expose new APIs while preserving backward compatibility with `/api/video/generate`.

**Tech Stack:** Python 3.13, Flask, moviepy (video rendering), wave (audio), zipfile (packaging), SQLAlchemy (templates/jobs), threading (async jobs)

---

## File Structure

| File | Responsibility |
|------|----------------|
| `server/services/video_template.py` | Template CRUD, built-in templates, default config |
| `server/services/video_scene_planner.py` | Text → scene mapping, multi-scene planning |
| `server/services/audio_mixer.py` | Voice + BGM + ambient mixing with fade/loop |
| `server/services/video_renderer.py` | Motion effects (zoom, pan, shake), scene rendering |
| `server/services/video_job.py` | Async job queue, progress tracking, status management |
| `server/services/capcut_package.py` | ZIP export with MP4, audio, SRT, manifest, scenes |
| `server/models.py` | Add VideoTemplate, VideoJob, VideoAsset models |
| `server/routes/video.py` | New endpoints: templates, preview, jobs, download |
| `server/tests/test_video_template.py` | Template service tests |
| `server/tests/test_audio_mixer.py` | Audio mixing tests |
| `server/tests/test_video_renderer.py` | Motion effect tests |
| `server/tests/test_video_scene_planner.py` | Scene planning tests |
| `server/tests/test_video_job.py` | Job management tests |
| `server/tests/test_capcut_package.py` | Package export tests |

---

## Task 1: Database Models

**Files:**
- Modify: `server/models.py`
- Test: `server/tests/test_models.py`

- [ ] **Step 1: Write failing test for VideoTemplate model**

```python
# server/tests/test_models.py
def test_video_template_create(app, db):
    from server.models import VideoTemplate
    template = VideoTemplate(
        template_key='test_template',
        name='Test Template',
        config_json='{"fps": 24}',
        is_builtin=True,
    )
    db.session.add(template)
    db.session.commit()
    assert template.id is not None
    assert template.template_key == 'test_template'


def test_video_template_to_dict(app, db):
    from server.models import VideoTemplate
    template = VideoTemplate(
        template_key='test_template',
        name='Test Template',
        config_json='{"fps": 24}',
    )
    db.session.add(template)
    db.session.commit()
    d = template.to_dict()
    assert d['template_key'] == 'test_template'
    assert d['name'] == 'Test Template'
    assert d['config'] == {'fps': 24}


def test_video_job_create(app, db):
    from server.models import VideoJob
    job = VideoJob(
        job_id='test-job-uuid',
        title='Test Video',
        status='queued',
        request_json='{}',
    )
    db.session.add(job)
    db.session.commit()
    assert job.id is not None
    assert job.status == 'queued'


def test_video_job_to_dict(app, db):
    from server.models import VideoJob
    job = VideoJob(
        job_id='test-job-uuid',
        title='Test Video',
        status='rendering',
        progress=0.5,
        stage='mixing_audio',
        message='Mixing audio',
    )
    db.session.add(job)
    db.session.commit()
    d = job.to_dict()
    assert d['job_id'] == 'test-job-uuid'
    assert d['status'] == 'rendering'
    assert d['progress'] == 0.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest server/tests/test_models.py -v`
Expected: FAIL (VideoTemplate/VideoJob not defined)

- [ ] **Step 3: Add VideoTemplate model**

```python
# Add to server/models.py after Tag class

class VideoTemplate(db.Model):
    __tablename__ = 'video_templates'

    id = db.Column(db.Integer, primary_key=True)
    template_key = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    config_json = db.Column(db.Text, nullable=False, default='{}')
    is_builtin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        import json
        return {
            'id': self.id,
            'template_key': self.template_key,
            'name': self.name,
            'config': json.loads(self.config_json) if self.config_json else {},
            'is_builtin': self.is_builtin,
            'is_active': self.is_active,
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class VideoJob(db.Model):
    __tablename__ = 'video_jobs'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(36), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False, default='未命名')
    status = db.Column(db.String(20), nullable=False, default='queued')
    progress = db.Column(db.Float, default=0.0)
    stage = db.Column(db.String(50))
    message = db.Column(db.String(500))
    request_json = db.Column(db.Text, nullable=False, default='{}')
    manifest_json = db.Column(db.Text)
    output_path = db.Column(db.String(500))
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'job_id': self.job_id,
            'title': self.title,
            'status': self.status,
            'progress': self.progress,
            'stage': self.stage,
            'message': self.message,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class VideoAsset(db.Model):
    __tablename__ = 'video_assets'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.String(36), nullable=False)
    asset_type = db.Column(db.String(50), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    path = db.Column(db.String(500), nullable=False)
    metadata_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'job_id': self.job_id,
            'asset_type': self.asset_type,
            'filename': self.filename,
            'path': self.path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest server/tests/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server/models.py server/tests/test_models.py
git commit -m "feat: add VideoTemplate, VideoJob, VideoAsset models"
```

---

## Task 2: Video Template Service

**Files:**
- Create: `server/services/video_template.py`
- Test: `server/tests/test_video_template.py`

- [ ] **Step 1: Write failing test for template service**

```python
# server/tests/test_video_template.py
import json
import pytest


BUILTIN_TEMPLATES = [
    {
        'template_key': 'xianxia_narration',
        'name': '修仙旁白',
        'config': {
            'aspect_ratio': '9:16',
            'resolution': [1080, 1920],
            'fps': 24,
            'scene_duration_strategy': 'audio',
            'visual_effects': {
                'motion': 'slow_zoom_in',
                'overlay': 'mist',
                'transition': 'fade',
            },
            'audio': {
                'bgm_volume': 0.18,
                'voice_volume': 1.0,
                'ambient_volume': 0.12,
                'fade_in': 1.0,
                'fade_out': 1.5,
            },
            'export': {
                'include_source_package': True,
                'video_codec': 'libx264',
                'audio_codec': 'aac',
            },
        },
    },
]


def test_get_builtin_templates(app, db):
    from server.services.video_template import get_builtin_templates
    templates = get_builtin_templates()
    assert len(templates) == 5
    assert templates[0]['template_key'] == 'xianxia_narration'


def test_seed_templates(app, db):
    from server.services.video_template import seed_builtin_templates, get_all_templates
    seed_builtin_templates()
    templates = get_all_templates()
    assert len(templates) == 5
    assert templates[0].template_key == 'xianxia_narration'
    assert templates[0].is_builtin is True


def test_seed_templates_idempotent(app, db):
    from server.services.video_template import seed_builtin_templates, get_all_templates
    seed_builtin_templates()
    seed_builtin_templates()
    templates = get_all_templates()
    assert len(templates) == 5


def test_get_template_by_key(app, db):
    from server.services.video_template import seed_builtin_templates, get_template_by_key
    seed_builtin_templates()
    template = get_template_by_key('xianxia_narration')
    assert template is not None
    assert template.name == '修仙旁白'


def test_get_template_by_key_not_found(app, db):
    from server.services.video_template import get_template_by_key
    template = get_template_by_key('nonexistent')
    assert template is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest server/tests/test_video_template.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement video_template service**

```python
# server/services/video_template.py
import json
from server.models import db, VideoTemplate

BUILTIN_TEMPLATES = [
    {
        'template_key': 'xianxia_narration',
        'name': '修仙旁白',
        'sort_order': 1,
        'config': {
            'aspect_ratio': '9:16',
            'resolution': [1080, 1920],
            'fps': 24,
            'scene_duration_strategy': 'audio',
            'visual_effects': {
                'motion': 'slow_zoom_in',
                'overlay': 'mist',
                'transition': 'fade',
            },
            'audio': {
                'bgm_volume': 0.18,
                'voice_volume': 1.0,
                'ambient_volume': 0.12,
                'fade_in': 1.0,
                'fade_out': 1.5,
            },
            'export': {
                'include_source_package': True,
                'video_codec': 'libx264',
                'audio_codec': 'aac',
            },
        },
    },
    {
        'template_key': 'character_monologue',
        'name': '角色独白',
        'sort_order': 2,
        'config': {
            'aspect_ratio': '9:16',
            'resolution': [1080, 1920],
            'fps': 24,
            'scene_duration_strategy': 'audio',
            'visual_effects': {
                'motion': 'slow_zoom_in',
                'overlay': None,
                'transition': 'fade',
            },
            'audio': {
                'bgm_volume': 0.10,
                'voice_volume': 1.0,
                'ambient_volume': 0.08,
                'fade_in': 0.5,
                'fade_out': 1.0,
            },
            'export': {
                'include_source_package': True,
                'video_codec': 'libx264',
                'audio_codec': 'aac',
            },
        },
    },
    {
        'template_key': 'chapter_title',
        'name': '章节标题',
        'sort_order': 3,
        'config': {
            'aspect_ratio': '9:16',
            'resolution': [1080, 1920],
            'fps': 24,
            'scene_duration_strategy': 'fixed',
            'fixed_duration': 5.0,
            'visual_effects': {
                'motion': 'fade_in',
                'overlay': None,
                'transition': 'fade',
            },
            'audio': {
                'bgm_volume': 0.15,
                'voice_volume': 1.0,
                'ambient_volume': 0.0,
                'fade_in': 0.5,
                'fade_out': 1.0,
            },
            'export': {
                'include_source_package': True,
                'video_codec': 'libx264',
                'audio_codec': 'aac',
            },
        },
    },
    {
        'template_key': 'battle_transition',
        'name': '战斗转场',
        'sort_order': 4,
        'config': {
            'aspect_ratio': '9:16',
            'resolution': [1080, 1920],
            'fps': 30,
            'scene_duration_strategy': 'audio',
            'visual_effects': {
                'motion': 'shake',
                'overlay': 'flash',
                'transition': 'cut',
            },
            'audio': {
                'bgm_volume': 0.25,
                'voice_volume': 1.0,
                'ambient_volume': 0.20,
                'fade_in': 0.3,
                'fade_out': 0.5,
            },
            'export': {
                'include_source_package': True,
                'video_codec': 'libx264',
                'audio_codec': 'aac',
            },
        },
    },
    {
        'template_key': 'technique_explain',
        'name': '功法讲解',
        'sort_order': 5,
        'config': {
            'aspect_ratio': '9:16',
            'resolution': [1080, 1920],
            'fps': 24,
            'scene_duration_strategy': 'audio',
            'visual_effects': {
                'motion': 'slow_zoom_in',
                'overlay': None,
                'transition': 'fade',
            },
            'audio': {
                'bgm_volume': 0.12,
                'voice_volume': 1.0,
                'ambient_volume': 0.05,
                'fade_in': 1.0,
                'fade_out': 1.5,
            },
            'export': {
                'include_source_package': True,
                'video_codec': 'libx264',
                'audio_codec': 'aac',
            },
        },
    },
]


def get_builtin_templates() -> list[dict]:
    return BUILTIN_TEMPLATES


def seed_builtin_templates():
    for tmpl in BUILTIN_TEMPLATES:
        existing = VideoTemplate.query.filter_by(template_key=tmpl['template_key']).first()
        if not existing:
            db.session.add(VideoTemplate(
                template_key=tmpl['template_key'],
                name=tmpl['name'],
                config_json=json.dumps(tmpl['config'], ensure_ascii=False),
                is_builtin=True,
                sort_order=tmpl.get('sort_order', 0),
            ))
    db.session.commit()


def get_all_templates() -> list[VideoTemplate]:
    return VideoTemplate.query.filter_by(is_active=True).order_by(VideoTemplate.sort_order).all()


def get_template_by_key(key: str) -> VideoTemplate | None:
    return VideoTemplate.query.filter_by(template_key=key, is_active=True).first()


def get_template_config(key: str) -> dict | None:
    template = get_template_by_key(key)
    if not template:
        return None
    return json.loads(template.config_json)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest server/tests/test_video_template.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server/services/video_template.py server/tests/test_video_template.py
git commit -m "feat: add video template service with 5 builtin templates"
```

---

## Task 3: Audio Mixer Service

**Files:**
- Create: `server/services/audio_mixer.py`
- Test: `server/tests/test_audio_mixer.py`

- [ ] **Step 1: Write failing test for audio mixer**

```python
# server/tests/test_audio_mixer.py
import struct
import wave
import io
import pytest


def _make_wav_bytes(duration_sec=1.0, frequency=440, sample_rate=16000):
    """Create a simple sine wave WAV for testing."""
    import math
    num_samples = int(sample_rate * duration_sec)
    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        value = int(16000 * math.sin(2 * math.pi * frequency * t))
        samples.append(struct.pack('<h', value))
    
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b''.join(samples))
    return buf.getvalue()


def test_mix_audio_basic():
    from server.services.audio_mixer import mix_audio
    voice = _make_wav_bytes(2.0)
    result = mix_audio(voice_wav=voice)
    assert len(result) > 0
    with wave.open(io.BytesIO(result), 'rb') as wav:
        assert wav.getnchannels() == 1
        assert wav.getframerate() == 16000


def test_mix_audio_with_bgm():
    from server.services.audio_mixer import mix_audio
    voice = _make_wav_bytes(2.0)
    bgm = _make_wav_bytes(5.0, frequency=220)
    result = mix_audio(voice_wav=voice, bgm_wav=bgm, bgm_volume=0.2)
    assert len(result) > len(voice)


def test_mix_audio_bgm_loops_when_shorter():
    from server.services.audio_mixer import mix_audio
    voice = _make_wav_bytes(3.0)
    bgm = _make_wav_bytes(1.0, frequency=220)
    result = mix_audio(voice_wav=voice, bgm_wav=bgm, bgm_volume=0.2)
    with wave.open(io.BytesIO(result), 'rb') as wav:
        duration = wav.getnframes() / wav.getframerate()
        assert duration >= 2.9


def test_mix_audio_with_ambient():
    from server.services.audio_mixer import mix_audio
    voice = _make_wav_bytes(2.0)
    ambient = _make_wav_bytes(3.0, frequency=100)
    result = mix_audio(voice_wav=voice, ambient_wav=ambient, ambient_volume=0.1)
    assert len(result) > 0


def test_mix_audio_fade_in_out():
    from server.services.audio_mixer import mix_audio
    voice = _make_wav_bytes(3.0)
    bgm = _make_wav_bytes(5.0, frequency=220)
    result = mix_audio(voice_wav=voice, bgm_wav=bgm, bgm_volume=0.2, fade_in=0.5, fade_out=0.5)
    assert len(result) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest server/tests/test_audio_mixer.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement audio_mixer service**

```python
# server/services/audio_mixer.py
import io
import struct
import wave


def _read_wav(wav_bytes: bytes) -> dict:
    with wave.open(io.BytesIO(wav_bytes), 'rb') as wav:
        return {
            'channels': wav.getnchannels(),
            'sample_width': wav.getsampwidth(),
            'framerate': wav.getframerate(),
            'frames': wav.readframes(wav.getnframes()),
        }


def _resample_linear(frames: bytes, src_rate: int, dst_rate: int, sample_width: int, channels: int) -> bytes:
    if src_rate == dst_rate:
        return frames
    num_src_samples = len(frames) // (sample_width * channels)
    ratio = src_rate / dst_rate
    num_dst_samples = int(num_src_samples / ratio)
    out = bytearray()
    for i in range(num_dst_samples):
        src_pos = i * ratio
        idx = int(src_pos)
        frac = src_pos - idx
        byte_idx = idx * sample_width * channels
        next_byte_idx = min(byte_idx + sample_width * channels, len(frames) - sample_width * channels)
        if byte_idx >= len(frames) or next_byte_idx < 0:
            out.extend(b'\x00' * sample_width * channels)
            continue
        s1 = struct.unpack('<h', frames[byte_idx:byte_idx + 2])[0]
        s2 = struct.unpack('<h', frames[next_byte_idx:next_byte_idx + 2])[0]
        interpolated = int(s1 + frac * (s2 - s1))
        interpolated = max(-32768, min(32767, interpolated))
        out.extend(struct.pack('<h', interpolated))
    return bytes(out)


def _loop_or_crop(frames: bytes, target_frames: int, sample_width: int, channels: int) -> bytes:
    frame_bytes = sample_width * channels
    total_frames = len(frames) // frame_bytes
    if total_frames >= target_frames:
        return frames[:target_frames * frame_bytes]
    result = bytearray()
    while len(result) < target_frames * frame_bytes:
        remaining = target_frames * frame_bytes - len(result)
        chunk = frames[:min(len(frames), remaining)]
        result.extend(chunk)
    return bytes(result)


def _apply_fade(frames: bytes, fade_in_sec: float, fade_out_sec: float, 
                sample_width: int, channels: int, framerate: int) -> bytes:
    if fade_in_sec <= 0 and fade_out_sec <= 0:
        return frames
    frame_bytes = sample_width * channels
    total_frames = len(frames) // frame_bytes
    result = bytearray(frames)
    fade_in_frames = int(fade_in_sec * framerate)
    fade_out_frames = int(fade_out_sec * framerate)
    for i in range(min(fade_in_frames, total_frames)):
        gain = i / fade_in_frames
        for c in range(channels):
            offset = i * frame_bytes + c * sample_width
            sample = struct.unpack('<h', result[offset:offset + 2])[0]
            sample = int(sample * gain)
            result[offset:offset + 2] = struct.pack('<h', max(-32768, min(32767, sample)))
    for i in range(min(fade_out_frames, total_frames)):
        idx = total_frames - 1 - i
        gain = i / fade_out_frames
        for c in range(channels):
            offset = idx * frame_bytes + c * sample_width
            sample = struct.unpack('<h', result[offset:offset + 2])[0]
            sample = int(sample * gain)
            result[offset:offset + 2] = struct.pack('<h', max(-32768, min(32767, sample)))
    return bytes(result)


def _mix_pcm(voice: bytes, bgm: bytes, ambient: bytes, 
             voice_vol: float, bgm_vol: float, ambient_vol: float) -> bytes:
    max_len = max(len(voice), len(bgm), len(ambient))
    result = bytearray(max_len)
    for i in range(0, max_len, 2):
        v = struct.unpack('<h', voice[i:i + 2])[0] if i < len(voice) else 0
        b = struct.unpack('<h', bgm[i:i + 2])[0] if i < len(bgm) else 0
        a = struct.unpack('<h', ambient[i:i + 2])[0] if i < len(ambient) else 0
        mixed = int(v * voice_vol + b * bgm_vol + a * ambient_vol)
        mixed = max(-32768, min(32767, mixed))
        result[i:i + 2] = struct.pack('<h', mixed)
    return bytes(result)


def mix_audio(
    voice_wav: bytes,
    bgm_wav: bytes | None = None,
    ambient_wav: bytes | None = None,
    voice_volume: float = 1.0,
    bgm_volume: float = 0.18,
    ambient_volume: float = 0.12,
    fade_in: float = 1.0,
    fade_out: float = 1.5,
) -> bytes:
    voice_info = _read_wav(voice_wav)
    channels = voice_info['channels']
    sample_width = voice_info['sample_width']
    framerate = voice_info['framerate']
    voice_frames = voice_info['frames']
    total_samples = len(voice_frames) // (sample_width * channels)

    bgm_frames = b''
    if bgm_wav:
        bgm_info = _read_wav(bgm_wav)
        bgm_data = bgm_info['frames']
        if bgm_info['framerate'] != framerate:
            bgm_data = _resample_linear(bgm_data, bgm_info['framerate'], framerate, sample_width, channels)
        bgm_frames = _loop_or_crop(bgm_data, total_samples, sample_width, channels)
        bgm_frames = _apply_fade(bgm_frames, fade_in, fade_out, sample_width, channels, framerate)

    ambient_frames = b''
    if ambient_wav:
        ambient_info = _read_wav(ambient_wav)
        ambient_data = ambient_info['frames']
        if ambient_info['framerate'] != framerate:
            ambient_data = _resample_linear(ambient_data, ambient_info['framerate'], framerate, sample_width, channels)
        ambient_frames = _loop_or_crop(ambient_data, total_samples, sample_width, channels)

    mixed = _mix_pcm(voice_frames, bgm_frames, ambient_frames, voice_volume, bgm_volume, ambient_volume)

    output = io.BytesIO()
    with wave.open(output, 'wb') as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(framerate)
        wav.writeframes(mixed)
    return output.getvalue()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest server/tests/test_audio_mixer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server/services/audio_mixer.py server/tests/test_audio_mixer.py
git commit -m "feat: add audio mixer service with BGM/ambient support"
```

---

## Task 4: Video Renderer Service

**Files:**
- Create: `server/services/video_renderer.py`
- Test: `server/tests/test_video_renderer.py`

- [ ] **Step 1: Write failing test for video renderer**

```python
# server/tests/test_video_renderer.py
import pytest


def test_get_motion_function_slow_zoom_in():
    from server.services.video_renderer import get_motion_function
    fn = get_motion_function('slow_zoom_in')
    assert fn is not None
    result = fn(0.5, 1080, 1920, 0.0, 10.0)
    assert 'position' in result
    assert 'size' in result


def test_get_motion_function_unknown():
    from server.services.video_renderer import get_motion_function
    fn = get_motion_function('unknown_motion')
    assert fn is not None
    result = fn(0.5, 1080, 1920, 0.0, 10.0)
    assert 'position' in result


def test_motion_slow_zoom_in():
    from server.services.video_renderer import motion_slow_zoom_in
    result = motion_slow_zoom_in(0.0, 1080, 1920, 0.0, 10.0)
    assert result['scale'] == 1.0
    result = motion_slow_zoom_in(1.0, 1080, 1920, 0.0, 10.0)
    assert result['scale'] > 1.0


def test_motion_breathing_zoom():
    from server.services.video_renderer import motion_breathing_zoom
    result = motion_breathing_zoom(0.0, 1080, 1920, 0.0, 10.0)
    assert result['scale'] >= 1.0


def test_motion_pan_left_right():
    from server.services.video_renderer import motion_pan_left_right
    result = motion_pan_left_right(0.0, 1080, 1920, 0.0, 10.0)
    assert 'position' in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest server/tests/test_video_renderer.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement video_renderer service**

```python
# server/services/video_renderer.py
import math


def motion_slow_zoom_in(t: float, width: int, height: int, start: float, end: float) -> dict:
    progress = (t - start) / (end - start) if end > start else 0
    scale = 1.0 + 0.15 * progress
    offset_x = (width * scale - width) / 2
    offset_y = (height * scale - height) / 2
    return {
        'scale': scale,
        'position': (-offset_x, -offset_y),
        'size': (int(width * scale), int(height * scale)),
    }


def motion_slow_zoom_out(t: float, width: int, height: int, start: float, end: float) -> dict:
    progress = (t - start) / (end - start) if end > start else 0
    scale = 1.15 - 0.15 * progress
    offset_x = (width * scale - width) / 2
    offset_y = (height * scale - height) / 2
    return {
        'scale': scale,
        'position': (-offset_x, -offset_y),
        'size': (int(width * scale), int(height * scale)),
    }


def motion_pan_left_right(t: float, width: int, height: int, start: float, end: float) -> dict:
    progress = (t - start) / (end - start) if end > start else 0
    scale = 1.2
    pan_range = width * (scale - 1)
    offset_x = pan_range * progress
    return {
        'scale': scale,
        'position': (-offset_x, 0),
        'size': (int(width * scale), int(height * scale)),
    }


def motion_breathing_zoom(t: float, width: int, height: int, start: float, end: float) -> dict:
    progress = (t - start) / (end - start) if end > start else 0
    scale = 1.05 + 0.05 * math.sin(progress * 2 * math.pi)
    offset_x = (width * scale - width) / 2
    offset_y = (height * scale - height) / 2
    return {
        'scale': scale,
        'position': (-offset_x, -offset_y),
        'size': (int(width * scale), int(height * scale)),
    }


def motion_shake(t: float, width: int, height: int, start: float, end: float) -> dict:
    progress = (t - start) / (end - start) if end > start else 0
    intensity = 8 * (1 - progress)
    offset_x = intensity * math.sin(t * 30)
    offset_y = intensity * math.cos(t * 25)
    return {
        'scale': 1.05,
        'position': (offset_x, offset_y),
        'size': (int(width * 1.05), int(height * 1.05)),
    }


def motion_fade_in(t: float, width: int, height: int, start: float, end: float) -> dict:
    return {
        'scale': 1.0,
        'position': (0, 0),
        'size': (width, height),
        'opacity': min(1.0, (t - start) / 0.5) if end - start > 0.5 else 1.0,
    }


MOTION_FUNCTIONS = {
    'slow_zoom_in': motion_slow_zoom_in,
    'slow_zoom_out': motion_slow_zoom_out,
    'pan_left_right': motion_pan_left_right,
    'breathing_zoom': motion_breathing_zoom,
    'shake': motion_shake,
    'fade_in': motion_fade_in,
}


def get_motion_function(motion_key: str):
    return MOTION_FUNCTIONS.get(motion_key, motion_slow_zoom_in)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest server/tests/test_video_renderer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server/services/video_renderer.py server/tests/test_video_renderer.py
git commit -m "feat: add video renderer with motion effects"
```

---

## Task 5: Video Scene Planner Service

**Files:**
- Create: `server/services/video_scene_planner.py`
- Test: `server/tests/test_video_scene_planner.py`

- [ ] **Step 1: Write failing test for scene planner**

```python
# server/tests/test_video_scene_planner.py
import pytest


def test_plan_scenes_single_image():
    from server.services.video_scene_planner import plan_scenes
    scenes = plan_scenes(
        subtitle_segments=['你好', '世界'],
        chunk_durations=[1.0, 1.0],
        images=['scene1.png'],
        motion='slow_zoom_in',
        gap=0.3,
    )
    assert len(scenes) == 1
    assert scenes[0]['image'] == 'scene1.png'
    assert scenes[0]['start'] == 0.0


def test_plan_scenes_multiple_images():
    from server.services.video_scene_planner import plan_scenes
    scenes = plan_scenes(
        subtitle_segments=['你好', '世界', '测试'],
        chunk_durations=[1.0, 1.0, 1.0],
        images=['scene1.png', 'scene2.png'],
        motion='slow_zoom_in',
        gap=0.3,
    )
    assert len(scenes) == 2
    assert scenes[0]['image'] == 'scene1.png'
    assert scenes[1]['image'] == 'scene2.png'


def test_plan_scenes_default_motion():
    from server.services.video_scene_planner import plan_scenes
    scenes = plan_scenes(
        subtitle_segments=['你好'],
        chunk_durations=[2.0],
        images=['scene1.png'],
    )
    assert scenes[0]['motion'] == 'slow_zoom_in'


def test_plan_scenes_empty():
    from server.services.video_scene_planner import plan_scenes
    scenes = plan_scenes(
        subtitle_segments=[],
        chunk_durations=[],
        images=[],
    )
    assert len(scenes) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest server/tests/test_video_scene_planner.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement video_scene_planner service**

```python
# server/services/video_scene_planner.py
import math


def plan_scenes(
    subtitle_segments: list[str],
    chunk_durations: list[float],
    images: list[str],
    motion: str = 'slow_zoom_in',
    gap: float = 0.3,
) -> list[dict]:
    if not subtitle_segments or not images:
        return []
    
    total_duration = sum(chunk_durations) + gap * max(0, len(chunk_durations) - 1)
    num_images = len(images)
    
    if num_images == 1:
        return [{
            'index': 1,
            'image': images[0],
            'start': 0.0,
            'end': total_duration,
            'subtitle_start_index': 1,
            'subtitle_end_index': len(subtitle_segments),
            'motion': motion,
            'transition_in': 'fade',
            'transition_out': 'fade',
        }]
    
    scenes = []
    current_time = 0.0
    subs_per_scene = math.ceil(len(subtitle_segments) / num_images)
    
    for i, image in enumerate(images):
        start_sub = i * subs_per_scene
        end_sub = min((i + 1) * subs_per_scene, len(subtitle_segments))
        
        scene_duration = sum(chunk_durations[start_sub:end_sub])
        if end_sub < len(subtitle_segments):
            scene_duration += gap * max(0, end_sub - start_sub - 1)
        
        scenes.append({
            'index': i + 1,
            'image': image,
            'start': round(current_time, 3),
            'end': round(current_time + scene_duration, 3),
            'subtitle_start_index': start_sub + 1,
            'subtitle_end_index': end_sub,
            'motion': motion,
            'transition_in': 'fade' if i > 0 else None,
            'transition_out': 'fade' if i < num_images - 1 else None,
        })
        current_time += scene_duration + gap
    
    return scenes
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest server/tests/test_video_scene_planner.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server/services/video_scene_planner.py server/tests/test_video_scene_planner.py
git commit -m "feat: add video scene planner service"
```

---

## Task 6: CapCut Package Service

**Files:**
- Create: `server/services/capcut_package.py`
- Test: `server/tests/test_capcut_package.py`

- [ ] **Step 1: Write failing test for capcut package**

```python
# server/tests/test_capcut_package.py
import json
import zipfile
import io
import pytest


def test_build_manifest():
    from server.services.capcut_package import build_manifest
    manifest = build_manifest(
        title='测试视频',
        template_key='xianxia_narration',
        duration=10.0,
        resolution=[1080, 1920],
        scenes=[{'index': 1, 'image': 'scene1.png'}],
        voice_chunks=[{'index': 1, 'text': '你好'}],
        subtitles=[{'index': 1, 'text': '你好', 'start': 0.0, 'end': 1.0}],
        audio={'voice': 'voice.wav', 'mixed': 'mixed.wav', 'bgm': 'bgm.mp3'},
    )
    assert manifest['title'] == '测试视频'
    assert manifest['template_key'] == 'xianxia_narration'
    assert manifest['duration'] == 10.0


def test_build_capcut_zip():
    from server.services.capcut_package import build_capcut_zip
    zip_bytes = build_capcut_zip(
        title='测试视频',
        video_bytes=b'fake-video',
        voice_audio=b'fake-voice',
        mixed_audio=b'fake-mixed',
        srt_content='1\n00:00:00,000 --> 00:00:01,000\n你好\n',
        manifest={'title': '测试', 'duration': 1.0},
        scene_files=[('scenes/001.png', b'fake-image')],
        bgm_bytes=b'fake-bgm',
    )
    assert len(zip_bytes) > 0
    with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
        names = zf.namelist()
        assert '测试视频_成片.mp4' in names
        assert '测试视频_完整旁白.wav' in names
        assert '测试视频_同步字幕.srt' in names
        assert 'manifest.json' in names
        assert 'scenes/001.png' in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest server/tests/test_capcut_package.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement capcut_package service**

```python
# server/services/capcut_package.py
import io
import json
import zipfile


def build_manifest(
    title: str,
    template_key: str,
    duration: float,
    resolution: list[int],
    scenes: list[dict],
    voice_chunks: list[dict],
    subtitles: list[dict],
    audio: dict,
) -> dict:
    return {
        'title': title,
        'template_key': template_key,
        'duration': round(duration, 3),
        'resolution': resolution,
        'scenes': scenes,
        'voice_chunks': voice_chunks,
        'subtitles': subtitles,
        'audio': audio,
    }


def build_capcut_zip(
    title: str,
    video_bytes: bytes,
    voice_audio: bytes,
    mixed_audio: bytes,
    srt_content: str,
    manifest: dict,
    scene_files: list[tuple[str, bytes]],
    bgm_bytes: bytes | None = None,
) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f'{title}_成片.mp4', video_bytes)
        zf.writestr(f'{title}_完整旁白.wav', voice_audio)
        zf.writestr(f'{title}_混音音频.wav', mixed_audio)
        zf.writestr(f'{title}_同步字幕.srt', srt_content)
        zf.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
        for filename, data in scene_files:
            zf.writestr(filename, data)
        if bgm_bytes:
            zf.writestr('audio/bgm.mp3', bgm_bytes)
    buf.seek(0)
    return buf.getvalue()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest server/tests/test_capcut_package.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server/services/capcut_package.py server/tests/test_capcut_package.py
git commit -m "feat: add CapCut package export service"
```

---

## Task 7: Video Job Service

**Files:**
- Create: `server/services/video_job.py`
- Test: `server/tests/test_video_job.py`

- [ ] **Step 1: Write failing test for video job service**

```python
# server/tests/test_video_job.py
import pytest


def test_create_job(app, db):
    from server.services.video_job import create_job
    job = create_job(title='Test Video', request={'template_key': 'xianxia_narration'})
    assert job.job_id is not None
    assert job.status == 'queued'
    assert job.title == 'Test Video'


def test_get_job(app, db):
    from server.services.video_job import create_job, get_job
    job = create_job(title='Test Video', request={})
    found = get_job(job.job_id)
    assert found is not None
    assert found.title == 'Test Video'


def test_get_job_not_found(app, db):
    from server.services.video_job import get_job
    found = get_job('nonexistent')
    assert found is None


def test_update_job_progress(app, db):
    from server.services.video_job import create_job, update_job_progress
    job = create_job(title='Test', request={})
    update_job_progress(job.job_id, 0.5, 'rendering', 'Rendering video')
    from server.services.video_job import get_job
    updated = get_job(job.job_id)
    assert updated.status == 'rendering'
    assert updated.progress == 0.5


def test_update_job_completed(app, db):
    from server.services.video_job import create_job, update_job_completed
    job = create_job(title='Test', request={})
    update_job_completed(job.job_id, '/tmp/output.mp4', '{}')
    from server.services.video_job import get_job
    updated = get_job(job.job_id)
    assert updated.status == 'completed'
    assert updated.progress == 1.0


def test_update_job_failed(app, db):
    from server.services.video_job import create_job, update_job_failed
    job = create_job(title='Test', request={})
    update_job_failed(job.job_id, 'Something went wrong')
    from server.services.video_job import get_job
    updated = get_job(job.job_id)
    assert updated.status == 'failed'
    assert updated.error_message == 'Something went wrong'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest server/tests/test_video_job.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement video_job service**

```python
# server/services/video_job.py
import json
import uuid
from server.models import db, VideoJob


def create_job(title: str, request: dict) -> VideoJob:
    job = VideoJob(
        job_id=f'video-job-{uuid.uuid4().hex[:12]}',
        title=title,
        status='queued',
        request_json=json.dumps(request, ensure_ascii=False),
    )
    db.session.add(job)
    db.session.commit()
    return job


def get_job(job_id: str) -> VideoJob | None:
    return VideoJob.query.filter_by(job_id=job_id).first()


def update_job_progress(job_id: str, progress: float, stage: str, message: str = ''):
    job = get_job(job_id)
    if not job:
        return
    job.status = stage if stage in ('planning', 'synthesizing_voice', 'mixing_audio', 'rendering_video', 'packaging') else job.status
    job.progress = progress
    job.stage = stage
    job.message = message
    db.session.commit()


def update_job_completed(job_id: str, output_path: str, manifest_json: str = '{}'):
    job = get_job(job_id)
    if not job:
        return
    job.status = 'completed'
    job.progress = 1.0
    job.output_path = output_path
    job.manifest_json = manifest_json
    job.message = '视频生成完成'
    db.session.commit()


def update_job_failed(job_id: str, error_message: str):
    job = get_job(job_id)
    if not job:
        return
    job.status = 'failed'
    job.error_message = error_message
    job.message = f'生成失败: {error_message}'
    db.session.commit()


def list_jobs(limit: int = 20) -> list[VideoJob]:
    return VideoJob.query.order_by(VideoJob.created_at.desc()).limit(limit).all()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest server/tests/test_video_job.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server/services/video_job.py server/tests/test_video_job.py
git commit -m "feat: add video job service for async task management"
```

---

## Task 8: Update Video Routes

**Files:**
- Modify: `server/routes/video.py`
- Modify: `server/app.py`
- Test: `server/tests/test_video.py`

- [ ] **Step 1: Write failing test for new video routes**

```python
# Add to server/tests/test_video.py

def test_get_templates(client):
    response = client.get('/api/video/templates')
    assert response.status_code == 200
    data = response.get_json()
    assert len(data) == 5
    assert data[0]['template_key'] == 'xianxia_narration'


def test_get_template_by_key(client):
    response = client.get('/api/video/templates/xianxia_narration')
    assert response.status_code == 200
    data = response.get_json()
    assert data['template_key'] == 'xianxia_narration'


def test_get_template_not_found(client):
    response = client.get('/api/video/templates/nonexistent')
    assert response.status_code == 404


def test_create_video_job_missing_params(client):
    response = client.post('/api/video/jobs', json={})
    assert response.status_code == 400


def test_create_video_job(client):
    response = client.post('/api/video/jobs', json={
        'title': 'Test Video',
        'template_key': 'xianxia_narration',
        'text_id': 1,
        'images': ['scene1.png'],
    })
    assert response.status_code == 202
    data = response.get_json()
    assert 'job_id' in data
    assert data['status'] == 'queued'


def test_get_video_job_status(client):
    create_resp = client.post('/api/video/jobs', json={
        'title': 'Test',
        'template_key': 'xianxia_narration',
        'text_id': 1,
        'images': ['scene1.png'],
    })
    job_id = create_resp.get_json()['job_id']
    response = client.get(f'/api/video/jobs/{job_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['job_id'] == job_id


def test_get_video_job_not_found(client):
    response = client.get('/api/video/jobs/nonexistent')
    assert response.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest server/tests/test_video.py -v`
Expected: FAIL (new routes not implemented)

- [ ] **Step 3: Seed templates on app startup**

```python
# Modify server/app.py - add after db.create_all()
from server.services.video_template import seed_builtin_templates
seed_builtin_templates()
```

- [ ] **Step 4: Add new routes to video.py**

```python
# Add to server/routes/video.py after existing routes

from flask import Blueprint, request, jsonify
from server.services.video_template import get_all_templates, get_template_by_key, seed_builtin_templates
from server.services.video_job import create_job, get_job, list_jobs


@video_bp.route('/api/video/templates', methods=['GET'])
def get_templates():
    templates = get_all_templates()
    return jsonify([t.to_dict() for t in templates])


@video_bp.route('/api/video/templates/<template_key>', methods=['GET'])
def get_template(template_key):
    template = get_template_by_key(template_key)
    if not template:
        return jsonify({'error': '模板不存在'}), 404
    return jsonify(template.to_dict())


@video_bp.route('/api/video/jobs', methods=['POST'])
def create_video_job():
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求数据不能为空'}), 400
    
    title = data.get('title', '未命名')
    template_key = data.get('template_key', 'xianxia_narration')
    
    template = get_template_by_key(template_key)
    if not template:
        return jsonify({'error': f'模板 {template_key} 不存在'}), 400
    
    job = create_job(title=title, request=data)
    return jsonify({
        'job_id': job.job_id,
        'status': job.status,
    }), 202


@video_bp.route('/api/video/jobs/<job_id>', methods=['GET'])
def get_video_job(job_id):
    job = get_job(job_id)
    if not job:
        return jsonify({'error': '任务不存在'}), 404
    return jsonify(job.to_dict())


@video_bp.route('/api/video/jobs', methods=['GET'])
def list_video_jobs():
    jobs = list_jobs()
    return jsonify([j.to_dict() for j in jobs])
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest server/tests/test_video.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add server/routes/video.py server/app.py server/tests/test_video.py
git commit -m "feat: add video template and job API endpoints"
```

---

## Task 9: Integration - Wire up app.py

**Files:**
- Modify: `server/app.py`

- [ ] **Step 1: Add template seeding to app startup**

```python
# In server/app.py, inside create_app(), after db.create_all():
from server.services.video_template import seed_builtin_templates
seed_builtin_templates()
```

- [ ] **Step 2: Run full test suite**

Run: `uv run pytest`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add server/app.py
git commit -m "feat: seed builtin video templates on startup"
```

---

## Task 10: Final Verification

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest -v`
Expected: All tests PASS

- [ ] **Step 2: Verify backward compatibility**

The old endpoint `POST /api/video/generate` still works unchanged.

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: video generation backend - templates, jobs, scene planner, audio mixer, renderer, CapCut package"
```

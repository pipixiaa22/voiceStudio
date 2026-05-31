# Video Voice Workflow Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make video generation consume existing voice workflows so generated videos reuse emotional segment audio, voice profiles, pauses, cached WAVs, and workflow subtitle timelines.

**Architecture:** Extract voice workflow audio synthesis/cache helpers from the Flask route into a service that can be reused by voice workflow routes and video jobs. Split video job voice-track preparation into text and workflow branches, then keep the existing rendering and packaging flow while ensuring video rendering uses the mixed audio. Frontend changes pass `voice_source`, `voice_workflow_id`, and uploaded WAV BGM paths through the existing video wizard.

**Tech Stack:** Python 3.13, Flask, SQLAlchemy, pytest, moviepy, wave, Vue 3, Pinia, Ant Design Vue, Axios

---

## File Structure

| File | Responsibility |
|------|----------------|
| `server/services/voice_workflow_audio.py` | Shared workflow audio cache, synthesis, status, and full-track assembly helpers |
| `server/routes/voice_workflows.py` | Import shared helpers instead of owning private synthesis/cache functions |
| `server/services/video_job.py` | Add workflow voice-track branch, text voice-track helper, mixed-audio rendering, manifest merge |
| `server/routes/video.py` | Validate workflow job payloads and add WAV BGM upload endpoint |
| `server/tests/test_voice_workflow_audio.py` | Unit tests for cache reuse and workflow voice-track assembly |
| `server/tests/test_video_job.py` | Unit tests for workflow branch selection, manifest source, and text fallback |
| `server/tests/test_video.py` | Route tests for upload-audio and workflow job validation |
| `web/src/api/index.js` | Add `videoApi.uploadAudio` |
| `web/src/components/video/AudioMixStep.vue` | Upload WAV BGM, validate workflow selection, emit stable audio options |
| `web/src/components/video/VideoGenerateModal.vue` | Include voice workflow fields in create-job payload |
| `web/src/components/video/VideoPreviewStep.vue` | Display selected audio source |
| `server/tests/test_video_workflow_frontend_source.py` | Source-level frontend guard tests |

---

## Task 1: Extract Voice Workflow Audio Helpers

**Files:**
- Create: `server/services/voice_workflow_audio.py`
- Modify: `server/routes/voice_workflows.py`
- Test: `server/tests/test_voice_workflow_audio.py`

- [ ] **Step 1: Write failing tests for shared cache and track helpers**

Create `server/tests/test_voice_workflow_audio.py`:

```python
import io
import wave

from server.models import db
from server.models.voice_workflow import VoiceWorkflow, VoiceWorkflowEdge, VoiceWorkflowSegment


def _wav_bytes(duration_seconds=0.1, framerate=8000):
    output = io.BytesIO()
    frames = b'\x00\x00' * int(duration_seconds * framerate)
    with wave.open(output, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(framerate)
        wav.writeframes(frames)
    return output.getvalue()


def _workflow_with_segments():
    workflow = VoiceWorkflow(title='配音工程', source_content='第一句。第二句。')
    workflow.settings = {'subtitle_max_chars': 20}
    db.session.add(workflow)
    db.session.flush()
    first = VoiceWorkflowSegment(
        workflow_id=workflow.id,
        order_index=1,
        text='第一句。',
        emotion='calm',
        pause_before_ms=0,
        pause_after_ms=100,
    )
    second = VoiceWorkflowSegment(
        workflow_id=workflow.id,
        order_index=2,
        text='第二句。',
        emotion='tense',
        pause_before_ms=50,
        pause_after_ms=0,
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
    return workflow


def test_synthesize_or_cache_segment_reuses_ready_cache(app, tmp_path, monkeypatch):
    from server.services import voice_workflow_audio
    from server.services.voice_workflow_service import build_audio_fingerprint

    monkeypatch.setattr(voice_workflow_audio, 'CACHE_DIR', str(tmp_path))
    workflow = _workflow_with_segments()
    segment = workflow.segments[0]
    expected = build_audio_fingerprint({**segment.to_dict(), 'model': 'mimo-v2.5-tts-voicedesign'})
    cache_path = voice_workflow_audio.cache_path_for_fingerprint(workflow.id, expected)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    audio = _wav_bytes()
    cache_path.write_bytes(audio)
    segment.audio_status = 'ready'
    segment.audio_fingerprint = expected
    db.session.commit()

    def fail_synthesize(*args, **kwargs):
        raise AssertionError('cache hit should not synthesize')

    monkeypatch.setattr(voice_workflow_audio, 'synthesize_emotion_segment', fail_synthesize)

    result = voice_workflow_audio.synthesize_or_cache_segment(workflow, segment, 'key', {}, reuse_cache=True)

    assert result['cached'] is True
    assert result['audio_bytes'] == audio
    assert result['duration'] > 0


def test_build_voice_track_from_workflow_returns_manifest_and_timeline(app, tmp_path, monkeypatch):
    from server.services import voice_workflow_audio

    monkeypatch.setattr(voice_workflow_audio, 'CACHE_DIR', str(tmp_path))
    workflow = _workflow_with_segments()
    audio = _wav_bytes()

    def fake_synthesize(workflow, segment, api_key, data, reuse_cache=True, persist_cache=True):
        return {
            'audio_base64': '',
            'audio_bytes': audio,
            'wav_info': voice_workflow_audio.read_wav_info(audio),
            'duration': 0.1,
            'fingerprint': f'f-{segment.id}',
            'cached': False,
            'segment_dict': segment.to_dict(),
        }

    monkeypatch.setattr(voice_workflow_audio, 'synthesize_or_cache_segment', fake_synthesize)

    result = voice_workflow_audio.build_voice_track_from_workflow(
        workflow.id,
        {'api_key': 'key', 'subtitle_options': {'max_chars': 20}},
    )

    assert result['source'] == 'voice_workflow'
    assert result['workflow_id'] == workflow.id
    assert result['voice_audio']
    assert result['subtitle_timeline'][0]['text'] == '第一句。'
    assert result['manifest']['source'] == 'voice_workflow'
    assert result['manifest']['workflow_id'] == workflow.id
    assert [item['text'] for item in result['voice_chunks']] == ['第一句。', '第二句。']
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest server/tests/test_voice_workflow_audio.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'server.services.voice_workflow_audio'`.

- [ ] **Step 3: Create shared service**

Create `server/services/voice_workflow_audio.py`:

```python
import base64
import os
from pathlib import Path

from server.models import db
from server.models.voice_workflow import VoiceWorkflow
from server.services import voice_profile_repository as repo
from server.services.audio_package import read_wav_info
from server.services.audio_postprocess import concat_emotional_wavs, build_emotional_subtitle_timeline
from server.services.emotional_tts import synthesize_emotion_segment
from server.services.voice_workflow_service import build_audio_fingerprint, build_workflow_manifest, ordered_segments

CACHE_DIR = 'outputs/voice_workflow_cache'


def profile_audio_voice(profile):
    if not profile:
        return None
    if profile.get('source_type') == 'voice_clone':
        return profile.get('voice_sample_data_uri')
    return profile.get('builtin_voice')


def cache_path_for_fingerprint(workflow_id, fingerprint):
    safe_name = fingerprint.replace('sha256:', '')[:16]
    return Path(CACHE_DIR) / str(workflow_id) / f'{safe_name}.wav'


def synthesize_or_cache_segment(
    workflow,
    segment,
    api_key,
    data,
    *,
    reuse_cache=True,
    persist_cache=True,
):
    profile_id = segment.voice_profile_id or workflow.default_voice_profile_id
    profile = repo.get_profile_by_id(int(profile_id)) if profile_id else None
    model = (profile or {}).get('model') or 'mimo-v2.5-tts-voicedesign'
    segment_dict = segment.to_dict()
    expected_fingerprint = build_audio_fingerprint({**segment_dict, 'model': model})
    cache_path = cache_path_for_fingerprint(workflow.id, expected_fingerprint)
    is_cached = (
        reuse_cache
        and segment.audio_status == 'ready'
        and segment.audio_fingerprint == expected_fingerprint
        and cache_path.exists()
    )

    if is_cached:
        audio_bytes = cache_path.read_bytes()
        info = read_wav_info(audio_bytes)
        duration = info['frames'] / info['framerate']
        return {
            'audio_base64': base64.b64encode(audio_bytes).decode('ascii'),
            'audio_bytes': audio_bytes,
            'wav_info': info,
            'duration': duration,
            'fingerprint': expected_fingerprint,
            'cached': True,
            'segment_dict': segment_dict,
        }

    result = synthesize_emotion_segment(
        api_key,
        segment_dict,
        voice_profile=profile,
        fallback_voice_description=data.get('voice_description', ''),
        style_tags=(profile or {}).get('style_tags'),
        model=model,
        voice=profile_audio_voice(profile),
    )
    audio_bytes = result['audio_bytes']
    info = result['wav_info']
    duration = result['duration']

    if persist_cache:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(audio_bytes)
        segment.audio_path = str(cache_path)
        segment.audio_fingerprint = expected_fingerprint
        segment.audio_status = 'ready'

    return {
        'audio_base64': result['audio_base64'],
        'audio_bytes': audio_bytes,
        'wav_info': info,
        'duration': duration,
        'fingerprint': expected_fingerprint,
        'cached': False,
        'segment_dict': segment_dict,
    }


def cache_status_for_segment(workflow, segment):
    profile_id = segment.voice_profile_id or workflow.default_voice_profile_id
    profile = repo.get_profile_by_id(int(profile_id)) if profile_id else None
    model = (profile or {}).get('model') or 'mimo-v2.5-tts-voicedesign'
    segment_dict = segment.to_dict()
    expected_fingerprint = build_audio_fingerprint({**segment_dict, 'model': model})
    cache_path = cache_path_for_fingerprint(workflow.id, expected_fingerprint)
    ready = (
        segment.audio_status == 'ready'
        and segment.audio_fingerprint == expected_fingerprint
        and cache_path.exists()
    )
    return {
        'segment_id': segment.id,
        'order_index': segment.order_index,
        'text': segment.text,
        'status': 'ready' if ready else (segment.audio_status or 'missing'),
        'ready': ready,
        'expected_fingerprint': expected_fingerprint,
        'cached_path': str(cache_path) if ready else None,
    }


def subtitle_max_chars_for_workflow(workflow, data):
    requested = (data.get('subtitle_options') or {}).get('max_chars')
    if requested is not None:
        try:
            parsed = int(requested)
        except (TypeError, ValueError):
            raise ValueError('subtitle_options.max_chars 必须是 1 到 200 之间的整数')
        if parsed < 1 or parsed > 200:
            raise ValueError('subtitle_options.max_chars 必须是 1 到 200 之间的整数')
        return parsed
    return (workflow.settings or {}).get('subtitle_max_chars', 20)


def build_voice_track_from_workflow(workflow_id: int, request_data: dict) -> dict:
    workflow = VoiceWorkflow.query.get(workflow_id)
    if not workflow:
        raise ValueError('配音工程不存在')
    api_key = request_data.get('api_key')
    if not api_key:
        raise ValueError('缺少 API Key')

    segments = ordered_segments(workflow)
    if not segments:
        raise ValueError('当前配音工程没有可用语句')

    audio_items = []
    durations = []
    manifest_segments = []
    reuse_cache = ((request_data.get('export_options') or {}).get('reuse_cache', True) is not False)
    for index, segment in enumerate(segments, 1):
        try:
            result = synthesize_or_cache_segment(
                workflow,
                segment,
                api_key,
                request_data,
                reuse_cache=reuse_cache,
            )
        except Exception as exc:
            raise ValueError(f'第 {segment.order_index} 句语音生成失败: {exc}') from exc
        filename = f'segments/{index:03d}.wav'
        audio_items.append({'wav_info': result['wav_info'], 'segment': result['segment_dict']})
        durations.append(result['duration'])
        manifest_segments.append({
            **result['segment_dict'],
            'filename': filename,
            'duration': round(result['duration'], 3),
            'cached': result['cached'],
        })

    db.session.commit()
    full_audio = concat_emotional_wavs(audio_items)
    subtitle_max_chars = subtitle_max_chars_for_workflow(workflow, request_data)
    timeline = build_emotional_subtitle_timeline(
        [segment.to_dict() for segment in segments],
        durations,
        subtitle_max_chars=subtitle_max_chars,
    )
    if not timeline:
        raise ValueError('字幕时间轴为空')
    manifest = build_workflow_manifest(workflow, manifest_segments, timeline)
    manifest['source'] = 'voice_workflow'
    manifest['workflow_id'] = workflow.id
    return {
        'source': 'voice_workflow',
        'workflow_id': workflow.id,
        'voice_audio': full_audio,
        'subtitle_timeline': timeline,
        'manifest': manifest,
        'voice_chunks': manifest_segments,
        'duration': round(timeline[-1]['end'], 3),
    }
```

- [ ] **Step 4: Update voice workflow routes to import the shared helpers**

Modify imports in `server/routes/voice_workflows.py`:

```python
from server.services.voice_workflow_audio import (
    CACHE_DIR,
    cache_path_for_fingerprint,
    cache_status_for_segment,
    synthesize_or_cache_segment,
)
```

Remove these route-local helper definitions:

```python
def _profile_audio_voice(profile):
    ...

def _cache_path_for_fingerprint(workflow_id, fingerprint):
    ...

def _synthesize_or_cache_segment(...):
    ...

def _cache_status_for_segment(workflow, segment):
    ...
```

Replace call sites:

```python
result = synthesize_or_cache_segment(workflow, segment, api_key, data, reuse_cache=False)
status = cache_status_for_segment(workflow, segment)
cache_dir = os.path.join(CACHE_DIR, str(workflow_id))
```

If any code needs a string path from `cache_path_for_fingerprint`, wrap it with `str(...)`.

- [ ] **Step 5: Run focused tests**

Run:

```bash
uv run pytest server/tests/test_voice_workflow_audio.py server/tests/test_voice_workflows_routes.py server/tests/test_voice_workflow_service.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add server/services/voice_workflow_audio.py server/routes/voice_workflows.py server/tests/test_voice_workflow_audio.py
git commit -m "feat: share voice workflow audio helpers"
```

---

## Task 2: Add Workflow Voice Track Branch to Video Jobs

**Files:**
- Modify: `server/services/video_job.py`
- Test: `server/tests/test_video_job.py`

- [ ] **Step 1: Write failing tests for workflow branch and text fallback**

Append to `server/tests/test_video_job.py`:

```python
import json


def test_build_voice_track_uses_workflow_when_requested(app, monkeypatch):
    from server.services import video_job

    captured = {}

    def fake_workflow_track(workflow_id, request_data):
        captured['workflow_id'] = workflow_id
        captured['request_data'] = request_data
        return {
            'source': 'voice_workflow',
            'workflow_id': workflow_id,
            'voice_audio': b'voice',
            'subtitle_timeline': [{'index': 1, 'text': '第一句。', 'start': 0, 'end': 1}],
            'manifest': {'source': 'voice_workflow', 'workflow_id': workflow_id},
            'voice_chunks': [{'text': '第一句。'}],
            'duration': 1,
        }

    monkeypatch.setattr(video_job, 'build_voice_track_from_workflow', fake_workflow_track)

    result = video_job.build_voice_track({
        'voice_source': 'workflow',
        'voice_workflow_id': 42,
        'api_key': 'key',
    })

    assert result['source'] == 'voice_workflow'
    assert captured['workflow_id'] == 42


def test_build_voice_track_falls_back_to_text_mode(app, db, monkeypatch):
    from server.models import Text
    from server.services import video_job

    text = Text(title='文本', content='你好。')
    db.session.add(text)
    db.session.commit()

    def fake_text_track(request_data):
        return {
            'source': 'text',
            'voice_audio': b'voice',
            'subtitle_timeline': [{'index': 1, 'text': '你好。', 'start': 0, 'end': 1}],
            'voice_chunks': [{'index': 1, 'text': '你好。'}],
            'duration': 1,
        }

    monkeypatch.setattr(video_job, 'build_voice_track_from_text', fake_text_track)

    result = video_job.build_voice_track({'text_id': text.id, 'api_key': 'key'})

    assert result['source'] == 'text'


def test_merge_video_manifest_marks_workflow_source():
    from server.services.video_job import merge_video_manifest

    manifest = merge_video_manifest(
        title='视频',
        template_key='xianxia_narration',
        resolution=[1080, 1920],
        scenes=[{'imagePath': '/tmp/a.png'}],
        audio_options={'bgm_enabled': False},
        voice_track={
            'source': 'voice_workflow',
            'workflow_id': 7,
            'duration': 1.2,
            'subtitle_timeline': [{'text': '第一句。', 'start': 0, 'end': 1.2}],
            'voice_chunks': [{'text': '第一句。'}],
            'manifest': {'source': 'voice_workflow', 'workflow_id': 7, 'segments': []},
        },
        warnings=['BGM 已开启但没有上传 WAV 文件'],
    )

    assert manifest['source'] == 'voice_workflow'
    assert manifest['workflow_id'] == 7
    assert manifest['video']['audio_options']['bgm_enabled'] is False
    assert manifest['video']['warnings'] == ['BGM 已开启但没有上传 WAV 文件']
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest server/tests/test_video_job.py -v
```

Expected: FAIL because `build_voice_track`, `build_voice_track_from_text`, and `merge_video_manifest` do not exist.

- [ ] **Step 3: Add voice-track helper functions**

Modify `server/services/video_job.py` near the top-level helpers:

```python
from server.services.voice_workflow_audio import build_voice_track_from_workflow


def build_voice_track(request_data: dict) -> dict:
    voice_source = request_data.get('voice_source') or (request_data.get('audio_options') or {}).get('voice_source')
    workflow_id = request_data.get('voice_workflow_id') or (request_data.get('audio_options') or {}).get('voice_workflow_id')
    if voice_source == 'workflow' and workflow_id:
        return build_voice_track_from_workflow(int(workflow_id), request_data)
    return build_voice_track_from_text(request_data)
```

Add `build_voice_track_from_text()` by moving the current text-mode code out of `_process_job()`:

```python
def build_voice_track_from_text(request_data: dict) -> dict:
    from splitter import split_text
    from server.services.tts_planner import plan_speech_chunks
    from server.services.tts_provider import TTSProvider
    from server.services.audio_package import read_wav_info, concat_wavs
    from server.services.subtitle_timeline import build_subtitle_timeline
    from server.services.voice_prompt import build_voice_prompt

    text_id = request_data.get('text_id')
    if text_id:
        from server.models import Text
        text = Text.query.get(text_id)
        if not text:
            raise ValueError('文本不存在')
        content = text.content
    else:
        content = request_data.get('content', '')
        if not content:
            raise ValueError('没有提供文本内容')

    max_chars = request_data.get('subtitle_options', {}).get('max_chars', 20)
    subtitle_segments = split_text(content, max_chars=max_chars)
    if not subtitle_segments:
        raise ValueError('没有有效的字幕段')

    chunk_max_chars = request_data.get('synthesis_options', {}).get('chunk_max_chars', 200)
    chunks = plan_speech_chunks(subtitle_segments, max_chars=chunk_max_chars)

    api_key = request_data.get('api_key')
    if not api_key:
        raise ValueError('缺少 API Key')

    voice_profile = _resolve_default_voice_profile(request_data)
    voice_description = build_voice_prompt(
        voice_profile,
        raw_description=request_data.get('voice_description', ''),
        fallback_description='温柔的女性声音',
    )
    voice_model = (voice_profile or {}).get('model') or 'mimo-v2.5-tts-voicedesign'
    voice_style_tags = (voice_profile or {}).get('style_tags')
    audio_voice = _audio_voice_from_profile(voice_profile)
    provider = TTSProvider(api_key)

    wav_infos = []
    chunk_files = []
    for chunk in chunks:
        audio_b64 = provider.synthesize(
            voice_description,
            chunk.text,
            style_tags=voice_style_tags,
            model=voice_model,
            voice=audio_voice,
        )
        audio_bytes = base64.b64decode(audio_b64)
        wav_info = read_wav_info(audio_bytes)
        wav_infos.append(wav_info)
        chunk_files.append((f'chunks/{chunk.index:03d}.wav', audio_bytes))

    gap = request_data.get('subtitle_options', {}).get('gap', 0.3)
    full_voice_audio = concat_wavs(wav_infos, gap=gap)
    chunk_durations = [info['frames'] / info['framerate'] for info in wav_infos]
    subtitle_timeline = build_subtitle_timeline(chunks, chunk_durations, gap=gap, subtitle_segments=subtitle_segments)
    return {
        'source': 'text',
        'voice_audio': full_voice_audio,
        'subtitle_timeline': subtitle_timeline,
        'voice_chunks': [{'index': c.index, 'text': c.text} for c in chunks],
        'chunk_files': chunk_files,
        'duration': subtitle_timeline[-1]['end'] if subtitle_timeline else 0,
    }
```

Add `merge_video_manifest()`:

```python
def merge_video_manifest(title, template_key, resolution, scenes, audio_options, voice_track, warnings=None):
    manifest = dict(voice_track.get('manifest') or {})
    manifest.update({
        'title': title,
        'source': voice_track.get('source', manifest.get('source', 'text')),
        'template_key': template_key,
        'duration': voice_track.get('duration', 0),
        'resolution': resolution,
        'voice_chunks': voice_track.get('voice_chunks', []),
        'subtitles': voice_track.get('subtitle_timeline', []),
        'video': {
            'scenes': scenes,
            'audio_options': audio_options,
            'warnings': warnings or [],
        },
    })
    if voice_track.get('workflow_id'):
        manifest['workflow_id'] = voice_track['workflow_id']
    return manifest
```

- [ ] **Step 4: Refactor `_process_job()` to call `build_voice_track()`**

In `server/services/video_job.py`, replace the inline text splitting/synthesis/timeline block with:

```python
voice_track = build_voice_track(request_data)
full_voice_audio = voice_track['voice_audio']
subtitle_timeline = voice_track['subtitle_timeline']
chunks_for_manifest = voice_track.get('voice_chunks', [])
```

Keep progress updates before and after this call:

```python
update_job_progress(job_id, 0.2, 'synthesizing_voice', '正在生成或复用配音音频')
```

On `ValueError`, call:

```python
update_job_failed(job_id, str(exc))
return
```

Keep generic exceptions under the outer exception handler.

- [ ] **Step 5: Run focused tests**

Run:

```bash
uv run pytest server/tests/test_video_job.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add server/services/video_job.py server/tests/test_video_job.py
git commit -m "feat: route video jobs through voice workflows"
```

---

## Task 3: Render with Mixed Audio and Preserve Workflow Manifest

**Files:**
- Modify: `server/services/video_job.py`
- Test: `server/tests/test_video_job.py`

- [ ] **Step 1: Write failing tests for BGM warning and mixed render path**

Append to `server/tests/test_video_job.py`:

```python
def test_prepare_audio_mix_warns_when_bgm_enabled_without_path():
    from server.services.video_job import prepare_audio_mix

    result = prepare_audio_mix(
        voice_audio=b'voice',
        audio_options={'bgm_enabled': True},
        audio_config={'voice_volume': 1.0, 'bgm_volume': 0.18},
    )

    assert result['mixed_audio'] == b'voice'
    assert result['warnings'] == ['BGM 已开启但没有上传 WAV 文件']


def test_generate_simple_video_accepts_audio_path_keyword():
    import inspect
    from server.services.video_job import _generate_simple_video

    signature = inspect.signature(_generate_simple_video)

    assert 'audio_path' in signature.parameters
    assert 'voice_path' not in signature.parameters
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest server/tests/test_video_job.py -v
```

Expected: FAIL because `prepare_audio_mix` does not exist and `_generate_simple_video` still uses `voice_path`.

- [ ] **Step 3: Add `prepare_audio_mix()`**

Modify `server/services/video_job.py`:

```python
def prepare_audio_mix(voice_audio: bytes, audio_options: dict, audio_config: dict) -> dict:
    from server.services.audio_mixer import mix_audio

    warnings = []
    bgm_wav = None
    bgm_path = audio_options.get('bgm_path')
    if audio_options.get('bgm_enabled'):
        if bgm_path and os.path.exists(bgm_path):
            with open(bgm_path, 'rb') as f:
                bgm_wav = f.read()
        else:
            warnings.append('BGM 已开启但没有上传 WAV 文件')

    mixed_audio = voice_audio
    if bgm_wav or audio_options.get('ambient_enabled'):
        mixed_audio = mix_audio(
            voice_wav=voice_audio,
            bgm_wav=bgm_wav,
            ambient_wav=None,
            voice_volume=audio_config.get('voice_volume', 1.0),
            bgm_volume=audio_options.get('bgm_volume', audio_config.get('bgm_volume', 0.18)),
            ambient_volume=audio_options.get('ambient_volume', audio_config.get('ambient_volume', 0.12)),
            fade_in=audio_options.get('bgm_fade_in', audio_config.get('fade_in', 1.0)),
            fade_out=audio_options.get('bgm_fade_out', audio_config.get('fade_out', 1.5)),
        )
    return {'mixed_audio': mixed_audio, 'warnings': warnings}
```

- [ ] **Step 4: Use mixed audio for rendering**

In `_process_job()` replace the inline mix block with:

```python
audio_options = request_data.get('audio_options', {})
mix_result = prepare_audio_mix(full_voice_audio, audio_options, audio_config)
mixed_audio = mix_result['mixed_audio']
audio_warnings = mix_result['warnings']
```

Inside the temp directory:

```python
voice_path = os.path.join(tmpdir, 'voice.wav')
with open(voice_path, 'wb') as f:
    f.write(full_voice_audio)

mixed_path = os.path.join(tmpdir, 'mixed.wav')
with open(mixed_path, 'wb') as f:
    f.write(mixed_audio)
```

Call video rendering with:

```python
_generate_simple_video(
    audio_path=mixed_path,
    subtitle_timeline=subtitle_timeline,
    output_path=output_path,
    width=resolution[0],
    height=resolution[1],
    fps=fps,
    image_path=image_path,
)
```

Rename `_generate_simple_video(voice_path: str, ...)` to:

```python
def _generate_simple_video(audio_path: str, subtitle_timeline: list, output_path: str, width: int, height: int, fps: int, image_path: str = None):
    audio = AudioFileClip(audio_path)
```

- [ ] **Step 5: Merge manifest with workflow/text voice track**

Replace the existing `build_manifest(...)` call with:

```python
manifest = merge_video_manifest(
    title=title,
    template_key=template_key,
    resolution=resolution,
    scenes=scenes_data,
    audio_options=audio_options,
    voice_track=voice_track,
    warnings=audio_warnings,
)
```

Keep `build_capcut_zip()` usage with:

```python
zip_bytes = build_capcut_zip(
    title=title,
    video_bytes=video_bytes,
    voice_audio=full_voice_audio,
    mixed_audio=mixed_audio,
    srt_content=srt_content,
    manifest=manifest,
    scene_files=[],
)
```

- [ ] **Step 6: Run focused tests**

Run:

```bash
uv run pytest server/tests/test_video_job.py server/tests/test_audio_mixer.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add server/services/video_job.py server/tests/test_video_job.py
git commit -m "feat: render video jobs with mixed audio"
```

---

## Task 4: Add WAV BGM Upload Route and Workflow Job Validation

**Files:**
- Modify: `server/routes/video.py`
- Modify: `web/src/api/index.js`
- Test: `server/tests/test_video.py`

- [ ] **Step 1: Write failing route tests**

Append to `server/tests/test_video.py`:

```python
import io


def test_upload_audio_accepts_wav(client):
    data = {
        'audio': (io.BytesIO(b'RIFF....WAVEfmt '), 'bgm.wav'),
    }

    response = client.post('/api/video/upload-audio', data=data, content_type='multipart/form-data')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['filename'].endswith('.wav')
    assert payload['path'].endswith('.wav')


def test_upload_audio_rejects_non_wav(client):
    data = {
        'audio': (io.BytesIO(b'not-wav'), 'bgm.mp3'),
    }

    response = client.post('/api/video/upload-audio', data=data, content_type='multipart/form-data')

    assert response.status_code == 400
    assert response.get_json()['error'] == '第一阶段只支持 WAV 格式 BGM'


def test_create_video_job_rejects_missing_workflow_id(client):
    response = client.post('/api/video/jobs', json={
        'title': 'Test Video',
        'template_key': 'xianxia_narration',
        'voice_source': 'workflow',
    })

    assert response.status_code == 400
    assert response.get_json()['error'] == '请选择配音工程'
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest server/tests/test_video.py -v
```

Expected: FAIL because `/api/video/upload-audio` does not exist and workflow validation is incomplete.

- [ ] **Step 3: Validate workflow job payloads**

Modify `create_video_job()` in `server/routes/video.py`:

```python
voice_source = data.get('voice_source') or (data.get('audio_options') or {}).get('voice_source')
voice_workflow_id = data.get('voice_workflow_id') or (data.get('audio_options') or {}).get('voice_workflow_id')
if voice_source == 'workflow':
    if not voice_workflow_id:
        return jsonify({'error': '请选择配音工程'}), 400
    from server.models.voice_workflow import VoiceWorkflow
    workflow = VoiceWorkflow.query.get(int(voice_workflow_id))
    if not workflow:
        return jsonify({'error': '配音工程不存在'}), 404
    data['voice_source'] = 'workflow'
    data['voice_workflow_id'] = int(voice_workflow_id)
```

Remove or replace the existing permissive `voice_workflow_id` block that silently ignores missing workflows.

- [ ] **Step 4: Add upload-audio route**

Add to `server/routes/video.py` near `upload_video_image()`:

```python
@video_bp.route('/api/video/upload-audio', methods=['POST'])
def upload_video_audio():
    if 'audio' not in request.files:
        return jsonify({'error': '没有上传音频'}), 400

    audio_file = request.files['audio']
    if not audio_file.filename:
        return jsonify({'error': '没有选择文件'}), 400

    ext = os.path.splitext(audio_file.filename)[1].lower()
    if ext != '.wav':
        return jsonify({'error': '第一阶段只支持 WAV 格式 BGM'}), 400

    upload_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'outputs',
        'uploads',
        'audio',
    )
    os.makedirs(upload_dir, exist_ok=True)

    import uuid
    filename = f'{uuid.uuid4().hex}{ext}'
    filepath = os.path.join(upload_dir, filename)
    audio_file.save(filepath)

    return jsonify({
        'filename': filename,
        'path': filepath,
    })
```

- [ ] **Step 5: Add frontend API method**

Modify `web/src/api/index.js`:

```js
uploadAudio: (formData) => api.post('/video/upload-audio', formData, {
  headers: { 'Content-Type': 'multipart/form-data' }
}),
```

Place it next to `uploadImage`.

- [ ] **Step 6: Run focused tests**

Run:

```bash
uv run pytest server/tests/test_video.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add server/routes/video.py web/src/api/index.js server/tests/test_video.py
git commit -m "feat: upload wav bgm for video jobs"
```

---

## Task 5: Complete Frontend Video Wizard Payload

**Files:**
- Modify: `web/src/components/video/AudioMixStep.vue`
- Modify: `web/src/components/video/VideoGenerateModal.vue`
- Modify: `web/src/components/video/VideoPreviewStep.vue`
- Test: `server/tests/test_video_workflow_frontend_source.py`

- [ ] **Step 1: Write failing source-level frontend tests**

Create `server/tests/test_video_workflow_frontend_source.py`:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_video_generate_modal_sends_voice_workflow_payload():
    source = (ROOT / 'web/src/components/video/VideoGenerateModal.vue').read_text()

    assert 'voice_source:' in source
    assert 'voice_workflow_id:' in source
    assert "audioOptions.value.voice_source" in source
    assert "audioOptions.value.voice_workflow_id" in source


def test_audio_mix_step_uploads_wav_bgm_and_validates_workflow():
    source = (ROOT / 'web/src/components/video/AudioMixStep.vue').read_text()

    assert 'videoApi.uploadAudio' in source
    assert 'accept=".wav"' in source
    assert '请选择配音工程' in source
    assert 'bgm_path' in source


def test_video_preview_step_displays_audio_source():
    source = (ROOT / 'web/src/components/video/VideoPreviewStep.vue').read_text()

    assert '音频来源' in source
    assert '配音工程' in source
    assert 'voice_source' in source
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
uv run pytest server/tests/test_video_workflow_frontend_source.py -v
```

Expected: FAIL because frontend code does not yet include these strings.

- [ ] **Step 3: Update `AudioMixStep.vue`**

Modify imports:

```js
import { message } from 'ant-design-vue'
import { videoApi, voiceWorkflowsApi } from '../../api'
```

Initialize `localOptions` with `bgm_path`:

```js
const localOptions = ref({
  voice_source: 'generate',
  voice_workflow_id: null,
  bgm_path: null,
  ...props.audioOptions,
})
```

Change upload accept:

```vue
accept=".wav"
```

Replace `handleBgmUpload`:

```js
const handleBgmUpload = async (file) => {
  if (!file.name.toLowerCase().endsWith('.wav')) {
    message.error('第一阶段只支持 WAV 格式 BGM')
    return false
  }
  const formData = new FormData()
  formData.append('audio', file)
  try {
    const { data } = await videoApi.uploadAudio(formData)
    bgmFile.value = file
    localOptions.value.bgm_path = data.path
    emit('update:audioOptions', { ...localOptions.value })
    message.success('BGM 已上传')
  } catch (error) {
    message.error(error.response?.data?.error || '上传 BGM 失败')
  }
  return false
}
```

Update `handleNext`:

```js
const handleNext = () => {
  if (localOptions.value.voice_source === 'workflow' && !localOptions.value.voice_workflow_id) {
    message.error('请选择配音工程')
    return
  }
  emit('update:audioOptions', { ...localOptions.value })
  emit('next')
}
```

- [ ] **Step 4: Update `VideoGenerateModal.vue` payload**

Extend initial `audioOptions` and reset block with:

```js
voice_source: props.prefill?.audio_options?.voice_source || 'generate',
voice_workflow_id: props.prefill?.audio_options?.voice_workflow_id || null,
bgm_path: props.prefill?.audio_options?.bgm_path || null,
```

Add top-level fields to `videoApi.createJob()`:

```js
voice_source: audioOptions.value.voice_source || 'generate',
voice_workflow_id: audioOptions.value.voice_workflow_id || null,
```

- [ ] **Step 5: Update `VideoPreviewStep.vue`**

Add a description row near the audio summary:

```vue
<a-descriptions-item label="音频来源">
  {{ audioOptions.voice_source === 'workflow' ? `配音工程 #${audioOptions.voice_workflow_id}` : '实时生成' }}
</a-descriptions-item>
```

Ensure `audioOptions` already exists in props; if not, add it:

```js
audioOptions: { type: Object, default: () => ({}) },
```

- [ ] **Step 6: Run focused tests**

Run:

```bash
uv run pytest server/tests/test_video_workflow_frontend_source.py -v
```

Expected: PASS.

If frontend package scripts are available, also run:

```bash
cd web && pnpm run build
```

Expected: production build succeeds.

- [ ] **Step 7: Commit**

```bash
git add web/src/components/video/AudioMixStep.vue web/src/components/video/VideoGenerateModal.vue web/src/components/video/VideoPreviewStep.vue server/tests/test_video_workflow_frontend_source.py
git commit -m "feat: send voice workflows from video wizard"
```

---

## Task 6: End-to-End Regression Tests and Cleanup

**Files:**
- Modify only files touched by earlier tasks if verification reveals issues

- [ ] **Step 1: Run backend integration slice**

Run:

```bash
uv run pytest server/tests/test_voice_workflow_audio.py server/tests/test_voice_workflows_routes.py server/tests/test_video_job.py server/tests/test_video.py server/tests/test_audio_mixer.py -v
```

Expected: PASS.

- [ ] **Step 2: Run full Python test suite**

Run:

```bash
uv run pytest
```

Expected: PASS.

- [ ] **Step 3: Run frontend build**

Run:

```bash
cd web && pnpm run build
```

Expected: PASS and static assets are regenerated under `server/static/`.

- [ ] **Step 4: Inspect git diff**

Run:

```bash
git diff --stat
git status --short
```

Expected: only task-related files are modified or newly generated. Existing unrelated dirty files from before this plan may still appear; do not revert them.

- [ ] **Step 5: Commit final verification fixes if needed**

If verification required fixes:

```bash
git add <fixed-files>
git commit -m "fix: stabilize video voice workflow integration"
```

If no fixes were needed, do not create an empty commit.

---

## Self-Review Notes

- Spec coverage: The plan covers backend workflow branch, cache reuse service extraction, emotional subtitle timeline reuse, manifest source metadata, text fallback, WAV BGM upload, frontend payload, preview display, and verification.
- Scope control: The plan keeps environment sound libraries and mp3/m4a transcoding out of this phase.
- TDD compliance: Each implementation task starts with a failing test command and an expected failure before production code changes.

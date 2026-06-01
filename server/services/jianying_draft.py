import json
import os
import re
import shutil
import time
import uuid
from pathlib import Path


MOYING_TRACK_PREFIX = '墨影字幕'
SRT_TIME_RE = re.compile(
    r'(?P<start>\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(?P<end>\d{2}:\d{2}:\d{2}[,.]\d{3})'
)


def parse_srt_timeline(srt_content: str) -> list[dict]:
    """Parse SRT content into timeline entries accepted by Jianying injection."""
    blocks = re.split(r'\n\s*\n', (srt_content or '').replace('\r\n', '\n').strip())
    timeline = []
    for block in blocks:
        lines = [line.strip('\ufeff') for line in block.split('\n') if line.strip()]
        if len(lines) < 2:
            continue
        time_index = next((idx for idx, line in enumerate(lines) if SRT_TIME_RE.search(line)), None)
        if time_index is None:
            continue
        match = SRT_TIME_RE.search(lines[time_index])
        text = '\n'.join(lines[time_index + 1:]).strip()
        if not text:
            continue
        timeline.append({
            'text': text,
            'start': _parse_srt_timestamp(match.group('start')),
            'end': _parse_srt_timestamp(match.group('end')),
        })
    if not timeline:
        raise ValueError('SRT 内容中没有可写入的字幕')
    return timeline


def inject_subtitles_into_draft(
    draft_path: str,
    subtitles: list[dict],
    *,
    track_name: str = MOYING_TRACK_PREFIX,
) -> dict:
    """Write subtitles into an unencrypted Jianying/CapCut desktop draft JSON."""
    if not subtitles:
        raise ValueError('没有可写入剪映工程的字幕')

    draft_file = _resolve_draft_file(draft_path)
    data = _read_draft_json(draft_file)
    _ensure_draft_shape(data)

    normalized = _normalize_subtitles(subtitles)
    backup_path = _backup_draft_file(draft_file)

    _remove_existing_moying_track(data, track_name)
    track, materials, speeds = _build_text_track(track_name, normalized)
    data['materials']['texts'].extend(materials)
    data['materials']['speeds'].extend(speeds)
    data['tracks'].append(track)
    data['duration'] = max(int(data.get('duration') or 0), max(item['end_us'] for item in normalized))
    data['update_time'] = int(time.time())

    draft_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    _touch_meta_info(draft_file.parent)

    return {
        'ok': True,
        'draft_file': str(draft_file),
        'backup_path': str(backup_path),
        'track_name': track_name,
        'subtitle_count': len(normalized),
    }


def _parse_srt_timestamp(value: str) -> float:
    timestamp = value.replace(',', '.')
    hours, minutes, rest = timestamp.split(':')
    seconds, millis = rest.split('.')
    return (
        int(hours) * 3600
        + int(minutes) * 60
        + int(seconds)
        + int(millis) / 1000
    )


def _resolve_draft_file(draft_path: str) -> Path:
    if not draft_path or not str(draft_path).strip():
        raise ValueError('请填写剪映工程目录')

    path = Path(os.path.expanduser(str(draft_path).strip())).resolve()
    if path.is_file():
        if path.name not in ('draft_content.json', 'draft_info.json'):
            raise ValueError('请选择 draft_content.json、draft_info.json 或其所在工程目录')
        return path

    if not path.exists() or not path.is_dir():
        raise ValueError('剪映工程目录不存在')

    for filename in ('draft_content.json', 'draft_info.json'):
        candidate = path / filename
        if candidate.exists():
            return candidate
    raise ValueError('该目录下没有找到 draft_content.json 或 draft_info.json')


def _read_draft_json(draft_file: Path) -> dict:
    try:
        return json.loads(draft_file.read_text(encoding='utf-8'))
    except UnicodeDecodeError as exc:
        raise ValueError('剪映草稿文件不是可读 JSON，可能是新版加密草稿') from exc
    except json.JSONDecodeError as exc:
        raise ValueError('剪映草稿文件不是合法 JSON，可能是新版加密草稿') from exc


def _ensure_draft_shape(data: dict):
    if not isinstance(data, dict):
        raise ValueError('剪映草稿内容格式异常')
    data.setdefault('materials', {})
    data['materials'].setdefault('texts', [])
    data['materials'].setdefault('speeds', [])
    data.setdefault('tracks', [])
    if not isinstance(data['tracks'], list) or not isinstance(data['materials']['texts'], list):
        raise ValueError('剪映草稿缺少可写入的 tracks/materials.texts 结构')


def _normalize_subtitles(subtitles: list[dict]) -> list[dict]:
    normalized = []
    for index, item in enumerate(subtitles, 1):
        text = str(item.get('text') or '').strip()
        if not text:
            continue
        start = float(item.get('start') or 0)
        end = float(item.get('end') or 0)
        if end <= start:
            raise ValueError(f'第 {index} 条字幕时间范围无效')
        normalized.append({
            'text': text,
            'start_us': round(start * 1_000_000),
            'end_us': round(end * 1_000_000),
            'duration_us': round((end - start) * 1_000_000),
        })
    if not normalized:
        raise ValueError('没有可写入剪映工程的有效字幕文本')
    return normalized


def _backup_draft_file(draft_file: Path) -> Path:
    timestamped = draft_file.with_name(f'{draft_file.name}.bak-{time.strftime("%Y%m%d-%H%M%S")}')
    stable = draft_file.with_name(f'{draft_file.name}.bak')
    shutil.copy2(draft_file, timestamped)
    shutil.copy2(draft_file, stable)
    return stable


def _remove_existing_moying_track(data: dict, track_name: str):
    removed_material_ids = set()
    remaining_tracks = []
    for track in data['tracks']:
        name = track.get('name') or ''
        should_remove = track.get('type') == 'text' and (name == track_name or name.startswith(f'{MOYING_TRACK_PREFIX}-'))
        if should_remove:
            for segment in track.get('segments') or []:
                if segment.get('material_id'):
                    removed_material_ids.add(segment['material_id'])
        else:
            remaining_tracks.append(track)

    data['tracks'] = remaining_tracks
    if removed_material_ids:
        data['materials']['texts'] = [
            material for material in data['materials']['texts']
            if material.get('id') not in removed_material_ids
        ]


def _build_text_track(track_name: str, subtitles: list[dict]) -> tuple[dict, list[dict], list[dict]]:
    track_id = _new_id()
    segments = []
    materials = []
    speeds = []
    for render_index, item in enumerate(subtitles):
        material_id = _new_id()
        speed_id = _new_id()
        item['material_id'] = material_id
        item['speed_id'] = speed_id
        materials.append(_build_text_material(item['text'], material_id))
        speeds.append(_build_speed_material(speed_id))
        segments.append(_build_text_segment(item, render_index))

    return {
        'attribute': 0,
        'flag': 0,
        'id': track_id,
        'is_default_name': False,
        'name': track_name,
        'segments': segments,
        'type': 'text',
    }, materials, speeds


def _build_text_segment(item: dict, render_index: int) -> dict:
    return {
        'cartoon': False,
        'clip': {
            'alpha': 1.0,
            'flip': {'horizontal': False, 'vertical': False},
            'rotation': 0.0,
            'scale': {'x': 1.0, 'y': 1.0},
            'transform': {'x': 0.0, 'y': -0.8},
        },
        'common_keyframes': [],
        'enable_adjust': True,
        'enable_color_correct_adjust': False,
        'enable_color_curves': True,
        'enable_color_match_adjust': False,
        'enable_color_wheels': True,
        'enable_lut': True,
        'enable_smart_color_adjust': False,
        'extra_material_refs': [item['speed_id']],
        'group_id': '',
        'hdr_settings': None,
        'id': _new_id(),
        'intensifies_audio': False,
        'is_placeholder': False,
        'is_tone_modify': False,
        'keyframe_refs': [],
        'last_nonzero_volume': 1.0,
        'material_id': item['material_id'],
        'render_index': render_index,
        'reverse': False,
        'source_timerange': {'start': 0, 'duration': item['duration_us']},
        'speed': 1.0,
        'target_timerange': {'start': item['start_us'], 'duration': item['duration_us']},
        'template_id': '',
        'template_scene': 'default',
        'track_attribute': 0,
        'track_render_index': 0,
        'uniform_scale': {'on': True, 'value': 1.0},
        'visible': True,
        'volume': 1.0,
    }


def _build_text_material(text: str, material_id: str) -> dict:
    utf16_len = len(text.encode('utf-16-le'))
    content = {
        'styles': [{
            'fill': {
                'alpha': 1.0,
                'content': {
                    'render_type': 'solid',
                    'solid': {'alpha': 1.0, 'color': [1.0, 1.0, 1.0]},
                },
            },
            'range': [0, utf16_len],
            'size': 8.0,
            'bold': False,
            'italic': False,
            'underline': False,
            'strokes': [{
                'content': {
                    'solid': {'alpha': 1.0, 'color': [0.0, 0.0, 0.0]},
                },
                'width': 0.08,
            }],
        }],
        'text': text,
    }
    return {
        'id': material_id,
        'content': json.dumps(content, ensure_ascii=False),
        'typesetting': 0,
        'alignment': 1,
        'letter_spacing': 0.0,
        'line_spacing': 0.02,
        'line_feed': 1,
        'line_max_width': 0.82,
        'force_apply_line_max_width': False,
        'check_flag': 15,
        'type': 'subtitle',
        'global_alpha': 1.0,
    }


def _build_speed_material(speed_id: str) -> dict:
    return {
        'curve_speed': None,
        'id': speed_id,
        'mode': 0,
        'speed': 1.0,
        'type': 'speed',
    }


def _touch_meta_info(draft_dir: Path):
    meta_file = draft_dir / 'draft_meta_info.json'
    if not meta_file.exists():
        return
    try:
        meta = json.loads(meta_file.read_text(encoding='utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return
    now_us = int(time.time() * 1_000_000)
    if isinstance(meta, dict):
        meta['tm_draft_modified'] = now_us
        meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')


def _new_id() -> str:
    return str(uuid.uuid4()).upper()

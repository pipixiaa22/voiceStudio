import json
import uuid
import threading
import traceback
import os
import tempfile
import base64
from server.models import db, VideoJob
from server.services.voice_workflow_audio import build_voice_track_from_workflow


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
    job.status = stage if stage in ('planning', 'synthesizing_voice', 'mixing_audio', 'rendering', 'rendering_video', 'packaging') else job.status
    job.progress = progress
    job.stage = stage
    job.message = message
    db.session.commit()


def update_job_completed(job_id: str, output_path: str, manifest_json: str = '{}', video_path: str = ''):
    job = get_job(job_id)
    if not job:
        return
    job.status = 'completed'
    job.progress = 1.0
    job.output_path = output_path
    job.manifest_json = manifest_json
    job.video_path = video_path
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


def _resolve_default_voice_profile(request_data: dict) -> dict | None:
    speaker_profiles = request_data.get('speaker_profiles') or {}
    profile_id = (
        speaker_profiles.get('旁白')
        or speaker_profiles.get('default')
        or request_data.get('voice_profile_id')
    )
    if not profile_id:
        snapshot = request_data.get('voice_profile_snapshot')
        return snapshot if isinstance(snapshot, dict) and snapshot else None

    try:
        from server.services import voice_profile_repository as repo
        return repo.get_profile_by_id(int(profile_id))
    except (TypeError, ValueError):
        return None


def _audio_voice_from_profile(profile: dict | None):
    if not profile:
        return None
    if profile.get('source_type') == 'voice_clone':
        return profile.get('voice_sample_data_uri')
    return profile.get('builtin_voice')


def start_job_processing(job_id: str, app):
    """Start background processing of a video job."""
    thread = threading.Thread(target=_process_job, args=(job_id, app), daemon=True)
    thread.start()


def build_voice_track(request_data: dict) -> dict:
    voice_source = request_data.get('voice_source') or (request_data.get('audio_options') or {}).get('voice_source')
    workflow_id = request_data.get('voice_workflow_id') or (request_data.get('audio_options') or {}).get('voice_workflow_id')
    if voice_source == 'workflow' and workflow_id:
        return build_voice_track_from_workflow(int(workflow_id), request_data)
    return build_voice_track_from_text(request_data)


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
        try:
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
        except Exception as exc:
            raise ValueError(f'语音块 {chunk.index} 合成失败: {str(exc)}') from exc

    gap = request_data.get('subtitle_options', {}).get('gap', 0.3)
    full_voice_audio = concat_wavs(wav_infos, gap=gap)
    chunk_durations = [info['frames'] / info['framerate'] for info in wav_infos]
    subtitle_timeline = build_subtitle_timeline(chunks, chunk_durations, gap=gap, subtitle_segments=subtitle_segments)

    return {
        'source': 'text',
        'voice_audio': full_voice_audio,
        'subtitle_timeline': subtitle_timeline,
        'voice_chunks': [{'index': chunk.index, 'text': chunk.text} for chunk in chunks],
        'chunk_files': chunk_files,
        'duration': subtitle_timeline[-1]['end'] if subtitle_timeline else 0,
    }


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


def _process_job(job_id: str, app):
    """Process a video job in the background."""
    with app.app_context():
        try:
            job = get_job(job_id)
            if not job:
                return

            request_data = json.loads(job.request_json)
            title = job.title or '视频'

            # Stage 1: Planning
            update_job_progress(job_id, 0.1, 'planning', '正在规划分镜和语音块')

            from server.services.audio_package import build_srt
            from server.services.audio_mixer import mix_audio
            from server.services.capcut_package import build_manifest, build_capcut_zip

            # Get template config
            template_key = request_data.get('template_key', 'xianxia_narration')
            from server.services.video_template import get_template_config
            template_config = get_template_config(template_key) or {}
            fps = template_config.get('fps', 24)
            resolution = template_config.get('resolution', [1080, 1920])
            audio_config = template_config.get('audio', {})

            # Stage 2: Synthesize voice
            update_job_progress(job_id, 0.2, 'synthesizing_voice', '正在合成语音')

            try:
                voice_track = build_voice_track(request_data)
            except ValueError as exc:
                update_job_failed(job_id, str(exc))
                return

            full_voice_audio = voice_track['voice_audio']
            subtitle_timeline = voice_track['subtitle_timeline']

            # Stage 3: Mix audio
            update_job_progress(job_id, 0.6, 'mixing_audio', '正在混合音频')

            audio_options = request_data.get('audio_options', {})
            mixed_audio = full_voice_audio

            if audio_options.get('bgm_enabled') or audio_options.get('ambient_enabled'):
                bgm_wav = None
                ambient_wav = None

                # TODO: Handle BGM file upload
                # For now, just mix with voice only
                mixed_audio = mix_audio(
                    voice_wav=full_voice_audio,
                    bgm_wav=bgm_wav,
                    ambient_wav=ambient_wav,
                    voice_volume=audio_config.get('voice_volume', 1.0),
                    bgm_volume=audio_options.get('bgm_volume', audio_config.get('bgm_volume', 0.18)),
                    ambient_volume=audio_options.get('ambient_volume', audio_config.get('ambient_volume', 0.12)),
                    fade_in=audio_options.get('bgm_fade_in', audio_config.get('fade_in', 1.0)),
                    fade_out=audio_options.get('bgm_fade_out', audio_config.get('fade_out', 1.5)),
                )

            # Stage 4: Render video
            update_job_progress(job_id, 0.7, 'rendering_video', '正在渲染视频')

            scenes_data = request_data.get('scenes', [])
            images = [s.get('imagePath') for s in scenes_data if s.get('imagePath')]

            with tempfile.TemporaryDirectory() as tmpdir:
                # Save voice audio
                voice_path = os.path.join(tmpdir, 'voice.wav')
                with open(voice_path, 'wb') as f:
                    f.write(full_voice_audio)

                # Create video
                output_path = os.path.join(tmpdir, f'{title}.mp4')

                # Use first image as background if available
                image_path = images[0] if images else None

                # Generate video with moviepy
                _generate_simple_video(
                    voice_path=voice_path,
                    subtitle_timeline=subtitle_timeline,
                    output_path=output_path,
                    width=resolution[0],
                    height=resolution[1],
                    fps=fps,
                    image_path=image_path,
                )

                update_job_progress(job_id, 0.9, 'packaging', '正在打包')

                # Build SRT
                srt_content = build_srt(subtitle_timeline)

                # Build manifest
                manifest = build_manifest(
                    title=title,
                    template_key=template_key,
                    duration=subtitle_timeline[-1]['end'] if subtitle_timeline else 0,
                    resolution=resolution,
                    scenes=[],
                    voice_chunks=voice_track.get('voice_chunks', []),
                    subtitles=subtitle_timeline,
                    audio={'voice': f'{title}_完整旁白.wav', 'mixed': f'{title}_混音音频.wav'},
                )

                # Build ZIP package
                with open(output_path, 'rb') as f:
                    video_bytes = f.read()

                zip_bytes = build_capcut_zip(
                    title=title,
                    video_bytes=video_bytes,
                    voice_audio=full_voice_audio,
                    mixed_audio=mixed_audio,
                    srt_content=srt_content,
                    manifest=manifest,
                    scene_files=[],
                )

                # Save output
                output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'outputs', 'video_jobs')
                os.makedirs(output_dir, exist_ok=True)
                
                # Save MP4 separately for preview
                video_path = os.path.join(output_dir, f'{job_id}.mp4')
                with open(video_path, 'wb') as f:
                    f.write(video_bytes)
                
                # Save ZIP package
                zip_path = os.path.join(output_dir, f'{job_id}.zip')
                with open(zip_path, 'wb') as f:
                    f.write(zip_bytes)

                update_job_completed(job_id, zip_path, json.dumps(manifest, ensure_ascii=False), video_path)

        except Exception as e:
            traceback.print_exc()
            update_job_failed(job_id, str(e))


def _generate_simple_video(voice_path: str, subtitle_timeline: list, output_path: str, width: int, height: int, fps: int, image_path: str = None):
    """Generate a video with image background and subtitles."""
    from moviepy import AudioFileClip, ImageClip, ColorClip, TextClip, CompositeVideoClip
    import traceback

    audio = AudioFileClip(voice_path)
    duration = audio.duration

    # Rescale subtitle timeline to match actual audio duration
    if subtitle_timeline:
        last_end = subtitle_timeline[-1]['end']
        if last_end > 0 and abs(last_end - duration) > 0.5:
            scale = duration / last_end
            for item in subtitle_timeline:
                item['start'] = round(item['start'] * scale, 3)
                item['end'] = round(item['end'] * scale, 3)

    # Create background clip
    if image_path and os.path.exists(image_path):
        bg_clip = ImageClip(image_path).with_duration(duration).resized((width, height))
    else:
        bg_clip = ColorClip(size=(width, height), color=(20, 20, 40)).with_duration(duration)

    # Create subtitle clips
    subtitle_clips = []
    font_size = int(height * 0.03)
    margin_bottom = int(height * 0.1)
    max_text_width = int(width * 0.85)

    # Try to find a working Chinese font
    font_paths = [
        '/System/Library/Fonts/PingFang.ttc',
        '/System/Library/Fonts/STHeiti Light.ttc',
        '/System/Library/Fonts/Hiragino Sans GB.ttc',
        '/System/Library/Fonts/Supplemental/Songti.ttc',
    ]
    
    font_path = None
    for fp in font_paths:
        if os.path.exists(fp):
            font_path = fp
            break

    for item in subtitle_timeline:
        text = item['text']
        start = item['start']
        end = item['end']

        try:
            # Split long text into lines
            wrapped_text = _wrap_text(text, font_size, max_text_width)
            
            txt_clip = TextClip(
                text=wrapped_text,
                font_size=font_size,
                color='white',
                font=font_path,
                stroke_color='black',
                stroke_width=2,
                text_align='center',
                size=(max_text_width, None),
            )
            txt_clip = txt_clip.with_position(('center', height - margin_bottom - txt_clip.h))
            txt_clip = txt_clip.with_start(start).with_end(end)
            subtitle_clips.append(txt_clip)
        except Exception as e:
            print(f"字幕生成失败: {text}, 错误: {e}")
            traceback.print_exc()

    # Composite
    final_clip = CompositeVideoClip([bg_clip] + subtitle_clips)
    final_clip = final_clip.with_audio(audio)

    final_clip.write_videofile(
        output_path,
        fps=fps,
        codec='libx264',
        audio_codec='aac',
        logger=None,
    )

    audio.close()
    bg_clip.close()
    for clip in subtitle_clips:
        clip.close()
    final_clip.close()


def _wrap_text(text: str, font_size: int, max_width: int) -> str:
    """Wrap text to fit within max_width pixels."""
    # Estimate chars per line (Chinese chars are ~font_size wide)
    chars_per_line = max(1, max_width // font_size)
    
    if len(text) <= chars_per_line:
        return text
    
    lines = []
    current_line = ''
    for char in text:
        current_line += char
        if len(current_line) >= chars_per_line:
            lines.append(current_line)
            current_line = ''
    if current_line:
        lines.append(current_line)
    
    return '\n'.join(lines)

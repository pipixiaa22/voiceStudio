import os
import re
import tempfile
from flask import Blueprint, request, jsonify, send_file

video_bp = Blueprint('video', __name__)

RESOLUTIONS = {
    '9:16': (1080, 1920),
    '16:9': (1920, 1080),
    '1:1': (1080, 1080),
}


def get_resolution(aspect_ratio):
    """获取宽高比对应的分辨率。"""
    if aspect_ratio not in RESOLUTIONS:
        raise ValueError(f'不支持的宽高比: {aspect_ratio}')
    return RESOLUTIONS[aspect_ratio]


def _format_ass_timestamp(seconds):
    """将秒数格式化为 ASS 时间戳 H:MM:SS.CC"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centiseconds = int((seconds % 1) * 100)
    return f'{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}'


def generate_ass_subtitle(timeline, width, height):
    """生成 ASS 格式字幕内容。"""
    # 计算字幕参数（基于视频高度）
    font_size = int(height * 0.03)
    margin_v = int(height * 0.1)
    margin_h = int(width * 0.05)

    ass_content = f"""[Script Info]
Title: 字幕工坊生成
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,Microsoft YaHei,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2,1,2,{margin_h},{margin_h},{margin_v},1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""

    for item in timeline:
        start = _format_ass_timestamp(item['start'])
        end = _format_ass_timestamp(item['end'])
        text = item['text'].replace('\n', '\\N')
        ass_content += f'Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n'

    return ass_content


def generate_video(image_path, audio_path, timeline, output_path, width, height):
    """使用 moviepy 合成视频。"""
    from moviepy import ImageClip, AudioFileClip, TextClip, CompositeVideoClip

    # 加载音频获取时长
    audio = AudioFileClip(audio_path)
    duration = audio.duration

    # 创建背景图片 clip
    image_clip = ImageClip(image_path).with_duration(duration).resized((width, height))

    # 创建字幕 clips
    subtitle_clips = []
    font_size = int(height * 0.03)
    margin_bottom = int(height * 0.1)

    for item in timeline:
        text = item['text']
        start = item['start']
        end = item['end']

        # 创建字幕文本 clip
        txt_clip = TextClip(
            text=text,
            font_size=font_size,
            color='white',
            font='/System/Library/Fonts/PingFang.ttc',
            stroke_color='black',
            stroke_width=2,
        )
        txt_clip = txt_clip.with_position(('center', height - margin_bottom - txt_clip.h))
        txt_clip = txt_clip.with_start(start).with_end(end)
        subtitle_clips.append(txt_clip)

    # 合成视频
    final_clip = CompositeVideoClip([image_clip] + subtitle_clips)
    final_clip = final_clip.with_audio(audio)

    # 写入视频文件
    final_clip.write_videofile(
        output_path,
        fps=24,
        codec='libx264',
        audio_codec='aac',
        logger=None,
    )

    # 清理资源
    audio.close()
    image_clip.close()
    for clip in subtitle_clips:
        clip.close()
    final_clip.close()

    return output_path


@video_bp.route('/api/video/generate', methods=['POST'])
def generate():
    """生成静态图片视频。"""
    # 验证参数
    text_id = request.form.get('text_id')
    aspect_ratio = request.form.get('aspect_ratio', '9:16')
    api_key = request.form.get('api_key')
    voice_description = request.form.get('voice_description')

    if not text_id:
        return jsonify({'error': '缺少文本ID'}), 400
    if not api_key:
        return jsonify({'error': '缺少 API Key'}), 400
    if not voice_description:
        return jsonify({'error': '缺少音色描述'}), 400

    # 验证宽高比
    try:
        width, height = get_resolution(aspect_ratio)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    # 验证图片
    if 'image' not in request.files:
        return jsonify({'error': '请上传背景图片'}), 400

    image_file = request.files['image']
    if not image_file.filename:
        return jsonify({'error': '请上传背景图片'}), 400

    # 获取文本内容
    from server.models import Text
    text = Text.query.get(text_id)
    if not text:
        return jsonify({'error': '文本不存在'}), 404

    try:
        # 创建临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            # 保存图片
            image_ext = os.path.splitext(image_file.filename)[1] or '.jpg'
            image_path = os.path.join(tmpdir, f'background{image_ext}')
            image_file.save(image_path)

            # 使用新服务层生成语音和字幕时间轴
            import base64
            from splitter import split_text
            from server.services.tts_provider import TTSProvider
            from server.services.tts_planner import plan_speech_chunks
            from server.services.audio_package import read_wav_info, concat_wavs
            from server.services.subtitle_timeline import build_subtitle_timeline

            # 创建 provider
            provider = TTSProvider(api_key)

            # 分割字幕段
            subtitle_segments = split_text(text.content, max_chars=20)

            # 规划语音块
            chunks = plan_speech_chunks(subtitle_segments, max_chars=200)

            # 逐块合成
            wav_infos = []
            for chunk in chunks:
                audio_b64 = provider.synthesize(voice_description, chunk.text)
                audio_bytes = base64.b64decode(audio_b64)
                wav_info = read_wav_info(audio_bytes)
                wav_infos.append(wav_info)

            # 拼接音频
            full_audio = concat_wavs(wav_infos, gap=0.3)
            audio_path = os.path.join(tmpdir, 'audio.wav')
            with open(audio_path, 'wb') as f:
                f.write(full_audio)

            # 生成字幕时间轴
            chunk_durations = [info['frames'] / info['framerate'] for info in wav_infos]
            timeline = build_subtitle_timeline(chunks, chunk_durations, gap=0.3, subtitle_segments=subtitle_segments)

            # 生成视频
            output_path = os.path.join(tmpdir, 'output.mp4')
            generate_video(image_path, audio_path, timeline, output_path, width, height)

            # 返回视频文件
            return send_file(
                output_path,
                mimetype='video/mp4',
                as_attachment=True,
                download_name=f'{text.title}.mp4',
            )

    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"视频生成错误: {e}")
        print(f"错误详情:\n{error_traceback}")
        return jsonify({'error': f'生成视频失败: {str(e)}', 'traceback': error_traceback}), 500


from server.services.video_template import get_all_templates, get_template_by_key
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

import os
import re
import subprocess
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


def check_ffmpeg():
    """检查 ffmpeg 是否可用。"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def generate_video(image_path, audio_path, ass_content, output_path, width, height):
    """使用 ffmpeg 合成视频。"""
    # 写入 ASS 字幕文件
    ass_path = output_path.replace('.mp4', '.ass')
    with open(ass_path, 'w', encoding='utf-8') as f:
        f.write(ass_content)

    # 构建 ffmpeg 命令
    cmd = [
        'ffmpeg', '-y',
        '-loop', '1',
        '-i', image_path,
        '-i', audio_path,
        '-vf', f'ass={ass_path}',
        '-c:v', 'libx264',
        '-tune', 'stillimage',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-pix_fmt', 'yuv420p',
        '-shortest',
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f'ffmpeg 错误: {result.stderr}')

    # 清理临时 ASS 文件
    if os.path.exists(ass_path):
        os.remove(ass_path)

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

    # 检查 ffmpeg
    if not check_ffmpeg():
        return jsonify({'error': '服务器未安装 ffmpeg'}), 500

    try:
        # 创建临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            # 保存图片
            image_ext = os.path.splitext(image_file.filename)[1] or '.jpg'
            image_path = os.path.join(tmpdir, f'background{image_ext}')
            image_file.save(image_path)

            # 调用 TTS 生成语音
            from server.routes.tts import _call_tts, _read_wav_info, _concat_wavs
            import base64

            # 将文本分段
            from splitter import split_text
            segments = split_text(text.content, max_chars=20)

            # 生成每段语音
            wav_infos = []
            timeline = []
            current_time = 0.0
            gap = 0.3

            for i, seg_text in enumerate(segments):
                audio_b64 = _call_tts(api_key, voice_description, seg_text)
                audio_bytes = base64.b64decode(audio_b64)
                wav_info = _read_wav_info(audio_bytes)
                duration = wav_info['frames'] / wav_info['framerate']

                wav_infos.append(wav_info)
                timeline.append({
                    'start': current_time,
                    'end': current_time + duration,
                    'text': seg_text,
                })
                current_time += duration + gap

            # 拼接音频
            full_audio = _concat_wavs(wav_infos, gap)
            audio_path = os.path.join(tmpdir, 'audio.wav')
            with open(audio_path, 'wb') as f:
                f.write(full_audio)

            # 生成 ASS 字幕
            ass_content = generate_ass_subtitle(timeline, width, height)

            # 生成视频
            output_path = os.path.join(tmpdir, 'output.mp4')
            generate_video(image_path, audio_path, ass_content, output_path, width, height)

            # 返回视频文件
            return send_file(
                output_path,
                mimetype='video/mp4',
                as_attachment=True,
                download_name=f'{text.title}.mp4',
            )

    except Exception as e:
        return jsonify({'error': f'生成视频失败: {str(e)}'}), 500

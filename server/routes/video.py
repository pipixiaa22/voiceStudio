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

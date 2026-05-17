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

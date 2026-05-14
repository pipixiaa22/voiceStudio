# main.py
import argparse
import sys

from splitter import split_text
from srt import generate_srt


def read_input(input_file: str | None) -> str:
    """从文件或标准输入读取文字。"""
    if input_file:
        with open(input_file, "r", encoding="utf-8") as f:
            return f.read()
    print("请输入文字（按 Ctrl+D 结束）：")
    return sys.stdin.read()


def main():
    parser = argparse.ArgumentParser(description="将文字生成 SRT 字幕文件")
    parser.add_argument("input_file", nargs="?", help="输入文件路径")
    parser.add_argument("--speed", type=float, default=5, help="语速（字/秒，默认 5）")
    parser.add_argument("--max-chars", type=int, default=20, help="每段最大字数（默认 20）")
    parser.add_argument("-o", default="output.srt", help="输出文件路径（默认 output.srt）")

    args = parser.parse_args()

    text = read_input(args.input_file)
    segments = split_text(text, max_chars=args.max_chars)

    if not segments:
        print("没有检测到有效文字。")
        return

    srt_content = generate_srt(segments, chars_per_second=args.speed)

    with open(args.o, "w", encoding="utf-8") as f:
        f.write(srt_content)

    print(f"已生成 {len(segments)} 段字幕，保存到 {args.o}")


if __name__ == "__main__":
    main()

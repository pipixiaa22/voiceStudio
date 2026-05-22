# TTS Phase 1：服务层重构 + 智能分块

## 概述

重构 TTS 语音合成功能，将业务逻辑从 Flask 路由提取到服务层，并引入智能分块机制，让语音合成更连贯。

## 目标

1. 提取服务层，降低路由复杂度
2. 引入语音块（SpeechChunk）概念，合并字幕段进行 TTS
3. 新增 sync-package-v2 API
4. 保留旧 API，渐进式迁移
5. 视频生成复用新服务

## 架构

```
server/
├── routes/
│   ├── tts.py          # 保留旧 API 不变
│   └── video.py        # 改用新服务
├── services/
│   ├── tts_provider.py      # 封装 MiMo TTS 请求
│   ├── tts_planner.py       # 字幕段 → 语音块规划
│   ├── audio_package.py     # WAV 读取、拼接、ZIP 打包
│   └── subtitle_timeline.py # 根据 chunk 时长生成字幕时间轴
```

## 核心流程

```
原文 → split_text() → 字幕段列表
         ↓
    tts_planner → 语音块列表 (80-300字)
         ↓
    tts_provider → 每个 chunk 生成 WAV
         ↓
    audio_package → 拼接完整音频 + 生成 SRT + 打包 ZIP
```

## 语音块规划规则

1. 优先按段落分组
2. 段落过长时按句号、问号、叹号、省略号拆成句组
3. 句组过长时再按逗号、分号切分
4. 每个语音块控制在 80-300 中文字符
5. 不跨越角色、旁白、明显情绪变化

## 服务层设计

### tts_provider.py

```python
def call_tts(api_key: str, voice_description: str, text: str) -> bytes:
    """调用 MiMo TTS API，返回 WAV 字节"""
```

### tts_planner.py

```python
@dataclass
class SpeechChunk:
    index: int
    text: str
    subtitle_indices: list[int]  # 包含的字幕段索引

def plan_speech_chunks(subtitle_segments: list[str], max_chars: int = 200) -> list[SpeechChunk]:
    """将字幕段合并为语音块"""
```

### audio_package.py

```python
def read_wav_info(audio_bytes: bytes) -> dict: ...
def concat_wavs(wav_infos: list[dict], gap: float) -> bytes: ...
def build_zip_package(title, full_audio, timeline, chunks) -> bytes: ...
```

### subtitle_timeline.py

```python
def build_subtitle_timeline(chunks: list[SpeechChunk], chunk_durations: list[float], gap: float) -> list[dict]:
    """根据语音块时长生成字幕时间轴"""
```

## API 设计

### POST /api/tts/sync-package-v2

**请求：**
```json
{
  "api_key": "tts-key",
  "title": "作品标题",
  "content": "完整文本",
  "voice_description": "温柔女声",
  "subtitle_options": { "max_chars": 20, "gap": 0.3 },
  "synthesis_options": { "mode": "chunked", "chunk_max_chars": 200 }
}
```

**响应：** ZIP 文件，包含：
- `{title}_完整音频.wav`
- `{title}_同步字幕.srt`
- `manifest.json`
- `chunks/001.wav`, `chunks/002.wav`, ...

## 依赖关系

```
tts_provider.py (无依赖)
    ↑
tts_planner.py (依赖 splitter.py)
    ↑
subtitle_timeline.py (无依赖)
    ↑
audio_package.py (无依赖)
    ↑
routes/tts.py (依赖以上所有)
routes/video.py (依赖以上所有)
```

## 测试策略

1. `tts_planner`：字幕段到语音块的合并规则
2. `subtitle_timeline`：一个 chunk 多条字幕时的时间分配
3. `audio_package`：WAV 拼接、gap、参数不一致错误
4. API 测试：`sync-package-v2` 返回完整 WAV、SRT、manifest、chunks

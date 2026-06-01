# 情绪段落化 TTS 技术方案

## 背景

当前项目已经具备一条可用的语音合成链路：

```text
文本内容
-> splitter.split_text()
-> server.services.tts_planner.plan_speech_chunks()
-> server.services.tts_provider.TTSProvider.synthesize()
-> server.services.audio_package.concat_wavs()
-> server.services.subtitle_timeline.build_subtitle_timeline()
-> server.services.audio_package.build_srt()
-> ZIP / 视频生成包
```

近期已经新增 `server.services.voice_prompt`，用于把音色档案转换成更稳定的 TTS prompt，包括：

- 声音身份
- 播讲风格
- 稳定性要求
- 负向约束
- 音色复刻时的参考音频优先规则

但当前系统仍然缺少“情绪段落化”能力。也就是说，它可以稳定使用同一个音色合成多段文本，但还不能明确表达：

```text
第一句平淡、克制。
第二句突然爆发、语速加快、音量提高。
第三句压低声音、冷漠收尾。
```

这份方案目标是基于现有项目结构，设计一套可逐步落地的“文本 -> 情绪段 -> 分段音频 -> 完整音频 + 字幕”的工程方案。

## 目标

1. 支持句子级或段落级情绪控制。
2. 支持“前一句平淡，后一句爆发”的强反差表达。
3. 保持同一个音色档案下的声线一致性。
4. 保持字幕同步能力，不破坏现有 SRT/视频生成流程。
5. 第一版不依赖特定供应商 SSML，优先兼容当前 MiMo TTS 的自然语言提示方式。
6. 后续可扩展到 OpenAI instructions、Azure SSML、Google SSML 等 provider-specific 控制。

## 非目标

1. 第一版不做完整音频编辑工作站。
2. 第一版不做逐字级音高曲线编辑。
3. 第一版不承诺每个 TTS provider 都支持真实 pitch/volume 参数。
4. 第一版不做自动 ASR 校验情绪是否命中。
5. 第一版不引入复杂数据库迁移，优先把情绪计划写入 manifest。

## 当前缺口

### 后端缺口

当前 `SpeechChunk` 只有：

```python
@dataclass
class SpeechChunk:
    index: int
    text: str
    subtitle_indices: list[int]
```

它缺少：

- `emotion`
- `intensity`
- `rate`
- `pitch`
- `volume`
- `pause_before_ms`
- `pause_after_ms`
- `transition`
- `delivery_instruction`

当前 `concat_wavs()` 只支持统一 gap：

```python
concat_wavs(wav_infos, gap=0.3)
```

它不能按每段单独设置停顿，也没有淡入淡出、响度处理、去静音等后处理能力。

当前 `TTSProvider.synthesize()` 支持：

```python
voice_description
text
style_tags
model
voice
optimize_text_preview
```

它没有显式接收情绪参数，也没有 provider adapter 层把通用情绪参数转换成不同 TTS 平台的控制方式。

### 前端缺口

当前语音合成前端主要是：

- 选择文本
- 选择音色档案
- 试听
- 生成同步包

它没有：

- 情绪自动识别开关
- 每段情绪列表
- 单段情绪编辑
- 强度/语速/停顿调节
- 情绪转折预设，如“突然爆发”“压抑后爆发”“转冷漠”

## 推荐架构

新增一层“情绪计划”：

```text
字幕段 subtitle_segments
-> 情绪段 emotion_segments
-> TTS 合成段 speech_chunks
-> 音频后处理 audio_segments
-> 完整音频 + 字幕时间轴
```

建议新增服务：

```text
server/services/emotion_planner.py
server/services/emotional_tts.py
server/services/audio_postprocess.py
```

职责：

| 文件 | 职责 |
| --- | --- |
| `emotion_planner.py` | 从文本或用户配置生成情绪段计划 |
| `emotional_tts.py` | 把情绪段转换成 TTS 请求并逐段合成 |
| `audio_postprocess.py` | 处理按段停顿、淡入淡出、响度归一化、拼接 |
| `voice_prompt.py` | 继续负责音色身份和全局稳定性 prompt |
| `tts_provider.py` | 继续负责单次 provider API 调用 |

## 核心数据结构

### EmotionSegment

建议新增 dataclass：

```python
from dataclasses import dataclass, field


@dataclass
class EmotionSegment:
    index: int
    text: str
    subtitle_indices: list[int] = field(default_factory=list)
    emotion: str = 'neutral'
    intensity: float = 0.5
    rate: float = 1.0
    pitch: float = 0.0
    volume_db: float = 0.0
    pause_before_ms: int = 0
    pause_after_ms: int = 250
    transition: str = 'normal'
    delivery_instruction: str = ''
```

字段说明：

| 字段 | 含义 |
| --- | --- |
| `emotion` | 标准情绪枚举，如 `calm`、`angry`、`sad`、`cold` |
| `intensity` | 情绪强度，建议 0.0 到 2.0 |
| `rate` | 相对语速，1.0 为正常 |
| `pitch` | 相对音高，第一版只进入自然语言提示 |
| `volume_db` | 相对音量，第一版可在后处理阶段应用 |
| `pause_before_ms` | 段前停顿 |
| `pause_after_ms` | 段后停顿 |
| `transition` | `normal`、`burst`、`suppressed_burst`、`cold_shift` |
| `delivery_instruction` | 供应商无结构化控制时使用的自然语言表演指令 |

### 情绪枚举

第一版建议支持：

```python
EMOTION_PRESETS = {
    'neutral': {...},
    'calm': {...},
    'suppressed': {...},
    'angry': {...},
    'angry_burst': {...},
    'sad': {...},
    'fear': {...},
    'cold': {...},
    'excited': {...},
    'whisper': {...},
}
```

推荐参数：

| emotion | intensity | rate | pitch | volume_db | pause_after_ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| `calm` | 0.25 | 0.95 | -1 | -1 | 250 |
| `suppressed` | 0.55 | 0.9 | -1 | -2 | 350 |
| `angry_burst` | 1.6 | 1.15 | 2 | 3 | 180 |
| `sad` | 0.8 | 0.85 | -2 | -1 | 500 |
| `cold` | 0.7 | 0.8 | -2 | -2 | 450 |
| `excited` | 1.2 | 1.12 | 1 | 2 | 180 |

### Manifest 结构

生成包中的 `manifest.json` 建议新增：

```json
{
  "emotional_tts": {
    "enabled": true,
    "mode": "manual",
    "segments": [
      {
        "index": 1,
        "text": "我知道了。",
        "emotion": "calm",
        "intensity": 0.2,
        "rate": 0.95,
        "pitch": -1,
        "volume_db": 0,
        "pause_after_ms": 250,
        "transition": "normal"
      },
      {
        "index": 2,
        "text": "可是你为什么现在才告诉我！",
        "emotion": "angry_burst",
        "intensity": 1.6,
        "rate": 1.15,
        "pitch": 2,
        "volume_db": 3,
        "pause_before_ms": 80,
        "transition": "burst"
      }
    ]
  }
}
```

## 后端流程

### 第一版流程

```text
POST /api/tts/sync-package-v2
  content
  voice_profile_id
  emotional_tts_options
    enabled
    mode
    segments
    auto_detect
      enabled
      provider/model/api_key
  ↓
split_text()
  ↓
plan_emotion_segments()
  ↓
for segment in emotion_segments:
  build_voice_prompt(profile)
  build_segment_delivery_instruction(segment)
  TTSProvider.synthesize(
    voice_description=global_voice_prompt + segment_instruction,
    text=segment.text,
    style_tags=segment_style_tags
  )
  ↓
read_wav_info()
  ↓
postprocess_segment()
  ↓
concat_emotional_wavs()
  ↓
build_subtitle_timeline()
  ↓
build_srt()
  ↓
build_zip_package()
```

### 情绪计划生成

第一版支持三种来源，按优先级：

1. 用户手动编辑的 `emotional_tts_options.segments`
2. 文本内联标记
3. 规则自动识别

#### 文本内联标记

支持：

```text
[calm] 我知道了。
[angry_burst] 可是你为什么现在才告诉我！
```

也可以复用中文括号形式：

```text
（平静）我知道了。
（爆发）可是你为什么现在才告诉我！
```

解析后标记不进入最终字幕文本，除非用户勾选“保留标记”。

#### 规则自动识别

第一版不急着调用 LLM，可以先做规则：

| 文本特征 | 情绪 |
| --- | --- |
| `！`、`？！`、多个感叹号 | `angry_burst` 或 `excited` |
| `……`、省略号、短句 | `suppressed` |
| “为什么”“凭什么”“你怎么敢” | `angry` |
| “我没事”“算了”“不必了” | `suppressed` 或 `cold` |
| “是你逼我的”“我原本不想” | `cold` |

LLM 自动分析可以放到第二阶段。

### 段级提示词

新增函数：

```python
def build_segment_delivery_instruction(segment: EmotionSegment) -> str:
    ...
```

示例输出：

```text
这句话紧接上一句，仍使用同一个说话人音色。
表演方式：情绪突然爆发，语速加快，音量提高，重音更强。
边界：不要破音，不要像换了一个人，不要夸张到卡通化。
```

最终传给自然语言 TTS：

```python
voice_description = "\n".join([
    build_voice_prompt(profile),
    "本段表演：",
    build_segment_delivery_instruction(segment),
])
```

### TTSProvider 扩展

当前 `TTSProvider.synthesize()` 可保持兼容，但建议增加可选参数：

```python
def synthesize(
    self,
    voice_description: str,
    text: str,
    *,
    style_tags: str | None = None,
    model: str = 'mimo-v2.5-tts-voicedesign',
    voice: str | None = None,
    optimize_text_preview: bool = False,
    emotion_options: dict | None = None,
) -> bytes:
```

第一版 `emotion_options` 只用于构造 payload 前的日志/manifest，不直接传给 MiMo。后续不同 provider 可以读取它。

### Provider Adapter

第二阶段建议抽象：

```text
server/services/tts_adapters/
  base.py
  mimo.py
  openai.py
  azure.py
```

接口：

```python
class TTSAdapter:
    def synthesize_segment(self, voice_prompt, segment, voice_profile) -> bytes:
        ...
```

自然语言 provider：

```text
voice_prompt + segment.delivery_instruction
```

SSML provider：

```xml
<mstts:express-as style="angry" styledegree="1.6">
  可是你为什么现在才告诉我！
</mstts:express-as>
```

## 音频后处理

当前 `concat_wavs()` 只插入固定静音。情绪段落化需要更细的处理。

建议新增：

```python
def concat_emotional_wavs(items: list[AudioSegmentInfo]) -> bytes:
    ...
```

其中：

```python
@dataclass
class AudioSegmentInfo:
    wav_info: dict
    emotion_segment: EmotionSegment
```

第一版必须支持：

1. 每段独立 `pause_before_ms`
2. 每段独立 `pause_after_ms`
3. `volume_db` 的简单 PCM 增益
4. 防削波 clipping

第一版可以暂不做：

1. LUFS 响度归一化
2. 去除首尾静音
3. crossfade
4. 呼吸音合成

第二阶段再做：

| 功能 | 建议 |
| --- | --- |
| 普通衔接 | 30-50ms crossfade |
| 爆发型 | 100-250ms 停顿，弱 crossfade |
| 悲伤/哽咽 | 300-600ms 停顿 |
| 快速对话 | 80-150ms 停顿 |

## 字幕同步

当前 `build_subtitle_timeline(chunks, chunk_durations, gap, subtitle_segments)` 假设 gap 固定。

情绪段落化后需要新增：

```python
build_emotional_subtitle_timeline(
    emotion_segments,
    segment_durations,
)
```

时间轴计算：

```text
current_time += pause_before_ms
start = current_time
end = start + audio_duration
current_time = end + pause_after_ms
```

如果一个 emotion segment 对应多个字幕段，继续按当前 `subtitle_indices` 拆分到字幕层。

## API 设计

### sync-package-v2 扩展

请求：

```json
{
  "api_key": "xxx",
  "title": "情绪测试",
  "content": "我知道了。可是你为什么现在才告诉我！",
  "voice_profile_id": 9,
  "subtitle_options": {
    "max_chars": 20,
    "gap": 0.3
  },
  "synthesis_options": {
    "mode": "chunked",
    "chunk_max_chars": 200
  },
  "emotional_tts_options": {
    "enabled": true,
    "mode": "manual",
    "segments": [
      {
        "text": "我知道了。",
        "emotion": "calm",
        "intensity": 0.2,
        "rate": 0.95,
        "pitch": -1,
        "volume_db": 0,
        "pause_after_ms": 250
      },
      {
        "text": "可是你为什么现在才告诉我！",
        "emotion": "angry_burst",
        "intensity": 1.6,
        "rate": 1.15,
        "pitch": 2,
        "volume_db": 3,
        "pause_before_ms": 80
      }
    ]
  }
}
```

响应：仍然返回 ZIP，不改变现有下载逻辑。

### 预览接口

建议新增：

```text
POST /api/tts/emotion-plan
```

用途：前端在生成前预览情绪段。

请求：

```json
{
  "content": "我知道了。可是你为什么现在才告诉我！",
  "mode": "rule"
}
```

响应：

```json
{
  "segments": [
    {
      "index": 1,
      "text": "我知道了。",
      "emotion": "calm",
      "intensity": 0.2,
      "rate": 0.95,
      "pitch": -1,
      "volume_db": 0,
      "pause_after_ms": 250
    },
    {
      "index": 2,
      "text": "可是你为什么现在才告诉我！",
      "emotion": "angry_burst",
      "intensity": 1.6,
      "rate": 1.15,
      "pitch": 2,
      "volume_db": 3,
      "pause_before_ms": 80
    }
  ]
}
```

## 前端设计

### 简单模式

在 `VoiceSynthModal.vue` 的音色步骤或生成步骤增加：

```text
[x] 自动识别情绪

整体风格：
[平静] [热血] [悬疑] [冷漠] [悲伤]
```

用户不需要逐段编辑。

### 高级模式

新增“情绪段落”步骤或折叠区：

```text
情绪段落
------------------------------------------------
1. 我知道了。
   情绪: 平静
   强度: 20%
   语速: 95%
   音量: 0dB
   段后停顿: 250ms

2. 可是你为什么现在才告诉我！
   情绪: 爆发愤怒
   强度: 160%
   语速: 115%
   音量: +3dB
   段前停顿: 80ms
```

控件建议：

| 参数 | 控件 |
| --- | --- |
| emotion | Select |
| intensity | Slider |
| rate | Slider |
| volume_db | Slider |
| pause_before_ms | InputNumber |
| pause_after_ms | InputNumber |
| transition | Segmented |

### 前端状态

建议新增：

```js
const emotionalTts = ref({
  enabled: false,
  mode: 'rule',
  segments: [],
})
```

提交到后端：

```js
ttsApi.syncPackageV2({
  ...
  emotional_tts_options: emotionalTts.value.enabled ? emotionalTts.value : undefined,
})
```

## 视频生成联动

`VideoGenerateModal.vue` 当前已经传：

```js
speaker_profiles
voice_description
subtitle_options
```

后续可以追加：

```js
emotional_tts_options
```

`server/services/video_job.py` 在合成旁白时复用同一套 `emotion_planner + emotional_tts`。

视频生成收益很明显：

- 字幕时间轴天然跟情绪段对齐
- 爆发段可以配合画面 shake/flash
- 冷漠段可以配合慢推镜头
- 后续可以让 `video_scene_planner` 读取 emotion segments

## 数据库策略

第一版不新增表。

原因：

- 当前同步包是一次性生成任务。
- 情绪参数可存在 `manifest.json`。
- 文本库 `Text.source_context_json` 已能承载来源上下文。

第二阶段如要保存用户反复编辑的配音工程，再考虑新增：

```text
voice_projects
voice_project_segments
```

字段示例：

```sql
CREATE TABLE voice_project_segments (
  id INTEGER PRIMARY KEY,
  project_id INTEGER NOT NULL,
  segment_index INTEGER NOT NULL,
  text TEXT NOT NULL,
  emotion VARCHAR(50),
  intensity FLOAT,
  rate FLOAT,
  pitch FLOAT,
  volume_db FLOAT,
  pause_before_ms INTEGER,
  pause_after_ms INTEGER,
  created_at DATETIME,
  updated_at DATETIME
);
```

## 实施阶段

### Phase 1：手动情绪段落

目标：用户可以手动设置每段情绪并生成同步包。

后端：

- 新增 `EmotionSegment`
- 新增 `emotion_planner.py`
- 新增 `build_segment_delivery_instruction()`
- 新增 `concat_emotional_wavs()`
- 扩展 `/api/tts/sync-package-v2`
- manifest 记录 emotional_tts

前端：

- 增加“启用情绪段落化”开关
- 文本切分后展示 emotion segments
- 每段可选择 emotion / intensity / rate / pause
- 提交 `emotional_tts_options`

### Phase 2：规则自动识别

目标：用户不手工编辑，也能得到基础情绪段。

后端：

- `plan_emotion_segments(content, mode='rule')`
- 支持标点、关键词、内联标记
- 新增 `/api/tts/emotion-plan`

前端：

- “自动识别情绪”按钮
- 用户可在自动结果上微调

### Phase 3：音频后处理增强

目标：减少分段拼接感。

后端：

- PCM 增益
- 防削波
- 每段首尾短 fade
- 可选 crossfade
- 可选静音裁剪

### Phase 4：Provider-specific 控制

目标：针对不同 TTS 平台做更强控制。

后端：

- TTS adapter 抽象
- MiMo：自然语言 prompt + style_tags
- OpenAI：instructions
- Azure：SSML express-as / styledegree
- Google：SSML prosody

## 测试计划

### 单元测试

新增：

```text
server/tests/test_emotion_planner.py
server/tests/test_emotional_tts.py
server/tests/test_audio_postprocess.py
```

覆盖：

1. 标点规则识别：
   - `我知道了。可是你为什么现在才告诉我！`
   - 第一段 calm，第二段 angry_burst
2. 内联标签解析：
   - `[calm] 我知道了。`
   - `[angry_burst] 可是你为什么现在才告诉我！`
3. 手动 segments 校验：
   - 缺 text 报错
   - intensity 超范围被 clamp
   - pause 小于 0 被拒绝或 clamp
4. 音频拼接：
   - 每段独立 pause_before/pause_after
   - volume_db 改变 PCM 振幅
   - 防削波生效
5. manifest：
   - emotional_tts 被写入 ZIP

### 路由测试

扩展：

```text
server/tests/test_sync_package_v2.py
```

覆盖：

- 不传 `emotional_tts_options` 时保持旧行为。
- 传入 `emotional_tts_options.enabled=true` 时使用情绪段。
- 生成 ZIP 中包含完整音频、SRT、manifest、分段 WAV。

### 前端验证

最小验证：

- 打开语音合成弹窗。
- 启用情绪段落化。
- 自动生成情绪段列表。
- 修改第二段为“爆发愤怒”。
- 点击试听或生成。
- 确认请求包含 `emotional_tts_options`。

## 风险与边界

1. 自然语言 TTS 对 pitch/rate/volume 不一定严格执行。
2. 多段生成可能导致声线漂移，必须在 prompt 中反复强调同一说话人。
3. 过强的 `volume_db` 可能导致削波，需要后处理限制。
4. 爆发段不应强求无缝，短停顿往往比 crossfade 更自然。
5. 自动情绪识别容易误判，第一版必须允许用户手动覆盖。

## 推荐结论

当前项目非常适合做情绪段落化，因为已经有字幕切分、语音块、WAV 拼接和 SRT 时间轴。

推荐第一版优先实现：

```text
手动情绪段落
-> 段级自然语言提示词
-> 每段独立停顿
-> manifest 记录
-> 前端简单/高级模式
```

暂不优先做复杂 SSML adapter 和 LUFS 响度归一化。先把“前一句平淡，后一句突然爆发”稳定跑通，再扩展 provider-specific 控制。

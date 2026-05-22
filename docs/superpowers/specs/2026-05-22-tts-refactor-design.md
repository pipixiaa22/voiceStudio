# 语音合成重构技术方案

## 背景

当前项目是一个面向视频剪辑的字幕工坊：用户导入或粘贴中文文本，系统通过 `splitter.py` 按标点和长度生成短字幕，再通过 `srt.py` 生成 SRT。现有语音合成集中在 `server/routes/tts.py` 和 `web/src/components/VoiceSynthModal.vue`，已经支持单段合成、批量 ZIP、同步包，以及视频生成时的逐字幕段 TTS。

现有实现的主要问题是“字幕分段”和“语音合成分段”使用了同一套粒度。字幕需要短、稳定、便于阅读；语音合成需要更长的上下文、连贯的语气和一致的音色。若按 20 字左右的字幕段逐段调用 TTS，容易出现音色、情绪、语速和停顿割裂。

## 目标

1. 在保留现有字幕导出能力的基础上，新增更稳定的语音合成工作流。
2. 降低多段合成时的音色漂移，让整篇内容听起来像同一个人连续朗读。
3. 提高用户描述音色后的命中率，让用户能在批量生成前确认声音方向。
4. 同时满足视频生成、剪辑导入、失败重试、局部重生等使用场景。

## 非目标

1. 不把字幕分段逻辑改成只服务 TTS。字幕仍然保持短字幕优先。
2. 不在第一阶段强依赖复杂的强制对齐模型。若后续需要逐字级精准卡点，再增加独立对齐服务。
3. 不把业务逻辑继续堆在 Flask route 内。重构后 route 只负责参数校验和响应封装。

## 核心设计

重构后要把文本拆成三种不同粒度：

| 粒度 | 用途 | 示例 |
|------|------|------|
| 原文 Text | 用户保存和编辑的完整文本 | 一篇文案 |
| 字幕段 SubtitleSegment | 屏幕显示和 SRT 输出 | 10-20 字左右 |
| 语音块 SpeechChunk | TTS 实际调用单位 | 一句、几句或一个短段落 |

推荐架构是“语音块合成，字幕段对齐”。也就是说，字幕仍按现有 `split_text(content, max_chars=20)` 生成，但 TTS 不再默认逐字幕段调用，而是把相邻字幕段合并成更自然的 `SpeechChunk` 后合成。每个语音块生成一个 WAV，系统再拼成完整音频，并根据语音块时长推导字幕时间轴。

## 方案对比

### 方案 A：继续逐字幕段合成

每个字幕段单独调用 TTS，然后拼接 WAV。

优点：
- 实现最简单，当前项目已经接近这个形态。
- 每段失败可单独重试。
- 字幕时间轴天然准确。

缺点：
- 最容易产生音色割裂。
- 每段上下文过短，模型会重新解释角色、情绪和节奏。
- 调用次数多，速度慢，失败概率和成本更高。

结论：只保留为“精确字幕段模式”或调试模式，不作为默认方案。

### 方案 B：整篇文本一次合成

把全文一次性提交给 TTS。

优点：
- 音色和语气最连贯。
- 调用次数最少。
- 适合短文案和纯音频导出。

缺点：
- 受接口长度、超时和失败重试影响大。
- 局部修改后通常要整篇重生。
- 很难直接得到每条字幕的精确时间。

结论：适合作为“短文优先策略”。当文本较短且接口允许时，可以一键整篇合成。

### 方案 C：按语义语音块合成

先生成字幕段，再把连续字幕段按句子、段落、长度上限合并成语音块。每个语音块一次 TTS，最后拼成完整音频。

优点：
- 比逐字幕段更连贯，比整篇合成更可控。
- 局部失败只需重试一个语音块。
- 可以保留分段 WAV、完整 WAV、SRT、manifest。
- 更适合当前项目的同步包和视频生成流程。

缺点：
- 需要新增语音块规划和字幕时间分配逻辑。
- 若不用对齐模型，语音块内部的字幕时间只能先做估算。

结论：推荐作为默认方案。

## 音色一致性策略

### 1. 建立 VoiceProfile，而不是直接使用自由文本

当前前端有“默认音色描述”和“润色”功能，但最终传给 TTS 的仍是一段自然语言。建议新增 `VoiceProfile` 概念，把用户输入规范化为结构化数据和一段锁定后的 canonical prompt。

建议字段：

```json
{
  "id": "voice-profile-id",
  "name": "温柔叙述女声",
  "raw_description": "年轻女性，温柔甜美，治愈感",
  "canonical_prompt": "一位年轻女性中文叙述者，音色清澈柔和，语速中慢，情绪温暖克制...",
  "attributes": {
    "gender": "female",
    "age": "young_adult",
    "timbre": "soft_clear",
    "speed": "medium_slow",
    "emotion": "warm_calm",
    "accent": "standard_mandarin"
  },
  "negative_prompt": "不要夸张表演，不要儿童音，不要明显播音腔",
  "version": 1
}
```

后续所有语音块都使用同一个 `canonical_prompt`，避免每段使用不同措辞导致模型重新采样。

### 2. 区分“音色锁定”和“语气指令”

音色相关信息应稳定不变，包括性别、年龄、音色质感、语速范围、口音、角色身份。每个语音块只允许添加轻量的语气指令，例如“这里语气稍微坚定”或“这里保持平静”。不要在片段级重新写“年轻女性、温柔、甜美”等音色描述。

推荐请求结构：

```json
{
  "voice_profile_id": 3,
  "voice_prompt": "<canonical_prompt>",
  "delivery_note": "保持自然叙述，句尾不要过度上扬",
  "text": "本语音块文本"
}
```

当前 MiMo 调用可以继续用 `messages` 形式封装，但内部服务层要保证 `voice_prompt` 在同一个任务中完全一致。

### 3. 优先合并自然语义边界

合成单位不要按字幕段切，而应按以下规则规划：

1. 优先按原文段落分组。
2. 段落过长时按句号、问号、叹号、省略号拆成句组。
3. 句组过长时再按逗号、分号切分。
4. 每个语音块控制在接口稳定范围内，例如 80-300 中文字符。
5. 不跨越角色、旁白、明显情绪变化或用户手动插入的分隔符。

### 4. 同一任务内固定采样条件

如果 TTS 接口支持 seed、voice id、speaker id、temperature、style strength 等参数，应在 `TTSJob` 层固定并写入 manifest。当前代码未暴露这些参数，因此第一阶段至少要固定：

- `canonical_prompt`
- 文本预处理规则
- 语音块规划规则
- gap
- TTS model 名称
- provider 名称

这样即使接口本身有随机性，也能减少业务侧引入的漂移。

## 更准确命中用户想要的音色

### 1. 从“填写描述”升级为“创建音色档案”

前端不应只给一个大文本框。建议提供两层输入：

基础表单：
- 性别/年龄感
- 普通话/口音
- 语速
- 情绪
- 音色质感
- 场景：短视频解说、故事朗读、课程讲解、广告旁白等

自由描述：
- 用户用自然语言补充“像什么、不像什么”

系统把两部分合并后调用现有 `/api/tts/polish` 或新的 `/api/tts/voice-profile/normalize`，生成结构化 `VoiceProfile`。

### 2. 批量生成前必须有试听确认

新增“试听校准”流程：

1. 用户输入音色意图。
2. 系统用固定试听文案生成 2-3 个候选声音。
3. 用户选择最接近的一版。
4. 系统保存该版的 `canonical_prompt`、候选编号和参数 hash。
5. 批量生成时使用被确认的音色档案。

固定试听文案建议同时覆盖陈述、转折、疑问和情绪变化，例如：

```text
今天我们来聊一个很实用的方法。它听起来简单，但真正做好并不容易。你可能会问，第一步应该从哪里开始？
```

试听文案固定的好处是：用户比较的是音色，而不是被不同文本内容干扰。

### 3. 支持负向约束

很多用户更容易说清楚“不想要什么”。音色档案应包含 `negative_prompt`：

- 不要儿童音
- 不要明显播音腔
- 不要情绪太夸张
- 不要机械感
- 不要太快

生成 canonical prompt 时把负向约束一起固化。

### 4. 保留用户选择历史

建议新增音色预设列表：

- 最近使用
- 已收藏
- 项目内音色
- 全局默认音色

同一类视频长期使用同一 `VoiceProfile`，比每次重新描述更容易保持品牌一致性。

## 音频文件：单段还是多段

推荐结论：内部多段，交付双形态。

### 内部多段

系统内部按 `SpeechChunk` 生成多个 WAV：

- 便于失败重试。
- 便于局部重新生成。
- 便于后续用户调整某一段语气。
- 便于调试音色漂移发生在哪个语音块。

### 交付单段

对大多数视频工作流，应提供完整音频：

- `title_完整音频.wav`
- `title_同步字幕.srt`
- `manifest.json`

视频生成也应优先使用完整音频，避免剪辑软件导入多段素材后手动对齐。

### 同时保留分段素材

同步包继续保留分段音频，但分段从“字幕段”调整为“语音块”：

```text
title_完整音频.wav
title_同步字幕.srt
manifest.json
chunks/001.wav
chunks/002.wav
chunks/003.wav
```

如果用户需要更细粒度素材，可以额外导出 `subtitle_segments` 清单，但不建议默认生成每条字幕的独立音频。

## 时间轴生成

TTS 音频生成后，系统可以准确读取每个语音块的真实时长。难点在于一个语音块内可能包含多条字幕。

第一阶段建议使用“加权估算”：

1. 语音块有真实开始时间和结束时间。
2. 语音块内部的字幕段按文本长度分配时长。
3. 问号、叹号、省略号、句号后的字幕段增加少量停顿权重。
4. 每条字幕设置最小时长，例如 0.8 秒。
5. 最后一条字幕强制对齐语音块结束时间，避免累计误差。

第二阶段可增加“自动对齐”：

- 使用 ASR 识别完整音频，得到字/词级时间戳。
- 将识别文本和原字幕段做文本匹配。
- 回填更精确的字幕时间。

第一阶段适合快速落地；第二阶段适合追求剪映内更精准卡点的场景。

## 后端重构建议

当前 `server/routes/tts.py` 同时承担 API 请求、TTS 调用、音频解析、拼接、SRT 生成和 ZIP 打包。建议拆成服务层：

```text
server/routes/tts.py
server/services/tts_provider.py
server/services/voice_profile.py
server/services/tts_planner.py
server/services/audio_package.py
server/services/subtitle_timeline.py
```

职责划分：

| 文件 | 职责 |
|------|------|
| `tts_provider.py` | 封装 MiMo TTS/LLM 请求，后续可替换供应商 |
| `voice_profile.py` | 音色描述规范化、canonical prompt、负向约束 |
| `tts_planner.py` | 从原文、字幕段生成 SpeechChunk |
| `audio_package.py` | WAV 读取、拼接、静音 gap、ZIP 打包 |
| `subtitle_timeline.py` | 根据 chunk 时长生成字幕时间轴 |
| `routes/tts.py` | 参数校验、调用服务、返回 JSON/文件 |

视频生成 `server/routes/video.py` 也应复用同一个 TTS 编排服务，避免视频功能继续逐字幕段合成。

## API 设计

### 创建/规范化音色档案

```http
POST /api/tts/voice-profile/normalize
```

请求：

```json
{
  "api_key": "llm-key",
  "raw_description": "年轻女性，温柔甜美，治愈感",
  "negative_prompt": "不要儿童音，不要播音腔",
  "attributes": {
    "gender": "female",
    "speed": "medium_slow",
    "scene": "short_video_narration"
  }
}
```

响应：

```json
{
  "voice_profile": {
    "canonical_prompt": "...",
    "attributes": {},
    "negative_prompt": "...",
    "version": 1
  }
}
```

### 试听候选

```http
POST /api/tts/voice-profile/audition
```

返回 2-3 个试听音频 base64 或 ZIP。第一阶段也可以只返回一个候选，先完成“批量前试听确认”的产品闭环。

### 生成同步包

```http
POST /api/tts/sync-package-v2
```

请求：

```json
{
  "api_key": "tts-key",
  "title": "作品标题",
  "content": "完整文本",
  "subtitle_options": {
    "max_chars": 20,
    "gap": 0.3
  },
  "voice_profile": {
    "canonical_prompt": "...",
    "negative_prompt": "..."
  },
  "synthesis_options": {
    "mode": "chunked",
    "chunk_min_chars": 80,
    "chunk_max_chars": 300,
    "export_chunks": true
  }
}
```

响应：ZIP 文件。

ZIP 内建议：

```text
作品标题_完整音频.wav
作品标题_同步字幕.srt
manifest.json
chunks/001.wav
chunks/002.wav
```

### manifest 结构

```json
{
  "title": "作品标题",
  "provider": "mimo",
  "model": "mimo-v2.5-tts-voicedesign",
  "voice_profile": {
    "canonical_prompt_hash": "sha256...",
    "version": 1
  },
  "subtitle_options": {
    "max_chars": 20,
    "gap": 0.3
  },
  "chunks": [
    {
      "index": 1,
      "filename": "chunks/001.wav",
      "text": "语音块文本",
      "start": 0.0,
      "end": 12.4,
      "duration": 12.4,
      "subtitle_indices": [1, 2, 3, 4]
    }
  ],
  "subtitles": [
    {
      "index": 1,
      "text": "字幕文本",
      "start": 0.0,
      "end": 2.1,
      "chunk_index": 1
    }
  ]
}
```

## 前端交互建议

`VoiceSynthModal.vue` 建议从“分段列表 + 每段音色输入”改为四步：

1. 选择文本：选择已有文本或手动粘贴。
2. 音色档案：填写/选择预设，生成 canonical prompt。
3. 试听确认：用固定试听文案生成样音，用户确认后锁定。
4. 生成：选择整篇、智能分块、逐字幕段三种模式，默认智能分块。

片段列表仍然可以保留，但应显示两层信息：

- 字幕段：用于预览字幕。
- 语音块：用于显示实际 TTS 调用单位和重试状态。

## 数据持久化建议

第一阶段可以不新增数据库表，只把 voice profile 放在请求 payload 和 manifest 中。

第二阶段建议新增表：

```text
voice_profiles
- id
- name
- raw_description
- canonical_prompt
- attributes_json
- negative_prompt
- provider
- model
- created_at
- updated_at

tts_jobs
- id
- text_id
- voice_profile_id
- status
- options_json
- manifest_json
- created_at
- updated_at
```

如果暂时不做服务端持久化，前端至少应把常用音色档案保存到 localStorage，延续当前 API Key 设置的轻量存储方式。

## 错误处理

需要区分以下错误：

| 类型 | 处理 |
|------|------|
| 音色规范化失败 | 允许用户直接使用原始描述继续 |
| 试听失败 | 显示供应商错误，允许重试 |
| 单个 chunk 合成失败 | 保留已成功 chunk，支持从失败 chunk 继续 |
| 音频参数不一致 | 尝试重采样或提示无法拼接 |
| ZIP 打包失败 | 返回明确错误，不吞掉部分失败 |
| 视频生成失败 | 保留 TTS 同步包生成能力，便于用户独立下载 |

## 测试策略

后端测试：

1. `tts_planner`：字幕段到语音块的合并规则。
2. `subtitle_timeline`：一个 chunk 多条字幕时的时间分配。
3. `audio_package`：WAV 拼接、gap、参数不一致错误。
4. `voice_profile`：规范化输出字段完整，保留用户核心意图。
5. API 测试：`sync-package-v2` 返回完整 WAV、SRT、manifest、chunks。

前端测试：

1. 选择文本后能同时预览字幕段和语音块。
2. 音色试听确认前，批量生成按钮不可用或给出明确提示。
3. 智能分块、整篇、逐字幕段三种模式的 payload 正确。
4. 失败 chunk 可重试，不清空已生成结果。

## 分阶段落地

### Phase 1：服务层重构和智能分块

- 提取 TTS provider、音频、时间轴服务。
- 新增 SpeechChunk 规划。
- 新增 `sync-package-v2`。
- 保留旧 API，避免现有前端功能立即断裂。
- 视频生成改为复用新服务。

### Phase 2：音色档案和试听确认

- 新增 VoiceProfile 规范化。
- 前端新增音色档案编辑和试听确认。
- 批量生成使用锁定后的 canonical prompt。
- manifest 写入音色档案 hash。

### Phase 3：更精准对齐和持久化

- 引入 ASR/强制对齐服务。
- 新增数据库表保存 voice profiles 和 tts jobs。
- 支持历史任务恢复、局部重生、音色预设管理。

## 推荐决策

默认模式采用“智能分块合成”：

- 字幕段继续使用当前短字幕逻辑。
- TTS 按语义语音块调用，减少割裂感。
- 内部保留多段 chunk WAV。
- 对外导出完整 WAV + SRT + manifest + chunks。
- 批量生成前先让用户试听并确认音色档案。

这套方案兼顾了音色统一、用户可控、失败重试和视频剪辑交付。它也最贴合当前项目：现有的同步包、视频生成、SRT 导出都能平滑迁移到同一个 TTS 编排服务上。

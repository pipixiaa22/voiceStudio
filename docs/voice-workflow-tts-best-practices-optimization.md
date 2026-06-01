# 配音工作台语音生成最佳实践优化方案

## 结论

当前配音工作台已经具备“音色档案 + 单句情绪 + 分段试听/导出”的基础能力，但还没有完整达到专业配音生成的最佳实践。主要原因不是字段缺失，而是控制层级尚未拆清：人物人设、稳定声线、当前情绪、上下文转折、供应商能力映射和音频验收仍然混在一段自然语言提示词里。

建议采用“分层控制 + provider adapter + 可试听验收”的方案，把语音生成拆成以下六层：

1. 声音身份：声线、性别、年龄感、口音、音色质感、语言。
2. 人物人设：角色身份、性格、人物关系、说话习惯、禁用表演方式。
3. 场景上下文：当前剧情阶段、说话对象、情绪原因、上一句到下一句的转折。
4. 当前表演状态：情绪、强度、语速、音高、音量、停顿、转场、补充表演指令。
5. 供应商映射：MiMo 使用 voice design prompt；OpenAI 使用 `instructions`、`speed`、`voice` 等结构化参数。
6. 试听验收：缓存指纹、重试、AB 试听、导出前校验、manifest 记录生成参数。

## 现状评估

### 已经符合最佳实践的部分

- 音色档案已经能沉淀声音身份：`canonical_prompt`、`raw_description`、`gender`、`age_group`、`accent`、`speed`、`emotion`、`scene`、`timbre`、`style_tags`、`negative_prompt`。
- `build_voice_prompt()` 会把音色身份、播讲风格、稳定性要求和负向约束组合为稳定提示词。
- 配音工作台支持工程默认音色和单句覆盖音色。
- 单句支持 `emotion`、`intensity`、`rate`、`pitch`、`volume_db`、`pause_before_ms`、`pause_after_ms`、`transition`、`delivery_instruction`。
- 合成前会把全局音色提示和“本段表演”合并，强调同一说话人音色，降低逐句合成时的声线漂移。
- 音量和停顿已进入后处理，导出包里也能保留分段音频、SRT 和 manifest。

### 当前主要缺口

1. 人物人设不够结构化。

   现在“人物是谁、和听众/对手是什么关系、说话习惯是什么”主要靠 `raw_description` 自由文本承载。自由文本灵活，但难以批量复用、难以对齐 UI，也难以做自动检查。

2. 当前情绪没有完整上下文。

   `emotion` 只表达“这一句像什么情绪”，没有表达“为什么有这个情绪”“对谁说”“上一句如何转到这一句”。强戏剧文本里，这会导致表演像逐句贴标签，而不是连续表演。

3. `intensity` 和 `pitch` 没有充分进入提示词或 provider 参数。

   目前它们会进入存储和缓存指纹，但 `build_segment_delivery_instruction()` 主要使用 `emotion`、`rate`、`volume_db`、`transition`，没有显式解释 `intensity` 和 `pitch`。

4. provider 能力没有统一适配层。

   配音工作台实际合成走 `TTSProvider` 的 MiMo 请求。OpenAI provider 虽然存在，但当前只传 `input` 和 `voice`，没有使用 `instructions`、`speed`，也仍默认列出较旧的 `tts-1`。

5. 自动情绪识别偏规则化。

   当前靠标点和关键词识别，如感叹号、省略号、“为什么”“算了”等。它适合初稿，不适合判断隐忍、反讽、压低怒意、人物关系变化等复杂表演。

6. 缺少导出前质量门禁。

   现在可以试听和导出，但缺少“所有段落是否有音色、是否存在未保存更改、缓存是否匹配、音频参数是否一致、是否使用最新表演指令”的统一检查。

## 参考原则

### MiMo 语音设计

项目内 `video.md` 已记录 MiMo voice design prompt 的关键维度：性别与年龄、音色/质感、情绪/语气、语速/节奏、角色/人设、说话风格、场景描写、年代参照。它也强调提示词应具体、生动，避免冲突、避免模糊词，合成文本要贴合音色。

配音工作台应把这些维度从“用户自己写一段话”升级为“结构化字段 + 自动拼接提示词 + 允许高级用户补充自由文本”。

### OpenAI TTS

OpenAI 当前 Text to Speech 指南建议使用 `gpt-4o-mini-tts`，并说明可以通过提示控制口音、情绪范围、语调、风格、语速、语气、耳语等表达；`speech` API 也支持 `instructions` 和 `speed`，其中 `instructions` 不适用于 `tts-1` / `tts-1-hd`。

参考：

- [OpenAI Text to speech guide](https://platform.openai.com/docs/guides/text-to-speech?lang=javascript)
- [OpenAI Audio API reference](https://platform.openai.com/docs/api-reference/audio?api-mode=chat)
- [gpt-4o-mini-tts model page](https://platform.openai.com/docs/models/gpt-4o-mini-tts)

因此，OpenAI provider 的最佳实践不是把所有控制塞进 `input`，而是：

- `input` 只放要朗读的文本。
- `instructions` 放声音身份、人物人设、当前表演状态和边界约束。
- `speed` 映射相对语速。
- `voice` 使用内置音色或自定义 voice id。
- `response_format` 在工作台中优先使用 `wav`，便于后处理和拼接。

## 目标架构

### 1. Canonical TTS Segment Request

新增一个供应商无关的段落请求对象，作为工作台到 TTS 的唯一内部协议。

```python
@dataclass
class TTSSegmentRequest:
    text: str
    voice_identity: dict
    persona: dict
    scene_context: dict
    performance: dict
    provider: str
    model: str
    voice: str | dict | None = None
    output_format: str = 'wav'
```

推荐字段：

```json
{
  "voice_identity": {
    "language": "zh-CN",
    "gender": "male",
    "age_group": "30-40",
    "accent": "标准普通话",
    "timbre": "低沉、有厚度、克制"
  },
  "persona": {
    "role_name": "玄霜峰师尊",
    "archetype": "冷面师尊",
    "personality": "克制、威严、很少直接表达关心",
    "speaking_habit": "短句多，语气压低，不拖腔",
    "relationship_to_listener": "对方是刚入门的弟子",
    "negative_prompt": "不要播音腔，不要综艺感，不要卡通化"
  },
  "scene_context": {
    "scene": "修仙短剧",
    "beat": "训诫弟子但隐藏保护意图",
    "previous_emotion": "calm",
    "current_emotion_cause": "弟子触犯禁令",
    "next_transition": "压抑后转冷"
  },
  "performance": {
    "emotion": "cold",
    "intensity": 0.75,
    "rate": 0.9,
    "pitch": -2,
    "volume_db": -2,
    "pause_before_ms": 120,
    "pause_after_ms": 450,
    "transition": "cold_shift",
    "delivery_instruction": "像在压住怒意，不要吼"
  }
}
```

### 2. Provider Adapter

新增 `server/services/tts_adapters/`，把 canonical request 映射到不同 TTS 平台。

```text
server/services/tts_adapters/
  base.py
  mimo.py
  openai.py
```

职责：

- `base.py`：定义统一接口、返回结构和错误类型。
- `mimo.py`：把身份、人设、场景、表演拼成 voice design prompt，正文放 assistant content。
- `openai.py`：把身份、人设、场景、表演拼成 `instructions`，正文放 `input`，语速映射到 `speed`。

这样可以避免工作台写死某一个供应商，也能让 `rate`、`pitch`、`intensity` 是否真实生效变得可追踪。

### 3. Prompt Builder 分层

把当前 `build_voice_prompt()` 拆成更明确的三个 builder：

```text
build_voice_identity_prompt(profile)
build_persona_prompt(profile, workflow)
build_segment_performance_prompt(segment, context)
```

最终组合：

```text
声音身份：
- ...

人物人设：
- ...

当前场景：
- ...

本段表演：
- ...

边界约束：
- ...
```

这样能避免“音色身份”和“当前情绪”互相污染。例如一个“清冷女声”可以在某句“愤怒但不破音”，而不是被重新生成成另一个“愤怒角色”。

## 分阶段优化计划

### Phase 1：补齐提示词和参数映射

目标：不大改 UI，不改数据库结构，先提升生成质量。

改动：

- 在 `build_segment_delivery_instruction()` 中显式使用 `intensity` 和 `pitch`。
- 把 `rate`、`pitch`、`volume_db` 映射为更细的表演语言，而不是只有“快/慢、高/低”。
- 增加 `transition` 枚举：`normal`、`burst`、`suppressed_burst`、`cold_shift`、`soften`、`whisper_in`。
- 在 manifest 中记录最终传给 TTS 的 `voice_description` 摘要和 provider 参数摘要，便于复盘。
- 为提示词生成补测试，确保强度、音高、转场和用户补充指令都进入输出。

验收标准：

- 同一个段落改 `intensity` 后，生成提示词内容可见变化。
- 改 `pitch` 后，提示词明确出现压低/抬高声线的表演要求。
- 导出 manifest 能看到每段的核心生成参数。

### Phase 2：引入人物人设字段

目标：让“人物是谁”不再只靠一段自由文本。

建议新增字段：

- `role_name`：角色名或身份，如“冷面师尊”“深夜电台主播”。
- `archetype`：角色类型，如“反派谋士”“温柔老师”“热血解说”。
- `personality`：性格关键词。
- `speaking_habit`：说话习惯，如“短句、少起伏、尾音收紧”。
- `relationship_to_listener`：说话对象关系。
- `persona_prompt`：高级自由补充。

UI：

- `VoiceProfileDrawer` 新增“人物人设”区块。
- `SegmentInspector` 保持简洁，只显示当前段的“本句音色”和“表演指令”。
- 工作台工具栏可选择工程默认人设/音色。

后端：

- `voice_profiles` 表新增可选字段，或先放入 `metadata_json` 以减少迁移频率。
- `build_voice_prompt()` 兼容旧档案；旧档案没有人设字段时行为不变。

验收标准：

- 新建音色档案时可以结构化填写人设。
- 生成提示词中能清楚区分“声音身份”和“人物人设”。
- 旧音色档案无需迁移也能继续生成。

### Phase 3：建立 TTS adapter 层

目标：让 MiMo、OpenAI 和未来供应商使用统一工作台参数，但各自按最佳方式调用。

MiMo adapter：

- `messages[0].content` 使用 voice design prompt。
- `messages[1].content` 只放朗读文本，必要时可在文本前添加供应商支持的风格标签。
- voice clone 时优先使用样音，文字提示只补表演方式。

OpenAI adapter：

- 默认模型改为 `gpt-4o-mini-tts`。
- `input` 只放朗读文本。
- `instructions` 放声音身份、人设、当前表演和边界约束。
- `speed` 使用 `rate`，并限制在 API 支持范围。
- `response_format` 使用 `wav`。
- 只有支持 `instructions` 的模型才发送 `instructions`。

验收标准：

- 同一段 canonical request 可以分别生成 MiMo payload 和 OpenAI payload。
- OpenAI payload 中不把表演指令混入 `input`。
- `tts-1` / `tts-1-hd` 不发送 `instructions`，并在 UI 上提示控制能力受限。

### Phase 4：上下文感知的情绪规划

目标：从“逐句情绪标签”升级为“连续表演规划”。

输入：

- 源文本。
- 工程默认人物人设。
- 可选剧情类型，如短视频旁白、修仙短剧、课程讲解、新闻资讯。

输出：

- 每句情绪。
- 情绪原因。
- 与上一句的转场。
- 强度曲线。
- 建议停顿。
- 需要用户确认的高风险段落。

实现顺序：

1. 保留当前规则识别作为快速本地模式。
2. 支持文本内联标记，如 `[cold]`、`（压低声音）`。
3. 增加可选 LLM 分析模式，返回结构化 JSON。
4. UI 提供“应用到全部”前的预览表格，用户可逐句修改。

验收标准：

- 自动规划能识别“压抑 -> 爆发 -> 冷漠收尾”的情绪弧。
- 用户手动改过的段落不会被重新规划覆盖，除非明确选择覆盖。
- LLM 输出非法 JSON 时回退到规则模式并给出提示。

### Phase 5：试听与质量验收

目标：让用户知道一条配音是否可交付。

新增能力：

- 单句 AB 试听：同一段保存多个候选音频，用户选择一个作为最终版本。
- 导出前检查：缺失音色、缺失音频、缓存过期、音频参数不一致、未保存更改。
- 失败重试：单段失败不应让整条导出不可恢复。
- 质量标记：`missing`、`dirty`、`generating`、`ready`、`approved`、`failed`。
- manifest 记录每段的 profile、model、emotion、prompt 摘要、fingerprint、duration。

验收标准：

- 导出前能明确列出阻塞项。
- 用户批准过的段落不会因为无关编辑被误判失效。
- 生成失败后可以只重试失败段。

## 推荐实施顺序

优先级从高到低：

1. Phase 1：补齐提示词和参数映射。成本低，收益高，基本不影响 UI。
2. Phase 3：建立 provider adapter。解决 OpenAI/MiMo 差异，也是后续扩展的基础。
3. Phase 2：结构化人物人设。提升专业工作流，但涉及数据结构和 UI。
4. Phase 5：试听与质量验收。提升可交付性，适合和缓存机制一起做。
5. Phase 4：上下文感知情绪规划。最有价值但不宜最先做，依赖前面几层稳定。

## 关键测试建议

### 单元测试

- `build_segment_delivery_instruction()`：
  - `intensity=1.8` 时输出高强度表演描述。
  - `pitch=-3` 时输出压低声线描述。
  - `transition='suppressed_burst'` 时输出先压抑再爆发描述。

- `build_voice_prompt()`：
  - 有人设字段时输出“人物人设”区块。
  - 旧 profile 没有人设字段时保持兼容。
  - voice clone 时仍强调样音优先。

- `tts_adapters.openai`：
  - `input` 等于原文。
  - `instructions` 包含身份、人设、表演、边界。
  - `speed` 来自 `rate` 并被 clamp 到合法范围。
  - `tts-1` 不发送 `instructions`。

- `tts_adapters.mimo`：
  - user message 包含 voice design prompt。
  - assistant message 只包含要朗读文本或供应商风格标签加文本。
  - voice clone 使用样音作为 `audio.voice`。

### 路由测试

- 单句试听会使用段落音色覆盖，否则使用工程默认音色。
- 修改文本、情绪、人设、模型后缓存失效。
- 只修改节点坐标不应让音频缓存失效。
- 导出前存在失败段时返回明确错误。

### 前端测试

- 新建音色档案能保存人设字段。
- 选择工程默认音色后，未单独设置音色的段落标记为缓存失效。
- 手动修改表演指令后，当前段状态变为 `missing` 或 `dirty`。

## 风险与取舍

1. 不同 TTS 平台对情绪控制的实际支持程度不同。

   解决方式：UI 和 manifest 明确展示 provider capability。不能真实控制的参数转为自然语言提示或后处理，不假装完全生效。

2. 人设字段太多会增加用户负担。

   解决方式：基础用户只填“我想要的声音”；高级区才展开人设字段。系统可以用默认值和模板补齐。

3. LLM 情绪规划可能不稳定。

   解决方式：LLM 只做建议，用户确认后才应用；手动编辑优先级最高。

4. 分段合成仍可能有声线漂移。

   解决方式：稳定性提示、voice clone 样音优先、相邻上下文摘要、AB 试听和 approved 缓存共同降低风险。

## 最小可行改造

如果只做一个短周期版本，建议限定为：

1. 改 `build_segment_delivery_instruction()`，补 `intensity`、`pitch`、更多 transition。
2. 新增 `server/services/tts_adapters/openai.py` 和 `mimo.py`，先只支持 payload 构建测试，不急着切换所有路由。
3. OpenAI provider 默认模型更新为 `gpt-4o-mini-tts`，并支持 `instructions`、`speed`、`response_format='wav'`。
4. manifest 增加每段生成参数摘要。
5. 加对应单元测试。

这组改造能先解决“当前情绪和人设是否真的进入生成”的核心问题，同时避免一次性改动过大。


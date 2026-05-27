# 多模型供应商与模型选择优化方案

## 背景

当前项目的模型配置基本围绕 MiMo：

```text
MiMo TTS API Key
MiMo LLM API Key
MiMo TTS 模型
MiMo LLM 润色模型
```

随着功能扩展，系统需要同时支持：

- 多个 LLM 供应商：MiniMax、DeepSeek、ChatGPT/OpenAI、自定义 OpenAI-compatible API
- 多个 TTS 供应商：MiMo、MiniMax、OpenAI TTS、自定义 TTS API
- 用户自定义模型
- 不同功能使用不同模型

因此需要把“API Key 设置”升级为“模型供应商与用途路由设置”。

## 目标

1. 系统内置多个模型供应商和常用模型。
2. 用户可以新增自定义供应商和模型。
3. 用户可以为不同用途选择默认模型。
4. 前端选择过程清晰，不把一堆 Key 和模型堆在同一个表单里。
5. 后端通过统一 provider registry 调用 LLM/TTS，不再把 MiMo 写死在业务路由中。

## 非目标

1. 不在第一阶段实现所有供应商的完整高级参数。
2. 不把 API Key 存入导出包或 manifest。
3. 不强制迁移现有 MiMo 配置，需兼容旧 localStorage。
4. 不在第一阶段做团队多用户权限。

## 核心概念

### Provider

供应商，例如：

```text
mimo
minimax
deepseek
openai
custom_openai_compatible
custom_tts
```

### Model

供应商下的具体模型，例如：

```text
mimo-v2.5-tts-voicedesign
mimo-v2.5-tts-voiceclone
deepseek-chat
gpt-4.1-mini
tts-1
```

### Capability

模型能力，不同能力决定模型可用于哪些功能：

```text
llm_text
llm_voice_prompt_polish
tts_builtin_voice
tts_voice_design
tts_voice_clone
tts_plain
```

### Usage

系统中的具体用途：

```text
voice_prompt_polish     音色描述优化
tts_audition            音色试听
tts_video_voiceover     视频旁白
tts_sync_package        同步包语音
script_polish           文案润色
scene_planning          分镜规划
```

## 推荐用户流程

### 第一次配置

```text
打开设置
-> 选择“API 与模型”
-> 添加供应商 Key
-> 系统自动显示该供应商支持的模型
-> 选择各用途默认模型
-> 测试连接
-> 保存
```

### 日常切换

```text
设置 -> 用途默认模型
音色描述优化：DeepSeek / deepseek-chat
音色试听：MiMo / voiceclone
视频旁白：MiMo / voiceclone
分镜规划：ChatGPT / gpt-4.1-mini
```

### 单次覆盖

在语音合成或视频生成页面，只允许轻量覆盖：

```text
本次使用模型：[默认模型 v]
```

默认不展开 API Key。

## 系统预设供应商

### LLM 供应商

| Provider | 用途 | 模型示例 | API 形态 |
|----------|------|----------|----------|
| DeepSeek | 文案润色、音色 prompt 优化、分镜规划 | `deepseek-chat` | OpenAI-compatible |
| ChatGPT/OpenAI | 高质量文案、分镜、结构化规划 | `gpt-4.1-mini`, `gpt-4.1` | OpenAI API |
| MiniMax | 中文文本处理、对话生成 | 需按实际可用模型配置 | 厂商 API |
| MiMo Token Plan | 现有音色描述润色 | `mimo-v2.5-pro` | Anthropic-like |
| 自定义 OpenAI-compatible | 用户自己的代理或兼容服务 | 用户填写 | OpenAI-compatible |

### TTS 供应商

| Provider | 用途 | 模型示例 | 特点 |
|----------|------|----------|------|
| MiMo | 音色设计、音色复刻、预置音色 | `mimo-v2.5-tts-voicedesign`, `mimo-v2.5-tts-voiceclone` | 当前主力，适合角色声 |
| MiniMax TTS | 中文 TTS，可作为备用 | 用户配置 | 需要后续接具体 API |
| OpenAI TTS | 通用旁白、英文/多语种 | `tts-1`, `gpt-4o-mini-tts` | 稳定通用 |
| 自定义 TTS | 用户自建或第三方服务 | 用户填写 | 需定义请求模板 |

## 模型选择界面

建议将设置页从单一 modal 升级为 drawer 或 modal + tabs。

```text
设置
├── API Key
├── 默认模型
├── 供应商管理
└── 高级
```

### Tab 1：API Key

按供应商分组：

```text
MiMo
[API Key                         ]
状态：未测试 / 可用 / 失败
[测试连接]

DeepSeek
[API Key                         ]
[Base URL: https://api.deepseek.com]
状态：未测试
[测试连接]

OpenAI / ChatGPT
[API Key                         ]
[Base URL: https://api.openai.com/v1]
[测试连接]
```

只显示用户启用的供应商。未启用供应商折叠在“添加供应商”中。

### Tab 2：默认模型

按用途选择，不按供应商堆列表：

```text
语音合成
音色试听              [MiMo / voiceclone v]
同步包语音            [MiMo / voiceclone v]
视频旁白              [MiMo / voiceclone v]

文本与规划
音色描述优化          [DeepSeek / deepseek-chat v]
文案润色              [ChatGPT / gpt-4.1-mini v]
分镜规划              [ChatGPT / gpt-4.1-mini v]
```

用户不需要先理解供应商，只需要知道“这个用途用哪个模型”。

### Tab 3：供应商管理

```text
已启用供应商
- MiMo
- DeepSeek
- OpenAI

[添加供应商]
```

添加供应商表单：

```text
供应商类型
[DeepSeek / OpenAI / MiniMax / 自定义 OpenAI-compatible / 自定义 TTS]

显示名称
[我的代理服务]

Base URL
[https://...]

API Key
[********]

能力
[x] LLM
[ ] TTS
[ ] Voice Clone

[保存并测试]
```

### Tab 4：高级

高级配置包括：

- 超时时间
- 重试次数
- 默认 max tokens
- 默认 temperature
- 是否保存连接测试日志
- 是否允许单次任务覆盖模型

## 前端数据结构

建议新增 `modelSettings`，不要继续把所有 Key 平铺成 `ttsKey`、`llmKey`。

```js
{
  "providers": [
    {
      "id": "mimo",
      "name": "MiMo",
      "type": "mimo",
      "enabled": true,
      "baseUrl": "https://api.xiaomimimo.com",
      "apiKey": "...",
      "capabilities": ["tts_voice_design", "tts_voice_clone", "llm_text"],
      "models": [
        {
          "id": "mimo-v2.5-tts-voicedesign",
          "label": "MiMo 音色设计",
          "capabilities": ["tts_voice_design"]
        }
      ]
    }
  ],
  "defaults": {
    "voice_prompt_polish": {
      "providerId": "deepseek",
      "modelId": "deepseek-chat"
    },
    "tts_audition": {
      "providerId": "mimo",
      "modelId": "mimo-v2.5-tts-voiceclone"
    },
    "tts_sync_package": {
      "providerId": "mimo",
      "modelId": "mimo-v2.5-tts-voiceclone"
    },
    "scene_planning": {
      "providerId": "openai",
      "modelId": "gpt-4.1-mini"
    }
  }
}
```

### 兼容旧配置

现有 localStorage：

```text
mimo_tts_key
mimo_llm_key
mimo_polish_prompt
```

迁移策略：

1. 首次打开设置时检测旧 key。
2. 自动创建 `mimo` provider。
3. 将旧 TTS Key 写入 MiMo provider。
4. 将旧 LLM Key 写入 MiMo Token Plan provider 或 MiMo provider 的 LLM key 字段。
5. 保留旧 key 一段时间，避免回滚失败。

## 后端架构

新增统一 provider registry。

```text
server/services/model_registry.py
server/services/model_provider_base.py
server/services/providers/mimo_provider.py
server/services/providers/openai_compatible_provider.py
server/services/providers/deepseek_provider.py
server/services/providers/openai_provider.py
server/services/providers/minimax_provider.py
```

### Provider 接口

```python
class ModelProvider:
    provider_id: str
    capabilities: list[str]

    def complete(self, messages, model, options):
        raise NotImplementedError

    def synthesize(self, text, model, voice_options, options):
        raise NotImplementedError

    def test_connection(self):
        raise NotImplementedError
```

### 业务层调用

业务路由不直接知道供应商细节：

```python
provider = registry.resolve(defaults['voice_prompt_polish'])
result = provider.complete(messages, model, options)
```

TTS：

```python
provider = registry.resolve(defaults['tts_sync_package'])
audio = provider.synthesize(text, model, voice_options, options)
```

## 数据库存储建议

如果继续轻量本地单用户，可以先用 localStorage 保存前端配置。

如果要云端持久化，建议新增表：

```text
model_providers
- id
- provider_key
- display_name
- provider_type
- base_url
- api_key_encrypted
- capabilities_json
- config_json
- is_builtin
- is_active
- created_at
- updated_at

model_catalog
- id
- provider_id
- model_key
- display_name
- capabilities_json
- config_json
- is_builtin
- is_active
- sort_order
- created_at
- updated_at

model_usage_defaults
- id
- usage_key
- provider_id
- model_id
- options_json
- created_at
- updated_at
```

第一阶段建议仍保存在 localStorage，因为当前项目没有用户系统；后端只接收前端传来的 provider/model/API Key 快照。

## API 设计

### 获取系统预设供应商

```http
GET /api/model-providers/presets
```

返回：

```json
[
  {
    "provider_key": "deepseek",
    "display_name": "DeepSeek",
    "provider_type": "openai_compatible",
    "base_url": "https://api.deepseek.com",
    "capabilities": ["llm_text"],
    "models": [
      {
        "model_key": "deepseek-chat",
        "display_name": "DeepSeek Chat",
        "capabilities": ["llm_text", "llm_voice_prompt_polish"]
      }
    ]
  }
]
```

### 测试连接

```http
POST /api/model-providers/test
```

请求：

```json
{
  "provider_type": "openai_compatible",
  "base_url": "https://api.deepseek.com",
  "api_key": "...",
  "model": "deepseek-chat",
  "capability": "llm_text"
}
```

响应：

```json
{
  "ok": true,
  "latency_ms": 820,
  "message": "连接成功"
}
```

### 统一 LLM 调用

```http
POST /api/models/llm/complete
```

### 统一 TTS 调用

```http
POST /api/models/tts/synthesize
```

旧接口仍保留：

```text
POST /api/tts/synthesize
POST /api/tts/polish
POST /api/tts/sync-package-v2
```

但内部逐步改为调用 registry。

## 预设模型建议

### DeepSeek

```json
{
  "provider_key": "deepseek",
  "display_name": "DeepSeek",
  "provider_type": "openai_compatible",
  "base_url": "https://api.deepseek.com",
  "models": [
    {
      "model_key": "deepseek-chat",
      "display_name": "DeepSeek Chat",
      "capabilities": ["llm_text", "llm_voice_prompt_polish", "scene_planning"]
    }
  ]
}
```

### ChatGPT / OpenAI

```json
{
  "provider_key": "openai",
  "display_name": "ChatGPT / OpenAI",
  "provider_type": "openai",
  "base_url": "https://api.openai.com/v1",
  "models": [
    {
      "model_key": "gpt-4.1-mini",
      "display_name": "GPT-4.1 Mini",
      "capabilities": ["llm_text", "scene_planning", "script_polish"]
    },
    {
      "model_key": "gpt-4.1",
      "display_name": "GPT-4.1",
      "capabilities": ["llm_text", "scene_planning", "script_polish"]
    },
    {
      "model_key": "tts-1",
      "display_name": "OpenAI TTS",
      "capabilities": ["tts_plain"]
    }
  ]
}
```

### MiMo

```json
{
  "provider_key": "mimo",
  "display_name": "MiMo",
  "provider_type": "mimo",
  "models": [
    {
      "model_key": "mimo-v2.5-tts",
      "display_name": "MiMo 预置音色",
      "capabilities": ["tts_builtin_voice"]
    },
    {
      "model_key": "mimo-v2.5-tts-voicedesign",
      "display_name": "MiMo 音色设计",
      "capabilities": ["tts_voice_design"]
    },
    {
      "model_key": "mimo-v2.5-tts-voiceclone",
      "display_name": "MiMo 音色复刻",
      "capabilities": ["tts_voice_clone"]
    },
    {
      "model_key": "mimo-v2.5-pro",
      "display_name": "MiMo Pro",
      "capabilities": ["llm_text", "llm_voice_prompt_polish"]
    }
  ]
}
```

### MiniMax

```json
{
  "provider_key": "minimax",
  "display_name": "MiniMax",
  "provider_type": "minimax",
  "models": [
    {
      "model_key": "minimax-text-default",
      "display_name": "MiniMax 文本模型",
      "capabilities": ["llm_text"]
    },
    {
      "model_key": "minimax-tts-default",
      "display_name": "MiniMax TTS",
      "capabilities": ["tts_plain"]
    }
  ]
}
```

MiniMax 具体模型名和 API 参数应在接入时按官方控制台实际可用模型更新。

## 模型选择体验优化

### 不让用户先选供应商

用户真正关心的是用途：

```text
我要优化音色描述
我要生成角色语音
我要做分镜规划
```

因此默认模型页应按用途组织，而不是按供应商组织。

### 模型选择器显示格式

```text
DeepSeek / DeepSeek Chat
MiMo / 音色复刻
ChatGPT / GPT-4.1 Mini
```

并显示能力标签：

```text
LLM
TTS
Voice Clone
OpenAI-compatible
```

### 禁用不匹配模型

例如“音色试听”只能选带 TTS 能力的模型：

```text
音色试听
[MiMo / 音色复刻]

DeepSeek Chat 灰掉，因为它没有 TTS 能力。
```

## 前端组件建议

```text
web/src/components/settings/SettingsDrawer.vue
web/src/components/settings/ProviderKeyPanel.vue
web/src/components/settings/UsageModelPanel.vue
web/src/components/settings/ProviderManager.vue
web/src/components/settings/ProviderForm.vue
web/src/components/settings/ModelSelect.vue
web/src/stores/modelSettings.js
```

`ApiSettingsModal.vue` 可作为兼容入口，内部逐步迁移到 `SettingsDrawer`。

## 后端迁移策略

### Phase 1：前端设置模型化

- 保留现有 MiMo 后端调用。
- 前端新增 provider/model 配置结构。
- 旧 MiMo key 自动迁移为 MiMo provider。
- 设置页支持 DeepSeek/OpenAI/MiniMax/自定义供应商录入。

### Phase 2：LLM provider registry

- 将 `/api/tts/polish` 改成走 LLM registry。
- 支持 DeepSeek / OpenAI-compatible 做音色描述优化。
- 保留 MiMo LLM 作为一个 provider。

### Phase 3：TTS provider registry

- 将 `/api/tts/synthesize`、`sync-package-v2` 改成走 TTS registry。
- MiMo 为默认 provider。
- OpenAI TTS / MiniMax TTS 作为可选 provider。

### Phase 4：云端持久化

- 新增 `model_providers`、`model_catalog`、`model_usage_defaults`。
- API Key 加密存储。
- 支持多设备同步设置。

## 安全建议

1. API Key 继续优先存本地，除非有用户系统和加密存储。
2. 连接测试接口不要把 Key 写入日志。
3. manifest 不记录 Key，只记录 provider/model。
4. 导出包不包含 Key。
5. 自定义 provider 的 Base URL 需要限制协议为 HTTPS，避免误传 Key 到不安全地址。

## 验收标准

1. 设置页能添加 DeepSeek、ChatGPT/OpenAI、MiniMax、自定义供应商。
2. 用户能为不同用途选择默认模型。
3. TTS 用途不能选择纯 LLM 模型。
4. LLM 用途不能选择纯 TTS 模型。
5. 旧 MiMo Key 能自动迁移或继续生效。
6. 业务页面不再展示一堆供应商 Key，只显示当前用途模型。
7. 后端业务路由逐步从 MiMo 专用调用迁移到 provider registry。

## 推荐结论

最合理的用户模型选择过程是：

```text
先添加供应商 Key
再按用途选择默认模型
业务生成时默认使用对应用途模型
高级用户可单次覆盖
```

不要让用户在语音合成或视频生成时先理解所有供应商差异。设置页负责复杂性，业务页只展示“当前使用哪个模型”和“是否可用”。

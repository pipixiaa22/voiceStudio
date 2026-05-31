# 视频生成与配音工程对接设计

## 背景

当前视频生成已经具备模板、异步任务、预览下载、多步骤弹窗、场景图片上传和基础素材包导出。配音工程已经具备线性语句编排、情绪参数、语速音量停顿、音色档案绑定、音频缓存、整条路径试听、SRT/manifest 导出和剪映字幕注入。

两套能力还没有真正串起来。视频生成弹窗的音频步骤已经出现“配音工程”选项，但后端视频任务仍主要走“文本拆分 -> 普通 TTS -> 字幕时间轴”的旧路径，没有消费 `voice_workflow_id`，也没有复用配音工程的情绪分段、缓存音频、音色绑定和字幕时间轴。

## 目标

1. 视频生成任务支持从已有配音工程生成视频。
2. workflow 模式下，视频旁白复用配音工程的线性顺序、分段文本、情绪参数、音色档案、停顿和缓存音频。
3. workflow 模式下，字幕时间轴来自配音工程的 emotional subtitle timeline，而不是重新按原文拆分。
4. workflow 模式下，素材包 manifest 明确标记来源为 `voice_workflow`，并包含 workflow id、分段信息、字幕时间轴和视频配置。
5. 保留原有文本直接生成视频路径，未选择配音工程时继续可用。
6. 前端视频生成弹窗把用户选择的配音工程传给 video job，并在预览步骤展示音频来源。
7. 为后续从配音工作台反向进入视频生成留下接口边界，但第一阶段不强制完成该入口。

## 非目标

1. 第一阶段不重做字幕样式系统。
2. 第一阶段不做多轨音频编辑器或波形裁剪。
3. 第一阶段不引入复杂视频时间线编辑。
4. 第一阶段不做 AI 图片生成。
5. 第一阶段不要求环境音素材库完整落地；保留 `ambient_key` 配置，内置素材存在后再真实混入。
6. 第一阶段不把 `/api/video/jobs` 改成 multipart；BGM 文件上传作为独立小闭环处理。

## 推荐路径

先实现“视频生成弹窗选择已有配音工程”的入口。

原因：

- 当前 UI 已经有 `voice_source: "workflow"` 和 `voice_workflow_id` 的雏形，成本最低。
- 后端 `video_job.py` 是实际断点，先打通它能让成片质量立刻受益。
- 保留文本直接生成路径，可以降低回归风险。
- 配音工作台里的“生成视频”按钮可以复用同一套 job payload，作为第二阶段 UI 入口。

## 用户流程

```text
用户打开视频生成弹窗
-> 音频步骤选择“配音工程”
-> 选择一个已有配音工程
-> 上传场景图，选择模板和音频设置
-> 创建视频任务
-> 后端读取配音工程
-> 复用或生成每句配音音频
-> 拼接完整旁白并生成字幕时间轴
-> 混入 BGM/环境音
-> 渲染 MP4
-> 输出 MP4 + 素材包
```

## 后端设计

### Job 请求结构

新增或规范化字段：

```json
{
  "voice_source": "workflow",
  "voice_workflow_id": 1,
  "template_key": "xianxia_narration",
  "scenes": [
    {
      "imagePath": "/absolute/path/to/image.png",
      "motion": "slow_zoom_in"
    }
  ],
  "audio_options": {
    "bgm_enabled": false,
    "bgm_path": null,
    "bgm_volume": 0.18,
    "bgm_fade_in": 1.0,
    "bgm_fade_out": 1.5,
    "ambient_enabled": false,
    "ambient_key": "wind",
    "ambient_volume": 0.12
  },
  "subtitle_options": {
    "max_chars": 20
  },
  "api_key": "..."
}
```

兼容规则：

- `voice_source === "workflow"` 且 `voice_workflow_id` 存在时，进入 workflow 模式。
- 没有 `voice_workflow_id` 时，继续走现有文本模式。
- 如果传入的 workflow 不存在，job 失败并返回“配音工程不存在”。
- 如果 workflow 没有有效线性路径或没有语句，job 失败并返回配音工程校验错误。

### 服务边界

新增一个内部 helper，放在 `server/services/video_job.py` 或拆到 `server/services/video_voice_workflow.py`：

```python
def build_voice_track_from_workflow(workflow_id: int, request_data: dict) -> dict:
    return {
        "voice_audio": full_voice_audio_bytes,
        "subtitle_timeline": timeline,
        "manifest": workflow_manifest,
        "voice_chunks": manifest_segments,
        "duration": total_duration,
    }
```

该 helper 负责：

1. 查询 `VoiceWorkflow`。
2. 调用 `ordered_segments(workflow)` 获取真实播放顺序。
3. 对每个 segment 调用配音工程已有的合成/缓存逻辑。
4. 调用 `concat_emotional_wavs()` 拼接完整旁白。
5. 调用 `build_emotional_subtitle_timeline()` 生成字幕时间轴。
6. 调用 `build_workflow_manifest()` 生成 workflow manifest。

为了避免直接依赖 Flask route 私有函数，配音工程里已有的缓存和合成逻辑应抽到 service 层，供 `routes/voice_workflows.py` 和 `video_job.py` 共同使用。第一阶段可以移动以下能力：

- `_synthesize_or_cache_segment`
- `_cache_status_for_segment`
- `_cache_path_for_fingerprint`
- `_profile_audio_voice`

目标位置建议为 `server/services/voice_workflow_audio.py`。

### Video Job 数据流

`_process_job()` 的核心分支：

```text
读取 request_data
-> 读取模板配置
-> if voice_source == workflow:
     build_voice_track_from_workflow()
   else:
     build_voice_track_from_text()
-> mix_audio()
-> render video
-> build_capcut_zip()
-> update_job_completed()
```

文本模式保留当前行为，但可以被整理为 `build_voice_track_from_text()`，减少 `_process_job()` 体积。

### 音频混音

当前 `mix_audio()` 已支持 `voice_wav`、`bgm_wav` 和 `ambient_wav`，但 job 没有真实读取 BGM 文件。

第一阶段完成：

- workflow 模式下 `voice_wav` 使用配音工程拼接出的完整旁白。
- 渲染视频时使用 `mixed_audio`，而不是始终使用未混音 `voice_audio`。
- 若 `bgm_path` 存在且文件可读，将其读入并传给 `mix_audio()`。
- 如果 `bgm_enabled` 为 true 但没有 `bgm_path`，保留旁白音频并在 manifest 中记录 warning。

BGM 上传作为紧邻任务：

- 新增 `/api/video/upload-audio`。
- 第一阶段只接收 `.wav`，避免把音频转码兼容扩大成另一个项目。
- 保存到 `outputs/uploads/audio/`。
- 返回 `{ filename, path }`。
- 前端 `AudioMixStep.vue` 上传 BGM 后把 `bgm_path` 放入 `audio_options`。

后续再扩展 mp3/m4a 上传，并在服务端通过 moviepy 或 ffmpeg 转成 WAV 后交给 `mix_audio()`。

### 视频渲染

当前 `_generate_simple_video()` 接收 `voice_path`，但 workflow 模式需要用混音结果渲染：

- 参数命名改成 `audio_path`。
- 写入临时文件时同时保存 `voice.wav` 和 `mixed.wav`。
- `mixed_audio` 存在时渲染使用 `mixed.wav`。
- 素材包仍同时包含完整旁白和混音音频。

### Manifest

workflow 模式 manifest 至少包含：

```json
{
  "title": "视频标题",
  "source": "voice_workflow",
  "workflow_id": 1,
  "template_key": "xianxia_narration",
  "duration": 12.3,
  "resolution": [1080, 1920],
  "segments": [],
  "subtitles": [],
  "video": {
    "scenes": [],
    "audio_options": {},
    "warnings": []
  }
}
```

文本模式 manifest 保持当前结构，但可以增加 `source: "text"`。

## 前端设计

### AudioMixStep

现状已有：

- `voice_source`
- `voice_workflow_id`
- workflow 列表加载
- BGM 上传 UI
- BGM/环境音设置

需要补齐：

- 对外 `v-model:audio-options` 中稳定输出 `voice_source`、`voice_workflow_id` 和 `bgm_path`。
- 选择配音工程时要求 `voice_workflow_id` 非空才能下一步。
- BGM 上传调用 `/api/video/upload-audio`，成功后设置 `audio_options.bgm_path`。
- 如果第一阶段只支持 WAV，上传控件提示并限制 `.wav`。

### VideoGenerateModal

创建 job 时：

- 从 `audioOptions` 读取 `voice_source` 和 `voice_workflow_id`。
- 顶层 payload 同时传 `voice_source`、`voice_workflow_id`，便于后端分支判断。
- `audio_options` 保留完整音频设置。

示例：

```js
const response = await videoApi.createJob({
  text_id: props.textId,
  title: props.textTitle,
  template_key: selectedTemplate.value?.template_key || 'xianxia_narration',
  scenes: uploadedScenes,
  speaker_profiles: speakerProfiles.value,
  voice_source: audioOptions.value.voice_source || 'generate',
  voice_workflow_id: audioOptions.value.voice_workflow_id || null,
  audio_options: audioOptions.value,
  subtitle_options: props.prefill?.subtitle_options || undefined,
  api_key: ttsKey.value,
})
```

### VideoPreviewStep

预览步骤展示：

- 音频来源：自动生成 / 配音工程。
- 如果是配音工程，展示 workflow 名称或 id。
- BGM 状态和环境音状态保持当前展示。

### 配音工作台反向入口

第一阶段只留边界：

- 后端 `createJob` 已支持 `voice_workflow_id`。
- 后续 `VoiceWorkflowView.vue` 可新增“生成视频”按钮，打开视频生成弹窗并预填 `audio_options.voice_source = "workflow"` 与当前 workflow id。

## 错误处理

workflow 模式下的错误信息要落到 job 的 `error_message`：

- 配音工程不存在。
- 配音工程没有语句。
- 配音工程连线不是完整线性路径。
- 某一句合成失败，错误包含 `order_index`。
- BGM 文件路径不存在或不可读。
- 字幕时间轴为空。

前端 job 进度页沿用现有失败展示。

## 测试策略

### 后端

新增或扩展：

- `server/tests/test_video_job.py`
  - workflow 模式读取 `VoiceWorkflow` 并生成 voice track。
  - workflow 模式 manifest 包含 `source: "voice_workflow"` 和 `workflow_id`。
  - workflow 模式使用 emotional subtitle timeline。
  - workflow 不存在时 job 失败。
  - 未传 workflow 时文本模式仍可用。

- `server/tests/test_voice_workflow_audio.py`
  - 抽出的缓存路径、fingerprint、合成复用逻辑保持行为不变。
  - ready 缓存存在时不重新调用 TTS。

- `server/tests/test_video.py`
  - `/api/video/upload-audio` 接收 WAV 并返回 path。
  - 不支持的 BGM 格式返回 400。

### 前端

如果当前测试体系允许，补源码级测试：

- `VideoGenerateModal.vue` 创建 job payload 包含 `voice_source` 和 `voice_workflow_id`。
- `AudioMixStep.vue` workflow 模式下暴露配音工程选择控件。
- `web/src/api/index.js` 包含 `uploadAudio` API。

### 手动验收

1. 创建一个配音工程，生成至少两句音频。
2. 从文本页打开视频生成。
3. 在音频步骤选择该配音工程。
4. 上传场景图并生成视频。
5. 等待 job 完成。
6. 预览 MP4，确认旁白来自配音工程。
7. 下载素材包，确认包含 MP4、完整旁白、混音音频、SRT 和 manifest。
8. 检查 manifest 的 `source` 为 `voice_workflow`。

## 分阶段实施

### 第一阶段：后端真实接通

- 抽出配音工程音频 service。
- `video_job.py` 增加 workflow voice track 分支。
- 渲染使用 mixed audio。
- manifest 标记 workflow 来源。
- 增加后端测试。

### 第二阶段：前端闭环

- `AudioMixStep.vue` 稳定输出 workflow 设置。
- `VideoGenerateModal.vue` 传递 workflow payload。
- `VideoPreviewStep.vue` 展示音频来源。
- 补 `uploadAudio` API 和 WAV 上传。

### 第三阶段：配音工作台入口

- `VoiceWorkflowView.vue` 增加“生成视频”入口。
- 打开视频生成弹窗并预填当前 workflow。
- 可选：从 workflow preflight 状态提醒缺失音频。

## 验收标准

1. 选择配音工程生成视频时，后端不再重新从文本拆分生成普通语音，而是使用配音工程线性路径。
2. 成片音频包含配音工程的分段情绪、音色、语速、音量和停顿效果。
3. 字幕时间轴与配音工程导出的字幕时间轴一致。
4. 素材包 manifest 明确包含 `source: "voice_workflow"` 和 `workflow_id`。
5. 未选择配音工程时，原文本生成视频路径仍能工作。
6. job 失败时能给出配音工程相关的明确错误。
7. 后端相关测试通过。

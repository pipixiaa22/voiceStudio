# 视频生成模块升级开发文档

## 背景

当前视频生成模块主要完成“背景图 + TTS 音频 + 字幕 -> MP4”的基础合成。这个能力已经能产出静态图片视频，但对修仙题材短视频来说，还缺少完整的成片工作流。

本方案排除“字幕样式升级”，只聚焦以下能力：

1. 视频模板系统
2. BGM 与环境音混音
3. 动态画面效果
4. 多分镜生成
5. 角色声线绑定
6. 剪映友好导出包
7. 生成前预览
8. 异步任务与进度

## 目标

让视频生成从一次性合成工具升级为“修仙短视频生成流程”：

```text
文本/分镜脚本
-> 选择视频模板
-> 绑定角色音色
-> 上传或选择场景图/BGM
-> 生成预览
-> 异步生成成片
-> 导出 MP4 + 剪映友好素材包
```

## 非目标

1. 不在本阶段重做字幕样式系统。
2. 不引入复杂的视频剪辑时间线编辑器。
3. 不实现 AI 图片生成，只支持用户上传或选择已有图片。
4. 不替代专业剪辑软件，重点是生成可用初版视频和素材包。

## 当前实现概览

相关文件：

```text
server/routes/video.py
server/routes/tts.py
server/services/tts_provider.py
web/src/components/VideoGenerateModal.vue
web/src/components/VoiceSynthModal.vue
```

当前问题：

- 只支持单张背景图。
- 缺少视频模板。
- 缺少 BGM/环境音混音。
- 没有多分镜。
- 没有角色音色绑定。
- 长视频生成依赖单次 HTTP 请求，缺少任务进度。
- 导出结果主要是 MP4，不够方便后期剪映精修。

## 推荐架构

新增服务层：

```text
server/services/video_template.py
server/services/video_scene_planner.py
server/services/audio_mixer.py
server/services/video_renderer.py
server/services/video_job.py
server/services/capcut_package.py
```

职责：

| 模块 | 职责 |
|------|------|
| `video_template.py` | 管理视频模板、默认参数、特效配置 |
| `video_scene_planner.py` | 把文本/语音块规划为多个 scene |
| `audio_mixer.py` | 旁白、BGM、环境音混音 |
| `video_renderer.py` | 根据 scene 渲染视频 |
| `video_job.py` | 异步任务、进度、失败重试 |
| `capcut_package.py` | 导出 MP4、音频、SRT、manifest、素材清单 |

## 一、视频模板系统

### 目标

模板是视频生成的核心入口。它定义视频的尺寸、节奏、画面动态、BGM 策略、默认转场和导出配置。

### 初始模板

建议先提供 5 个模板：

| 模板 | 场景 | 画面节奏 |
|------|------|----------|
| 修仙旁白 | 通用剧情叙述 | 慢推近、轻微云雾、低音量 BGM |
| 角色独白 | 师尊/女主/小师妹台词 | 单图慢推、音色优先、少量环境音 |
| 章节标题 | 章节开头、转折 | 标题卡、短音效、淡入淡出 |
| 战斗转场 | 冲突、天劫、剑气 | 快速缩放、闪白、剑鸣/雷声 |
| 功法讲解 | 丹药、境界、功法设定 | 稳定画面、清晰旁白、少动效 |

### 模板结构

```json
{
  "template_key": "xianxia_narration",
  "name": "修仙旁白",
  "aspect_ratio": "9:16",
  "resolution": [1080, 1920],
  "fps": 24,
  "scene_duration_strategy": "audio",
  "visual_effects": {
    "motion": "slow_zoom_in",
    "overlay": "mist",
    "transition": "fade"
  },
  "audio": {
    "bgm_volume": 0.18,
    "voice_volume": 1.0,
    "ambient_volume": 0.12,
    "fade_in": 1.0,
    "fade_out": 1.5
  },
  "export": {
    "include_source_package": true,
    "video_codec": "libx264",
    "audio_codec": "aac"
  }
}
```

### 前端表现

`VideoGenerateModal.vue` 中新增模板选择：

```text
模板
[修仙旁白] [角色独白] [章节标题] [战斗转场] [功法讲解]
```

选中模板后自动填入默认参数，但允许用户展开高级设置调整。

## 二、BGM 与环境音混音

### 目标

支持用户上传 BGM，并可选择环境音。最终视频音轨由：

```text
旁白音频 + BGM + 环境音
```

混音生成。

### 功能

1. 上传 BGM 文件：mp3/wav/m4a。
2. 设置 BGM 音量，默认 15%-20%。
3. 自动淡入淡出。
4. BGM 时长不足时循环，超出时裁剪。
5. 环境音可选：风声、雨声、雷声、剑鸣、钟声、火焰声。
6. 环境音按模板或关键词触发。

### 后端实现

建议使用 moviepy 或 ffmpeg。

音频处理流程：

```text
voice.wav
bgm.mp3
ambient.wav
-> normalize
-> volume adjust
-> loop/crop bgm
-> fade in/out
-> mix
-> final_audio.m4a
```

### API 参数

```json
{
  "audio_options": {
    "bgm_enabled": true,
    "bgm_volume": 0.18,
    "bgm_fade_in": 1.0,
    "bgm_fade_out": 1.5,
    "ambient_enabled": true,
    "ambient_key": "wind",
    "ambient_volume": 0.12
  }
}
```

## 三、动态画面效果

### 目标

在不引入复杂剪辑器的情况下，让静态图有基本镜头运动，避免成片完全静止。

### 初始动效

| 效果 | 用途 |
|------|------|
| 慢推近 | 通用旁白 |
| 慢拉远 | 回忆、远景 |
| 左右平移 | 展示山门、云海、场景图 |
| 呼吸缩放 | 氛围、角色立绘 |
| 轻微震动 | 战斗、天劫 |
| 闪白 | 突破、雷劫、剑光 |
| 淡入淡出 | 场景切换 |

### Scene 配置

```json
{
  "scene_index": 1,
  "image": "scenes/001.png",
  "start": 0.0,
  "end": 8.4,
  "motion": "slow_zoom_in",
  "transition_in": "fade",
  "transition_out": "fade"
}
```

### 实现建议

第一阶段用 moviepy 实现：

- `resize` + 时间函数做 zoom。
- `set_position` 做平移。
- `fadein/fadeout` 做转场。
- 震动和闪白可作为特殊 overlay clip。

若 moviepy 性能不足，再迁移到 ffmpeg filter_complex。

## 四、多分镜生成

### 目标

支持一段文本对应多个场景图，而不是整条视频只用一张图。

### 分镜来源

第一阶段支持手动分镜：

```text
用户上传多张图片
-> 按顺序绑定到语音块或文本段
```

第二阶段支持半自动分镜：

```text
根据段落/语义/角色台词自动建议 scene
```

### 分镜数据结构

```json
{
  "scenes": [
    {
      "index": 1,
      "title": "山门云海",
      "image_file": "scene_001.png",
      "subtitle_start_index": 1,
      "subtitle_end_index": 8,
      "voice_chunk_indices": [1],
      "motion": "slow_zoom_in"
    },
    {
      "index": 2,
      "title": "师尊训诫",
      "image_file": "scene_002.png",
      "subtitle_start_index": 9,
      "subtitle_end_index": 18,
      "voice_chunk_indices": [2, 3],
      "motion": "breathing_zoom"
    }
  ]
}
```

### 前端交互

在视频生成弹窗中增加“分镜”步骤：

```text
分镜
Scene 01 山门云海       [上传图片] [绑定字幕 1-8]
Scene 02 师尊训诫       [上传图片] [绑定字幕 9-18]
Scene 03 天劫将至       [上传图片] [绑定字幕 19-27]
```

若用户只上传一张图，则自动创建一个 scene，保持兼容。

## 五、角色声线绑定

### 目标

修仙视频经常有多个角色。系统应支持根据台词角色自动切换音色档案。

### 文本格式

建议支持以下格式：

```text
【师尊】跪下。你既入我玄霜峰，便该知道修仙一途，从无侥幸二字。
【小师妹】师姐师姐！你看，我真的引气入体了！
【旁白】云海翻涌，仙门将启。
```

### 角色绑定结构

```json
{
  "speaker_profiles": {
    "旁白": 3,
    "师尊": 12,
    "小师妹": 8
  }
}
```

### 后端处理

1. 解析每段文本的 speaker。
2. 按 speaker 分配 `voice_profile_id`。
3. TTS 规划时不要把不同 speaker 合并到同一个语音块。
4. manifest 中记录每条字幕和语音块的 speaker。

### 前端交互

```text
角色声线
旁白      [温柔叙述女声 v]
师尊      [冷淡御姐声 v]
小师妹    [修仙萝莉声 v]
```

若文本未标注角色，则全部使用默认音色。

## 六、剪映友好导出包

### 目标

除了直接导出 MP4，也导出便于后期剪映精修的素材包。

### ZIP 结构

```text
作品标题_成片.mp4
作品标题_完整旁白.wav
作品标题_混音音频.m4a
作品标题_同步字幕.srt
manifest.json
scenes/
  001.png
  002.png
  003.png
audio/
  voice_chunks/001.wav
  bgm.mp3
  ambient/wind.wav
```

### manifest

```json
{
  "title": "作品标题",
  "template_key": "xianxia_narration",
  "duration": 68.4,
  "resolution": [1080, 1920],
  "scenes": [],
  "voice_chunks": [],
  "subtitles": [],
  "audio": {
    "voice": "作品标题_完整旁白.wav",
    "mixed": "作品标题_混音音频.m4a",
    "bgm": "audio/bgm.mp3"
  }
}
```

## 七、生成前预览

### 目标

长视频完整生成成本高，用户应先看到低成本预览。

### 预览形式

第一阶段：

- 时间轴摘要
- scene 列表
- 每个 scene 的首帧图
- 音色/角色绑定摘要
- BGM/环境音摘要

第二阶段：

- 生成 5-10 秒低清预览 MP4。
- 分辨率 360x640。
- 可只渲染前两个 scene。

### API

```http
POST /api/video/preview
```

响应：

```json
{
  "duration": 68.4,
  "scene_count": 5,
  "subtitle_count": 72,
  "voice_chunk_count": 9,
  "estimated_render_seconds": 35,
  "warnings": [
    "第 3 个 scene 未上传图片，将使用默认背景"
  ]
}
```

## 八、异步任务与进度

### 目标

视频生成可能耗时较长，应改成异步任务，避免 HTTP 请求超时。

### API

创建任务：

```http
POST /api/video/jobs
```

响应：

```json
{
  "job_id": "video-job-uuid",
  "status": "queued"
}
```

查询任务：

```http
GET /api/video/jobs/:job_id
```

响应：

```json
{
  "job_id": "video-job-uuid",
  "status": "rendering",
  "progress": 0.56,
  "stage": "mixing_audio",
  "message": "正在混合旁白与 BGM"
}
```

下载结果：

```http
GET /api/video/jobs/:job_id/download
```

### 任务状态

```text
queued
planning
synthesizing_voice
mixing_audio
rendering_video
packaging
completed
failed
```

### 第一阶段实现

如果不引入 Celery，可先使用：

- SQLite/MySQL 记录任务。
- 后端线程池执行任务。
- 文件输出到 `outputs/video_jobs/<job_id>/`。

后续再升级为 Celery/RQ。

## 数据库建议

新增表：

```text
video_templates
- id
- template_key
- name
- config_json
- is_builtin
- is_active
- sort_order
- created_at
- updated_at

video_jobs
- id
- job_id
- title
- status
- progress
- stage
- message
- request_json
- manifest_json
- output_path
- error_message
- created_at
- updated_at

video_assets
- id
- job_id
- asset_type
- filename
- path
- metadata_json
- created_at
```

第一阶段也可以先只用本地 JSON 文件保存模板，任务表后置。

## API 总览

```text
GET  /api/video/templates
POST /api/video/preview
POST /api/video/jobs
GET  /api/video/jobs/:job_id
GET  /api/video/jobs/:job_id/download
```

兼容旧接口：

```text
POST /api/video/generate
```

旧接口可以内部转成默认模板 + 单 scene + 同步执行。

## 前端改造

`VideoGenerateModal.vue` 建议改成步骤式：

```text
1. 模板
2. 画面/分镜
3. 音色/角色
4. 音频
5. 预览
6. 生成
```

组件拆分：

```text
web/src/components/video/VideoGenerateModal.vue
web/src/components/video/VideoTemplateStep.vue
web/src/components/video/ScenePlannerStep.vue
web/src/components/video/SpeakerVoiceStep.vue
web/src/components/video/AudioMixStep.vue
web/src/components/video/VideoPreviewStep.vue
web/src/components/video/VideoJobProgress.vue
```

## 分阶段落地

### Phase 1：模板 + BGM + 动态单图

- 新增模板配置。
- 单图视频支持慢推、平移、呼吸缩放。
- 支持上传 BGM 并混音。
- 保留旧生成接口。

### Phase 2：多分镜 + 剪映友好包

- 支持上传多张 scene 图片。
- 按 scene 渲染并拼接。
- 导出 MP4 + 音频 + SRT + manifest + 素材。

### Phase 3：角色声线绑定

- 解析 `【角色】台词`。
- 角色绑定音色档案。
- TTS 按角色拆分语音块。
- manifest 写入 speaker 信息。

### Phase 4：异步任务 + 预览

- 新增 video_jobs。
- 前端轮询进度。
- 支持失败状态和下载历史结果。
- 支持低清预览。

## 验收标准

1. 用户可以选择视频模板。
2. 用户可以上传 BGM，并在生成视频中听到混音结果。
3. 单张背景图视频不再完全静止，至少支持一种动态镜头。
4. 用户可以上传多张图并按顺序生成多分镜视频。
5. 角色标注文本可以绑定不同音色档案。
6. 导出包包含 MP4、完整音频、SRT、manifest 和 scene 素材。
7. 长视频生成不阻塞前端，能看到任务进度。
8. 旧的单图视频生成路径仍然可用。

## 推荐优先级

建议按以下顺序开发：

```text
1. 视频模板系统
2. BGM 混音
3. 动态画面效果
4. 多分镜支持
5. 剪映友好导出包
6. 角色声线绑定
7. 生成前预览
8. 异步任务与进度
```

其中模板系统应最先做，因为它是后续 BGM、动态画面、多分镜和导出策略的配置入口。

# 视频生成功能设计

## 概述

为字幕工坊添加视频生成功能，用户上传一张图片，系统自动将文本转语音、生成字幕，并合成为静态图片视频。

## 技术栈

- 后端：Flask + ffmpeg (subprocess)
- 字幕格式：ASS (Advanced SubStation Alpha)
- 视频编码：H.264 + AAC
- 前端：Vue 3 + Ant Design Vue

## 视频参数

### 宽高比选项

| 名称 | 分辨率 | 用途 |
|------|--------|------|
| 9:16 竖屏 | 1080x1920 | 抖音、快手短视频 |
| 16:9 横屏 | 1920x1080 | B站、YouTube |
| 1:1 方形 | 1080x1080 | Instagram |

### 字幕样式

- 位置：底部居中，距离底部 10%
- 字体：系统默认中文字体 (PingFang SC / Microsoft YaHei)
- 字号：根据视频高度自动计算（约为高度的 3%）
- 颜色：白色 (#FFFFFF)
- 背景：黑色半透明 (80% opacity)
- 描边：黑色 2px

## 工作流程

```
1. 用户在文本编辑页点击「生成视频」
2. 弹出配置对话框：
   - 选择宽高比
   - 上传背景图片
   - 配置语音参数（复用现有 TTS 设置）
3. 用户点击「生成」
4. 后端处理：
   a. 调用 TTS API 生成语音 WAV
   b. 生成 ASS 字幕文件（基于语音时间轴）
   c. 使用 ffmpeg 合成视频：
      - 输入：背景图片 + 语音 + ASS 字幕
      - 输出：MP4 视频
5. 返回视频文件供下载
```

## API 设计

### POST /api/video/generate

**请求：**
- Content-Type: multipart/form-data
- 参数：
  - `text_id`: 文本ID
  - `image`: 背景图片文件
  - `aspect_ratio`: 宽高比 (9:16, 16:9, 1:1)
  - `api_key`: TTS API Key
  - `voice_description`: 音色描述

**响应：**
- 成功：视频文件流 (video/mp4)
- 失败：JSON 错误信息

## ffmpeg 命令

```bash
ffmpeg -loop 1 -i background.jpg -i audio.wav \
  -vf "ass=subtitles.ass" \
  -c:v libx264 -tune stillimage -c:a aac \
  -b:a 192k -pix_fmt yuv420p \
  -shortest output.mp4
```

## ASS 字幕格式示例

```
[Script Info]
Title: 字幕工坊生成
ScriptType: v4.00+

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,BackColour,Bold,Italic,Alignment,MarginL,MarginR,MarginV
Style: Default,PingFang SC,48,&H00FFFFFF,&H80000000,-1,0,2,20,20,100

[Events]
Format: Layer,Start,End,Style,Text
Dialogue: 0,0:00:00.00,0:00:03.00,Default,这是第一段字幕
Dialogue: 0,0:00:03.00,0:00:06.00,Default,这是第二段字幕
```

## 依赖

### 系统依赖
- ffmpeg (需要安装)

### Python 依赖
- 无新增（使用现有 requests 库）

## 文件结构

### 新增文件
- `server/routes/video.py` — 视频生成 API
- `server/tests/test_video.py` — 视频生成测试
- `web/src/components/VideoGenerateModal.vue` — 视频生成对话框

### 修改文件
- `server/app.py` — 注册视频路由
- `web/src/views/TextEdit.vue` — 添加生成视频按钮
- `web/src/api/index.js` — 添加视频生成 API

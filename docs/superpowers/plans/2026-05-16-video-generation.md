# 视频生成功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现静态图片视频生成功能，用户上传图片后自动合成语音、字幕、视频

**Architecture:** 使用 ffmpeg 后端合成视频，ASS 格式字幕，复用现有 TTS 语音合成功能

**Tech Stack:** Python, Flask, ffmpeg (subprocess), ASS 字幕格式, Vue 3

---

## 文件结构

### 新增文件
- `server/routes/video.py` — 视频生成 API 路由
- `server/tests/test_video.py` — 视频生成测试
- `web/src/components/VideoGenerateModal.vue` — 视频生成对话框

### 修改文件
- `server/app.py` — 注册视频路由
- `web/src/views/TextEdit.vue` — 添加生成视频按钮
- `web/src/api/index.js` — 添加视频生成 API

---

### Task 1: ASS 字幕生成器

**Files:**
- Create: `server/routes/video.py`
- Create: `server/tests/test_video.py`

- [ ] **Step 1: 写失败的测试**

```python
# server/tests/test_video.py
import pytest
from server.routes.video import generate_ass_subtitle, get_resolution


def test_get_resolution_9_16():
    width, height = get_resolution('9:16')
    assert width == 1080
    assert height == 1920


def test_get_resolution_16_9():
    width, height = get_resolution('16:9')
    assert width == 1920
    assert height == 1080


def test_get_resolution_1_1():
    width, height = get_resolution('1:1')
    assert width == 1080
    assert height == 1080


def test_get_resolution_invalid():
    with pytest.raises(ValueError):
        get_resolution('invalid')


def test_generate_ass_subtitle():
    timeline = [
        {'start': 0.0, 'end': 3.0, 'text': '这是第一段字幕'},
        {'start': 3.0, 'end': 6.0, 'text': '这是第二段字幕'},
    ]
    ass_content = generate_ass_subtitle(timeline, 1920, 1080)

    assert '[Script Info]' in ass_content
    assert '[V4+ Styles]' in ass_content
    assert '[Events]' in ass_content
    assert '0:00:00.00' in ass_content
    assert '0:00:03.00' in ass_content
    assert '这是第一段字幕' in ass_content
    assert '这是第二段字幕' in ass_content


def test_generate_ass_subtitle_empty():
    ass_content = generate_ass_subtitle([], 1920, 1080)
    assert '[Script Info]' in ass_content
    assert 'Dialogue' not in ass_content
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /Users/ckrey/video/script && uv run pytest server/tests/test_video.py -v
```

- [ ] **Step 3: 实现 ASS 字幕生成器**

```python
# server/routes/video.py
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
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd /Users/ckrey/video/script && uv run pytest server/tests/test_video.py -v
```

- [ ] **Step 5: 提交**

```bash
git add server/routes/video.py server/tests/test_video.py
git commit -m "feat: add ASS subtitle generator for video"
```

---

### Task 2: ffmpeg 视频合成

**Files:**
- Modify: `server/routes/video.py`
- Modify: `server/tests/test_video.py`

- [ ] **Step 1: 写失败的测试**

在 `server/tests/test_video.py` 中添加：

```python
def test_generate_video_invalid_ratio():
    """测试无效宽高比"""
    with pytest.raises(ValueError):
        get_resolution('4:3')


def test_format_ass_timestamp():
    """测试 ASS 时间戳格式化"""
    from server.routes.video import _format_ass_timestamp
    assert _format_ass_timestamp(0) == '0:00:00.00'
    assert _format_ass_timestamp(61.5) == '0:01:01.50'
    assert _format_ass_timestamp(3661.123) == '1:01:01.12'
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /Users/ckrey/video/script && uv run pytest server/tests/test_video.py::test_format_ass_timestamp -v
```

- [ ] **Step 3: 实现 ffmpeg 视频合成**

在 `server/routes/video.py` 中添加：

```python
def check_ffmpeg():
    """检查 ffmpeg 是否可用。"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def generate_video(image_path, audio_path, ass_content, output_path, width, height):
    """使用 ffmpeg 合成视频。"""
    # 写入 ASS 字幕文件
    ass_path = output_path.replace('.mp4', '.ass')
    with open(ass_path, 'w', encoding='utf-8') as f:
        f.write(ass_content)

    # 构建 ffmpeg 命令
    cmd = [
        'ffmpeg', '-y',
        '-loop', '1',
        '-i', image_path,
        '-i', audio_path,
        '-vf', f'ass={ass_path}',
        '-c:v', 'libx264',
        '-tune', 'stillimage',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-pix_fmt', 'yuv420p',
        '-shortest',
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f'ffmpeg 错误: {result.stderr}')

    # 清理临时 ASS 文件
    if os.path.exists(ass_path):
        os.remove(ass_path)

    return output_path
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd /Users/ckrey/video/script && uv run pytest server/tests/test_video.py -v
```

- [ ] **Step 5: 提交**

```bash
git add server/routes/video.py server/tests/test_video.py
git commit -m "feat: add ffmpeg video generation function"
```

---

### Task 3: 视频生成 API

**Files:**
- Modify: `server/routes/video.py`
- Modify: `server/app.py`
- Modify: `server/tests/test_video.py`

- [ ] **Step 1: 写失败的测试**

在 `server/tests/test_video.py` 中添加：

```python
def test_video_generate_missing_params(client):
    """测试缺少参数"""
    response = client.post('/api/video/generate')
    assert response.status_code == 400


def test_video_generate_invalid_ratio(client):
    """测试无效宽高比"""
    response = client.post('/api/video/generate', data={
        'aspect_ratio': '4:3',
    })
    assert response.status_code == 400
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /Users/ckrey/video/script && uv run pytest server/tests/test_video.py::test_video_generate_missing_params -v
```

- [ ] **Step 3: 实现视频生成 API**

在 `server/routes/video.py` 末尾添加：

```python
@video_bp.route('/api/video/generate', methods=['POST'])
def generate():
    """生成静态图片视频。"""
    # 验证参数
    text_id = request.form.get('text_id')
    aspect_ratio = request.form.get('aspect_ratio', '9:16')
    api_key = request.form.get('api_key')
    voice_description = request.form.get('voice_description')

    if not text_id:
        return jsonify({'error': '缺少文本ID'}), 400
    if not api_key:
        return jsonify({'error': '缺少 API Key'}), 400
    if not voice_description:
        return jsonify({'error': '缺少音色描述'}), 400

    # 验证宽高比
    try:
        width, height = get_resolution(aspect_ratio)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    # 验证图片
    if 'image' not in request.files:
        return jsonify({'error': '请上传背景图片'}), 400

    image_file = request.files['image']
    if not image_file.filename:
        return jsonify({'error': '请上传背景图片'}), 400

    # 获取文本内容
    from server.models import Text
    text = Text.query.get(text_id)
    if not text:
        return jsonify({'error': '文本不存在'}), 404

    # 检查 ffmpeg
    if not check_ffmpeg():
        return jsonify({'error': '服务器未安装 ffmpeg'}), 500

    try:
        # 创建临时目录
        with tempfile.TemporaryDirectory() as tmpdir:
            # 保存图片
            image_ext = os.path.splitext(image_file.filename)[1] or '.jpg'
            image_path = os.path.join(tmpdir, f'background{image_ext}')
            image_file.save(image_path)

            # 调用 TTS 生成语音
            from server.routes.tts import _call_tts, _read_wav_info, _concat_wavs
            import base64

            # 将文本分段
            from splitter import split_text
            segments = split_text(text.content, max_chars=20)

            # 生成每段语音
            wav_infos = []
            timeline = []
            current_time = 0.0
            gap = 0.3

            for i, seg_text in enumerate(segments):
                audio_b64 = _call_tts(api_key, voice_description, seg_text)
                audio_bytes = base64.b64decode(audio_b64)
                wav_info = _read_wav_info(audio_bytes)
                duration = wav_info['frames'] / wav_info['framerate']

                wav_infos.append(wav_info)
                timeline.append({
                    'start': current_time,
                    'end': current_time + duration,
                    'text': seg_text,
                })
                current_time += duration + gap

            # 拼接音频
            full_audio = _concat_wavs(wav_infos, gap)
            audio_path = os.path.join(tmpdir, 'audio.wav')
            with open(audio_path, 'wb') as f:
                f.write(full_audio)

            # 生成 ASS 字幕
            ass_content = generate_ass_subtitle(timeline, width, height)

            # 生成视频
            output_path = os.path.join(tmpdir, 'output.mp4')
            generate_video(image_path, audio_path, ass_content, output_path, width, height)

            # 返回视频文件
            return send_file(
                output_path,
                mimetype='video/mp4',
                as_attachment=True,
                download_name=f'{text.title}.mp4',
            )

    except Exception as e:
        return jsonify({'error': f'生成视频失败: {str(e)}'}), 500
```

- [ ] **Step 4: 注册路由**

修改 `server/app.py`，添加：

```python
from server.routes.video import video_bp
app.register_blueprint(video_bp)
```

- [ ] **Step 5: 运行测试确认通过**

```bash
cd /Users/ckrey/video/script && uv run pytest server/tests/test_video.py -v
```

- [ ] **Step 6: 提交**

```bash
git add server/routes/video.py server/app.py server/tests/test_video.py
git commit -m "feat: add video generation API endpoint"
```

---

### Task 4: 前端 API 封装

**Files:**
- Modify: `web/src/api/index.js`

- [ ] **Step 1: 添加视频生成 API**

在 `web/src/api/index.js` 中添加：

```javascript
export const videoApi = {
  generate: (formData) => api.post('/video/generate', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    responseType: 'blob',
  }),
}
```

- [ ] **Step 2: 提交**

```bash
git add web/src/api/index.js
git commit -m "feat: add video generation API wrapper"
```

---

### Task 5: 视频生成对话框组件

**Files:**
- Create: `web/src/components/VideoGenerateModal.vue`

- [ ] **Step 1: 创建视频生成对话框**

```vue
<!-- web/src/components/VideoGenerateModal.vue -->
<template>
  <a-modal
    :open="open"
    title="生成视频"
    @update:open="$emit('update:open', $event)"
    :footer="null"
    width="500px"
  >
    <a-form layout="vertical">
      <a-form-item label="宽高比">
        <a-radio-group v-model:value="aspectRatio">
          <a-radio-button value="9:16">9:16 竖屏</a-radio-button>
          <a-radio-button value="16:9">16:9 横屏</a-radio-button>
          <a-radio-button value="1:1">1:1 方形</a-radio-button>
        </a-radio-group>
      </a-form-item>

      <a-form-item label="背景图片">
        <a-upload
          :before-upload="handleImageUpload"
          :show-upload-list="false"
          accept="image/*"
        >
          <a-button>
            <template #icon>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                <circle cx="8.5" cy="8.5" r="1.5"/>
                <polyline points="21 15 16 10 5 21"/>
              </svg>
            </template>
            选择图片
          </a-button>
        </a-upload>
        <div v-if="imageFile" class="image-preview">
          <span>{{ imageFile.name }}</span>
          <a-button type="link" size="small" @click="imageFile = null">移除</a-button>
        </div>
      </a-form-item>

      <a-form-item label="音色描述">
        <a-textarea
          v-model:value="voiceDescription"
          placeholder="描述你想要的音色..."
          :rows="2"
        />
      </a-form-item>

      <a-form-item>
        <a-button
          type="primary"
          :loading="generating"
          :disabled="!canGenerate"
          @click="handleGenerate"
          block
        >
          {{ generating ? '正在生成...' : '生成视频' }}
        </a-button>
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup>
import { ref, computed } from 'vue'
import { message } from 'ant-design-vue'
import { videoApi } from '../api'
import { useSettings } from '../stores/settings'

const props = defineProps({
  open: Boolean,
  textId: { type: Number, required: true },
  textTitle: { type: String, default: '视频' },
})

const emit = defineEmits(['update:open'])

const { llmKey } = useSettings()

const aspectRatio = ref('9:16')
const imageFile = ref(null)
const voiceDescription = ref('温柔的女性声音')
const generating = ref(false)

const canGenerate = computed(() => {
  return imageFile.value && voiceDescription.value && llmKey.value
})

const handleImageUpload = (file) => {
  imageFile.value = file
  return false
}

const handleGenerate = async () => {
  if (!llmKey.value) {
    message.error('请先配置 API Key')
    return
  }

  generating.value = true
  try {
    const formData = new FormData()
    formData.append('text_id', props.textId)
    formData.append('image', imageFile.value)
    formData.append('aspect_ratio', aspectRatio.value)
    formData.append('api_key', llmKey.value)
    formData.append('voice_description', voiceDescription.value)

    const response = await videoApi.generate(formData)

    // 下载视频
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.download = `${props.textTitle}.mp4`
    link.click()
    window.URL.revokeObjectURL(url)

    message.success('视频生成成功')
    emit('update:open', false)
  } catch (error) {
    message.error('视频生成失败')
    console.error(error)
  } finally {
    generating.value = false
  }
}
</script>

<style scoped>
.image-preview {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
  font-size: 13px;
}
</style>
```

- [ ] **Step 2: 提交**

```bash
git add web/src/components/VideoGenerateModal.vue
git commit -m "feat: add video generate modal component"
```

---

### Task 6: 集成到文本编辑页面

**Files:**
- Modify: `web/src/views/TextEdit.vue`

- [ ] **Step 1: 添加视频生成按钮**

在 `TextEdit.vue` 的 script 部分添加导入：

```javascript
import VideoGenerateModal from '../components/VideoGenerateModal.vue'
```

在 data 部分添加状态：

```javascript
const videoModalVisible = ref(false)
```

- [ ] **Step 2: 添加按钮到模板**

在导出按钮后面添加：

```vue
<a-button v-if="textId" @click="videoModalVisible = true" class="export-btn">
  <template #icon>
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <polygon points="23 7 16 12 23 17 23 7"/>
      <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
    </svg>
  </template>
  生成视频
</a-button>
```

在模板末尾添加对话框：

```vue
<VideoGenerateModal
  v-model:open="videoModalVisible"
  :textId="textId"
  :textTitle="title"
/>
```

- [ ] **Step 3: 验证功能**

启动前后端，访问文本编辑页面，确认：
- 生成视频按钮显示正常
- 点击按钮弹出对话框
- 对话框中可以配置参数

- [ ] **Step 4: 提交**

```bash
git add web/src/views/TextEdit.vue
git commit -m "feat: integrate video generation into text editor"
```

---

### Task 7: 端到端验证

- [ ] **Step 1: 运行所有后端测试**

```bash
cd /Users/ckrey/video/script && uv run pytest tests/ server/tests/ -v
```

- [ ] **Step 2: 验证完整工作流程**

1. 启动开发环境
2. 创建一篇文本
3. 点击「生成视频」按钮
4. 选择宽高比
5. 上传背景图片
6. 配置音色描述
7. 点击「生成视频」
8. 验证视频下载成功

- [ ] **Step 3: 最终提交**

```bash
cd /Users/ckrey/video/script && git add -A && git commit -m "chore: complete video generation feature"
```

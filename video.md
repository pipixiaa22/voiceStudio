使用文本设计音色进行语音合成
无需提供音频文件，只需在角色为 user 的消息中添加音色描述文本，即可生成定制化的语音音色。当前仅支持 mimo-v2.5-tts-voicedesign 模型。

如何写好音色描述（voice design prompt）
使用 mimo-v2.5-tts-voicedesign 模型时，user 消息中的文本就是音色设计描述。描述越具体、越生动，生成的音色越贴近预期。

关键维度
一条好的音色描述通常涵盖以下多个维度（不需要面面俱到）：

维度	示例
性别与年龄	"young woman in her mid-20s"、"五十多岁的中年男性"
音色/质感	"deep and gravelly"、"丝滑醇厚、带着磁性"
情绪/语气	"warm and confident"、"温柔但带着一丝疲惫"
语速/节奏	"slow and deliberate"、"语速极快，像连珠炮"
以下维度可选择性加入，增加丰富度：

角色/人设：narrator, podcast host, 评书先生, 深夜电台DJ

说话风格：casual and colloquial, 一本正经地, 压低嗓音像在密谋

场景描写：narrating a nature documentary, 在给投资人路演

年代参照：1940s film noir, 八十年代译制片配音

写法建议
简洁描述型 -- 用关键词或一句话快速勾勒声音轮廓

Heavy Russian accent, gruff middle-aged male, blunt and matter-of-fact.

专业描述型 -- 通过场景、人设或多维度细节立体刻画声音

Young female, extreme close-up with a binaural, ear-to-ear ASMR feel. Audible breathing, subtle swallowing, and soft natural lip sounds. She speaks very slowly, creating a deeply relaxing and immersive experience.

一位年迈的老先生，说带北方口音的普通话，语速缓慢而沉稳，嗓音略带沙哑和沧桑感，仿佛一位饱经风霜的老爷爷在讲故事，充满岁月的智慧。

注意事项
长度：1-4 句即可，不需要写长文。核心特征描述清楚比堆砌维度更重要

避免冲突：不要同时要求矛盾的特征（如"稚嫩的童声 + CEO气场"）

避免音质效果词：不要写混响、回声、EQ、压缩等后期处理相关描述

避免模糊词：不要用"普通的""正常的""外国的"等缺乏具体指向的描述

中英文均可：模型同时支持中英文音色描述，选择你最能精确表达的语言

合成文本要贴合音色：assistant 消息中的合成文本（text）应与音色描述相匹配，才能获得最佳效果。例如为"温柔治愈系女声"搭配一段晚安独白，而非一段激烈的体育解说。建议使用 LLM 根据你的音色描述自动生成适配的合成文本；在 Studio 页面上，输入音色描述后可直接点击「生成文本」按钮

调用示例
mimo-v2.5-tts-voicedesign 可通过可选参数 optimize_text_preview 控制是否对目标播报文本进行智能润色；设为 true 时，可无需传入 assistant 消息。

非流式调用
Curl

curl --location --request POST 'https://api.xiaomimimo.com/v1/chat/completions' \
--header "api-key: $MIMO_API_KEY" \
--header 'Content-Type: application/json' \
--data-raw '{
    "model": "mimo-v2.5-tts-voicedesign",
    "messages": [
        {
            "role": "user",
            "content": "Give me a young male tone."
        },
        {
            "role": "assistant",
            "content": "Yes, I had a sandwich."
        }
    ],
    "audio": {
        "format": "wav",
        "optimize_text_preview": true
    }
}'

Python

import os
from openai import OpenAI
import base64

client = OpenAI(
    api_key=os.environ.get("MIMO_API_KEY"),
    base_url="https://api.xiaomimimo.com/v1"
)

completion = client.chat.completions.create(
    model="mimo-v2.5-tts-voicedesign",
    messages=[
        {
            "role": "user",
            "content": "Give me a young male tone."
        },
        {
            "role": "assistant",
            "content": "Yes, I had a sandwich."
        }
    ],
    audio={
        "format": "wav",
        "optimize_text_preview": True
    }
)

message = completion.choices[0].message
audio_bytes = base64.b64decode(message.audio.data)
with open("audio_file.wav", "wb") as f:
    f.write(audio_bytes)
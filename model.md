curl --location --request POST 'BASE_URL/v1/messages' \
--header "api-key: $MIMO_API_KEY" \
--header "Content-Type: application/json" \
--data-raw '{
    "model": "mimo-v2.5-pro",
    "max_tokens": 1024,
    "system": "You are MiMo, an AI assistant developed by Xiaomi. Today is date: Tuesday, December 16, 2025. Your knowledge cutoff date is December 2024.",
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "please introduce yourself"
                }
            ]
        }
    ]
}'

Baseurl : https://token-plan-cn.xiaomimimo.com/anthropic


基础响应：
{
    "id": "b966dbcad38c48b59d16d8c1f313681b",
    "type": "message",
    "role": "assistant",
    "model": "mimo-v2.5-pro",
    "stop_reason": "end_turn",
    "content": [
        {
            "type": "text",
            "text": "Hello! I'm MiMo, an AI assistant developed by Xiaomi. I'm here to help answer your questions, provide information, or assist with various tasks. My knowledge is up to date until December 2024. How can I help you today?"
        }
    ],
    "usage": {
        "input_tokens": 57,
        "output_tokens": 54
    }
}
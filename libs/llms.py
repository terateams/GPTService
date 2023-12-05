import base64

from openai import OpenAI
import os


def openai_streaming(sysmsg, historys: list):
    """OpenAI Streaming API"""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    messages = [
        {"role": "system", "content": sysmsg},
    ]
    for history in historys:
        messages.append(history)
    print(messages)
    completion = client.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=messages,
        stream=True
    )
    for chunk in completion:
        yield chunk.choices[0].delta


# 定义函数来调用 OpenAI GPT-4 Vision API
def openai_analyze_image(prompt_str, imagefs):
    client = OpenAI()
    # 将图像转换为 Base64 编码，这里需要一些额外的处理
    # 假设已经将图像转换为 base64_string
    base64_string = base64.b64encode(imagefs.getvalue()).decode('utf-8')

    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_str or "分析图片内容"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/jpeg;base64," + base64_string,
                            "detail": "high"
                        },
                    },
                ],
            }
        ],
        max_tokens=300,
    )

    return response.choices[0].message.content

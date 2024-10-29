import jwt
from openai import AsyncAzureOpenAI
import os
import os


def validate_api_key(api_key, api_secret: str) -> bool:
    if api_key:
        try:
            payload = jwt.decode(api_key, api_secret, algorithms=['HS256'])
            uid = payload.get('uid')
            if uid in ["gptservice","teamstools","teamscode"]:
                return True
        except Exception as e:
            return False
    return False



def get_openai_client():
    return AsyncAzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_deployment=os.getenv("AZURE_OPENAI_MODEL_DEPLOYMENT_NAME"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    )

async def openai_async_text_generate(sysmsg, prompt, model: str) -> str:
    """OpenAI API"""
    client = get_openai_client()
    messages = [
        {"role": "system", "content": sysmsg},
        {"role": "user", "content": prompt},
    ]
    response = await client.chat.completions.create(
        model=model, messages=messages, stream=False
    )
    return response.choices[0].message.content


async def openai_async_json_generate(sysmsg, prompt, model: str) -> str:
    """OpenAI API"""
    client = get_openai_client()
    messages = [
        {"role": "system", "content": sysmsg},
        {"role": "user", "content": prompt},
    ]
    response = await client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=messages,
        stream=False
    )
    return response.choices[0].message.content


async def openai_analyze_image(prompt_str, model, imageb64, **kwargs):
    client = get_openai_client()
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_str or "分析图片内容"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/jpeg;base64," + imageb64,
                            "detail": "high",
                        },
                    },
                ],
            }
        ],
        max_tokens=2000,
        **kwargs
    )
    return response.choices[0].message.content


async def openai_agenerate_image(
    prompt: str,
    quality: str = "standard",
    size: str = "1024x1024",
    style: str = "vivid",
):
    client = get_openai_client()
    response = await client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size=size,
        quality=quality,
        style=style,
        n=1,
    )
    return [d.url for d in response.data]


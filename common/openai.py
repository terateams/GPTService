import asyncio
import logging
import tempfile
import uuid
import aiohttp
from openai import AsyncAzureOpenAI
import os

from common.azure_blob import generate_blob_rl_sas_url, upload_blobfile

log = logging.getLogger(__name__)


def get_openai_client():
    return AsyncAzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_deployment=os.getenv("AZURE_OPENAI_MODEL_DEPLOYMENT_NAME"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    )

def get_openai_imagine_client():
    return AsyncAzureOpenAI(
        azure_endpoint=os.getenv("IMAGINE_AZURE_OPENAI_ENDPOINT"),
        azure_deployment=os.getenv("IMAGINE_AZURE_OPENAI_MODEL_DEPLOYMENT_NAME"),
        api_key=os.getenv("IMAGINE_AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("IMAGINE_AZURE_OPENAI_API_VERSION"),
    )

async def openai_async_text_generate(sysmsg, prompt, model: str, temperature: float = 0.7, streaming: bool = False) -> str:
    """OpenAI API"""
    client = get_openai_client()
    messages = [
        {"role": "system", "content": sysmsg},
        {"role": "user", "content": prompt},
    ]
    response = await client.chat.completions.create(
        model=model, messages=messages, stream=streaming, temperature=temperature
    )
    if not streaming:
        return response.choices[0].message.content
    return response


async def openai_async_json_generate(sysmsg, prompt, model: str, schema: dict = None) -> str:
    """OpenAI API"""
    client = get_openai_client()
    messages = [
        {"role": "system", "content": sysmsg},
        {"role": "user", "content": prompt},
    ]
    json_schema = {
        "type": "json_schema",
        "json_schema": {
            "name": "math_response",
            "schema": schema,
        }
    }
    response = await client.chat.completions.create(
        model=model,
        response_format=json_schema if schema else {"type": "json_object"},
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
    container_name: str = "images",
    expiry_hours: int = 48,
):
    client = get_openai_imagine_client()
    try:
        response = await client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality=quality,
            style=style,
            n=1,
        )
    except Exception as e:
        raise RuntimeError(f"生成图片失败: {str(e)}")
    
    # 检查生成图片的状态
    if not response or not response.data:
        raise RuntimeError("生成图片失败: 未返回有效数据")
    
    # 获取生成的图片 URL
    image_urls = [d.url for d in response.data]
    
    log.info(f"openai gen image URLs: {image_urls}")
    
    # 上传到 Azure Blob 并返回 Blob URL
    blob_urls = []
    for image_url in image_urls:
        # 下载图片内容
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                image_content = await resp.read()
        
        # 使用临时文件保存图片内容
        temp_dir = tempfile.gettempdir()
        temp_filename = os.path.join(temp_dir, f"{uuid.uuid4()}.jpg")
        
        with open(temp_filename, "wb") as f:
            f.write(image_content)
        
        # 生成随机的 blob 名称
        blob_name = f"{uuid.uuid4()}.jpg"
        async def upload_images():
            try:
                await upload_blobfile(
                    container_name=container_name,
                    blob_name=blob_name,
                    filename=temp_filename,
                    overwrite=True,
                    expiry_hours=expiry_hours,
                )
            finally:
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)
        
        asyncio.create_task(upload_images())
        
        # 生成 Blob URL
        blob_url = generate_blob_rl_sas_url(
            container_name=container_name,
            blob_name=blob_name,
            expiry_hours=expiry_hours
        )
        blob_urls.append(blob_url)
    
    return blob_urls


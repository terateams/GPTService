import json
import re
import sys
import uuid

import aiofiles

from common.rediscache import RedisCache
from common.translate import get_translate

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

import logging
import os
from fastapi import FastAPI, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
from concurrent.futures import ProcessPoolExecutor
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
import asyncio

from common.redisrag import RedisRag, tokens_len



from common.utils import (
    md5hash,
    validate_api_key,
)
from common.openai import (
    openai_async_text_generate,
    openai_analyze_image,
    openai_agenerate_image,
)

log_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG") in ["1", "true"] else logging.INFO
)
log = logging.getLogger(__name__)
console_handler = logging.StreamHandler(sys.stderr)
console_handler.setFormatter(log_formatter)
log.addHandler(console_handler)

DATA_DIR = os.environ.get("DATA_DIR", "/home/data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


class LimitUploadSize(BaseHTTPMiddleware):
    """Limit the upload file size"""

    def __init__(self, app: ASGIApp, max_upload_size: int) -> None:
        super().__init__(app)
        self.max_upload_size = max_upload_size

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.method == "POST":
            if "content-length" not in request.headers:
                return Response(status_code=status.HTTP_411_LENGTH_REQUIRED)
            content_length = int(request.headers["content-length"])
            if content_length > self.max_upload_size:
                return Response(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        return await call_next(request)


app = FastAPI(
    title="GPTService API",
    description="gptservice api",
    version="1.0.0",
    servers=[
        {"url": os.environ.get("GPTS_API_SERVER"), "description": "Production server"},
        {"url": "http://0.0.0.0:8700", "description": "Develop server"},
    ],
)

app.add_middleware(LimitUploadSize, max_upload_size=1024 * 1024 * 100)

executor = ProcessPoolExecutor()

templates = Jinja2Templates(directory="templates")

cache = RedisCache(os.environ.get("REDIS_URL"))


async def run_in_process(fn, *args):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, fn, *args)


class TokenData(BaseModel):
    api_key: str


class RestResult(BaseModel):
    code: int = Field(
        0,
        title="Return code",
        description="The return code is 0 for success, and the other is for failure",
    )
    msg: str = Field(
        "success",
        title="Return the message",
        description="A message is returned, success is success, failure is a specific error message",
    )
    result: dict = Field(
        {},
        title="Return data (optional)",
        description="Return data (optional), textual content or structured data",
    )
    
    @staticmethod 
    def success(data: Any = None) -> Dict:
        return {
            "code": 0,
            "msg": "success",
            "data": data
        }
    
    @staticmethod
    def error(msg: str) -> Dict:
        return {
            "code": -1,
            "msg": msg
        }


API_SECRET = os.environ.get("API_SECRET")
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


def verify_api_key(api_key: str = Depends(api_key_header)):
    """Verify the API Key"""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key"
        )
    if len(api_key) < 8 or not validate_api_key(api_key[7:], API_SECRET):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key"
        )
    return TokenData(api_key=api_key)


@app.get("/", include_in_schema=False)
async def root():
    return "ok"


@app.get("/assets/{filename}", include_in_schema=False)
async def download_file(filename: str):
    if not re.match(r"^[\w,\s-]+\.[A-Za-z]{3}$", filename):
        raise HTTPException(status_code=400, detail="Invalid file name")

    # 构建文件完整路径
    file_path = os.path.join(DATA_DIR, filename)

    # 检查文件是否存在
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # 返回文件响应
    return FileResponse(file_path)


@app.get("/privacy", include_in_schema=False)
async def root(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})


class RagQuery(BaseModel):
    index: str
    query: str
    topk: int = 2


@app.api_route(
    "/api/knowledge/query",
    methods=["GET", "POST"],
    summary="query the knowledge base",
    description="query the knowledge base for relevant content",
)
async def redis_rag_search(
    query: RagQuery,
    td: TokenData = Depends(verify_api_key),
):
    """Search the knowledge base to return relevant content"""
    try:
        cachekey = f"rag_{md5hash(query.query)}"
        vdb = RedisRag.get_vectordb(query.index)
        result = await vdb.asimilarity_search_with_relevance_scores(
            query.query, k=query.topk, return_metadata=True
        )
        if not result:
            return RestResult(
                result={},
                code=200,
                msg="ok",
            )
        data = []
        for r in result:
            item = r[0].model_dump()
            item["score"] = r[1]
            data.append(item)

        datastr = json.dumps(data, ensure_ascii=False, indent=4)
        cache.set_cache(cachekey, datastr, expire=3600 * 24 * 365)
        source = f"{os.getenv('GPTS_API_SERVER')}/api/knowledge/cache/{cachekey}"
        return RestResult(
            code=0,
            msg="ok",
            result=dict(data=data, tokens=tokens_len(datastr), source_url=source),
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/api/knowledge/cache/{haskkey}",
    summary="query the knowledge cache byhash",
    description="query the knowledge cache by hash",
    include_in_schema=False,
)
async def redis_rag_cache(haskkey: str, request: Request):
    """fetch the knowledge cache by hash"""
    try:
        data = cache.get_cache(haskkey)
        if not data:
            return templates.TemplateResponse(
                "jsonviewer.html", {"request": request, "data": "cache not found"}
            )
        return templates.TemplateResponse(
            "jsonviewer.html", {"request": request, "data": data}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class TextGenerate(BaseModel):
    sysmsg: str = Field(
        ...,
        description="System message that provides context or instructions for the model's behavior.",
    )
    prompt: str = Field(
        ..., description="The user's input prompt that the model will respond to."
    )
    model: str = Field(
        "gpt-4o",
        description="The model name to be used for text generation. Defaults to 'gpt-4o'.",
    )
    temperature: Optional[float] = Field(0.7, description="The temperature")


@app.api_route(
    "/api/openai/text/generate",
    methods=["GET", "POST"],
    summary="query the knowledge base",
    description="openai text generate",
)
async def openai_text_generate_api(
    tg: TextGenerate,
    td: TokenData = Depends(verify_api_key),
):
    logging.info("openai_text_generate HTTP trigger function processed a request.")

    try:
        result = await openai_async_text_generate(tg.sysmsg, tg.prompt, tg.model)
        response = {"data": result, "tokens": tokens_len(result)}
        return RestResult(
            code=0,
            msg="ok",
            result=response,
        )
    except Exception as e:
        return RestResult(
            code=500,
            msg=str(e),
            result={},
        )


@app.post("/api/openai/text/streaming", response_description="OpenAI text generation")
async def openai_generate(
    request: TextGenerate, td: TokenData = Depends(verify_api_key)
):
    sysmsg = request.sysmsg
    prompt = request.prompt
    model = request.model
    temperature = round(request.temperature, 1)

    async def event_generator():
        try:
            stream_result = await openai_async_text_generate(
                sysmsg=sysmsg,
                prompt=prompt,
                model=model,
                streaming=True,
                temperature=temperature,
            )
            async for chunk in stream_result:
                if chunk.choices:
                    data = f"data: {chunk.choices[0].delta.model_dump_json()}\n\n"
                    yield data.encode("utf-8")
            # [DONE]
            yield f"data: [DONE]\n\n".encode("utf-8")
        except Exception as e:
            log.error(f"Error: {str(e)}")
            yield f"data: {str(e)}\n\n".encode("utf-8")

    return StreamingResponse(event_generator(), media_type="text/event-stream")


class ImageAnalyze(BaseModel):
    prompt: str = Field(
        ..., description="The user's input prompt that the model will respond to."
    )
    model: str = Field(
        "gpt-4o",
        description="The model name to be used for text generation. Defaults to 'gpt-4o'.",
    )
    imgb64: str = Field(..., description="The base64 encoded image data.")


@app.api_route(
    "/api/openai/image/analyze",
    methods=["POST"],
    summary="image analyze",
    description="image analyze by openai",
)
async def openai_analyze_image_api(
    req: ImageAnalyze,
    td: TokenData = Depends(verify_api_key),
):
    logging.info("openai_analyze_image HTTP trigger function processed a request.")
    try:
        result = await openai_analyze_image(req.prompt, req.model, req.imgb64)
        response = {"data": result, "tokens": tokens_len(result)}
        return RestResult(
            code=0,
            msg="ok",
            result=response,
        )
    except Exception as e:
        return RestResult(
            code=500,
            msg=str(e),
            result={},
        )


class ImageGenerate(BaseModel):
    prompt: str = Field(
        ..., description="The user's input prompt for generating an image."
    )
    quality: str = Field(
        "standard",
        description="The quality of the generated image. Defaults to 'standard'.",
    )
    size: str = Field(
        "1024x1024",
        description="The size of the generated image. Defaults to '1024x1024'.",
    )
    style: str = Field(
        "vivid",
        description="The style of the generated image. Defaults to 'vivid'.",
    )
    container_name: str = Field(
        "images",
        description="The Azure Blob container name where the image will be stored. Defaults to 'images'.",
    )
    expiry_hours: int = Field(
        24 * 365,
        description="The number of hours the image URL will be valid. Defaults to 48 hours.",
    )


@app.api_route(
    "/api/openai/image/generate",
    methods=["POST"],
    summary="image generate",
    description="generate an image using openai",
)
async def openai_generate_image_api(
    req: ImageGenerate,
    td: TokenData = Depends(verify_api_key),
):
    logging.info("openai_generate_image HTTP trigger function processed a request.")
    try:
        blob_urls = await openai_agenerate_image(
            prompt=req.prompt,
            quality=req.quality,
            size=req.size,
            style=req.style,
            container_name=req.container_name,
            expiry_hours=req.expiry_hours,
        )
        response = {"data": blob_urls}
        return RestResult(
            code=0,
            msg="ok",
            result=response,
        )
    except Exception as e:
        return RestResult(
            code=500,
            msg=str(e),
            result={},
        )


# 定义请求模型
class TokenRequest(BaseModel):
    content: str = Field("", description="The content to count tokens for")


@app.post(
    "/api/openai/stat/token",
    summary="Count tokens in content",
    description="Calculate the number of tokens in the provided content",
)
async def openai_stat_token(
    request: TokenRequest, td: TokenData = Depends(verify_api_key)
):
    try:
        length = tokens_len(request.content)
        return RestResult(code=0, msg="ok", result={"data": length})
    except Exception as e:
        return RestResult(code=500, msg=str(e), result={})


# 定义翻译请求模型
class TranslateRequest(BaseModel):
    text: str = Field(..., description="The text to translate")
    to: str = Field(..., description="The target language")

@app.post(
    "/api/azure/translate",
    summary="Translate text",
    description="Translate text to target language"
)
async def translate_text(
    request: TranslateRequest,
    td: TokenData = Depends(verify_api_key)
):
    try:
        translate = get_translate()
        target = await translate.translate_text(
            request.text, 
            request.to
        )
        return RestResult(
            code=0,
            msg="ok",
            result={"data": target}
        )
    except Exception as e:
        log.error(e)
        return RestResult(
            code=500, 
            msg=str(e),
            result={}
        )



@app.post(
    "/api/azure/translate/document",
    summary="Translate document",
    description="Translate uploaded document to target language"
)
async def translate_document(
    file: UploadFile = File(...),
    target_lang: str = Form(...),
    td: TokenData = Depends(verify_api_key)
) -> Dict:
    """
    翻译上传的文档
    
    Parameters:
        file: 要翻译的文件
        target_lang: 目标语言代码
        td: API token 验证
    """
    try:
        # 创建临时文件目录
        filedir = os.path.join(os.environ.get('DATA_DIR', '/tmp'), 'translate')
        os.makedirs(filedir, exist_ok=True)
        
        # 保存上传的文件
        doc_file = os.path.join(filedir, file.filename)
        size = 0
        
        async with aiofiles.open(doc_file, "wb") as f:
            while chunk := await file.read(8192):  # 每次读取8KB
                size += len(chunk)
                await f.write(chunk)
                
        if size == 0:
            raise HTTPException(
                status_code=400,
                detail="File is empty"
            )
            
        # 执行文档翻译
        translate = get_translate()
        docs = await translate.translate_documents(
            uuid.uuid4().hex,
            doc_file,
            target_lang
        )
        
        return RestResult.success(data=docs)
        
    except Exception as e:
        log.error(f"Document translation error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Translation failed: {str(e)}"
        )



if __name__ == "__main__":
    import uvicorn

    webport = int(os.environ.get("WEB_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=webport)

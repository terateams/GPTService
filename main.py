from dotenv import load_dotenv
import logging
import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

load_dotenv()

from libs.common import num_tokens_from_string
from libs.qdrant_index import qdrant


log = logging.getLogger(__name__)

DATA_DIR = os.environ.get("DATA_DIR", "/data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


class LimitUploadSize(BaseHTTPMiddleware):
    """限制上传文件大小"""

    def __init__(self, app: ASGIApp, max_upload_size: int) -> None:
        super().__init__(app)
        self.max_upload_size = max_upload_size

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method == 'POST':
            if 'content-length' not in request.headers:
                return Response(status_code=status.HTTP_411_LENGTH_REQUIRED)
            content_length = int(request.headers['content-length'])
            if content_length > self.max_upload_size:
                return Response(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        return await call_next(request)


app = FastAPI(
    title="GPTService API",
    description="gptservice api",
    version="1.0.0",
)
app.add_middleware(LimitUploadSize, max_upload_size=1024 * 1024 * 10)


class TokenData(BaseModel):
    api_key: str


class IndexItem(BaseModel):
    collection: str = Field("default", title="索引名称", description="索引名称")
    text: str = Field(title="文本内容", description="要向量化存储的文本内容")
    type: str = Field("text", title="文本类型", description="文本类型, text: 文本, webbase: 网页, webpdf: 网页PDF")
    url: str = Field("", title="网页地址", description="网页地址, 当type为webbase或webpdf时, 此项必填")
    separator: str = Field("\n\n", title="分隔符", description="分隔符, 处理文本时如何切分")
    chunk_size: int = Field(2000, title="切分大小", description="切分大小, 处理文本时每段的大小")
    chunk_overlap: int = Field(0, title="切分重叠", description="切分重叠, 处理文本时每段的重叠大小")


class IndexSearchItem(BaseModel):
    collection: str = Field("default", title="索引名称", description="知识库索引存储名称")
    query: str = Field(title="查询内容", description="查询文本内容")


class TokenItem(BaseModel):
    text: str = Field(title="文本内容", description="要向量化存储的文本内容")
    encoding: str = Field("cl100k_base", title="编码", description="编码, 默认为cl100k_base")


class RestResult(BaseModel):
    code: int = Field(0, title="返回码", description="返回码, 0为成功, 其他为失败")
    msg: str = Field("ok", title="返回消息", description="返回消息, 成功为ok, 失败为具体错误信息")
    result: dict = Field({}, title="返回数据(可选)", description="返回数据(可选), 文本内容或是结构化数据")


API_KEY = os.environ.get("API_KEY")
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


def verify_api_key(api_key: str = Depends(api_key_header)):
    """验证API Key"""
    if api_key is None or api_key == "" or len(api_key) < 8 or api_key[7:] != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")
    return TokenData(api_key=api_key)


@app.get("/")
async def root():
    return "ok"


@app.post("/token/stat")
async def token_stat(item: TokenItem, td: TokenData = Depends(verify_api_key)):
    """统计文本的token数量"""
    try:
        return dict(code=0, msg="ok", data=dict(
            encoding=item.encoding,
            length=num_tokens_from_string(item.text, item.encoding)
        ))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/knowledge/create")
async def create_index(item: IndexItem, td: TokenData = Depends(verify_api_key)):
    """创建知识库内容索引"""
    try:
        if item.type == "text":
            await qdrant.index_text(item.collection, item.text, item.chunk_size, item.chunk_overlap)
        elif item.type == "webbase":
            await qdrant.index_text_from_url(item.collection, item.url, item.chunk_size, item.chunk_overlap)
        elif item.type == "webpdf":
            await qdrant.index_pdf_from_path(item.collection, item.url, item.chunk_size, item.chunk_overlap)
    except Exception as e:
        log.error(f"create_index error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    return RestResult(code=0, msg="success")


@app.post("/knowledge/search", summary="搜索知识库", description="搜索知识库, 获取相关内容")
async def search_index(item: IndexSearchItem, td: TokenData = Depends(verify_api_key)):
    """搜索知识库，返回相关内容"""
    try:
        result = await qdrant.search(item.collection, item.query)
        return RestResult(code=0, msg="ok", result=dict(data=result))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    webport = int(os.environ.get("WEB_PORT", 8700))
    uvicorn.run(app, host="0.0.0.0", port=webport)

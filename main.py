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

from common import num_tokens_from_string
from qdrant_index import qdrant


log = logging.getLogger(__name__)

DATA_DIR = os.environ.get("DATA_DIR", "/data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


class LimitUploadSize(BaseHTTPMiddleware):
    """Limit the upload file size"""

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
    collection: str = Field("default", title="Collection name", description="Collection name")
    text: str = Field(title="Textual content", description="The stored text content to be vectorized")
    type: str = Field("text", title="The type of text",
                      description="Text type, text: text,webbase: web page, webpdf: web page pdf")
    url: str = Field("", title="Web page url",
                     description="Web address, which is required when type is webbase or webpdf")
    separator: str = Field("\n\n", title="Separator", description="Separators, how to cut text when it is processed")
    chunk_size: int = Field(2000, title="Slice size",
                            description="Split size, the size of each segment when processing text")
    chunk_overlap: int = Field(0, title="Split overlap",
                               description="Split overlap, the size of the overlap of each segment when processing text")


class IndexSearchItem(BaseModel):
    collection: str = Field("default", title="Collection name", description="The name of the knowledge base index store")
    query: str = Field(title="Query content", description="Query the text content of the knowledge base index store")


class TokenItem(BaseModel):
    text: str = Field(title="Text content", description="The stored text content to be vectorized")
    encoding: str = Field("cl100k_base", title="Encoding", description="Encoding, defaults cl100k_base")


class RestResult(BaseModel):
    code: int = Field(0, title="Return code",
                      description="The return code is 0 for success, and the other is for failure")
    msg: str = Field("success", title="Return the message",
                     description="A message is returned, success is success, failure is a specific error message")
    result: dict = Field({}, title="Return data (optional)",
                         description="Return data (optional), textual content or structured data")


API_KEY = os.environ.get("API_KEY")
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


def verify_api_key(api_key: str = Depends(api_key_header)):
    """Verify the API Key"""
    if api_key is None or api_key == "" or len(api_key) < 8 or api_key[7:] != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")
    return TokenData(api_key=api_key)


@app.get("/")
async def root():
    return "ok"


@app.post("/token/stat", summary="Count the number of tokens in the text",
          description="Count the number of tokens in the text")
async def token_stat(item: TokenItem, td: TokenData = Depends(verify_api_key)):
    """Count the number of tokens in the text"""
    try:
        return dict(code=0, msg="ok", data=dict(
            encoding=item.encoding,
            length=num_tokens_from_string(item.text, item.encoding)
        ))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/knowledge/create", summary="Create a knowledge base content index",
          description="Create a knowledge base content index")
async def create_index(item: IndexItem, td: TokenData = Depends(verify_api_key)):
    """Create a knowledge base content index"""
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


@app.post("/knowledge/search", summary="Search the knowledge base",
          description="Search the knowledge base for relevant content")
async def search_index(item: IndexSearchItem, td: TokenData = Depends(verify_api_key)):
    """Search the knowledge base to return relevant content"""
    try:
        result = await qdrant.search(item.collection, item.query)
        return RestResult(code=0, msg="ok", result=dict(data=result))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    webport = int(os.environ.get("WEB_PORT", 8700))
    uvicorn.run(app, host="0.0.0.0", port=webport)

from dotenv import load_dotenv
import logging
import os
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

load_dotenv()

from common import num_tokens_from_string, generate_api_key, validate_api_key
from qdrant_index import qdrant

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

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
    servers=[
        {"url": os.environ.get("GPTS_API_SERVER"), "description": "Production server"},
        {"url": "http://127.0.0.1:8700", "description": "Develop server"},
    ]
)

app.add_middleware(LimitUploadSize, max_upload_size=1024 * 1024 * 10)


class TokenData(BaseModel):
    api_key: str


class IndexItem(BaseModel):
    collection: str = Field("default", title="Collection name", description="Collection name")
    texts: list = Field([], title="Textual content list", description="The stored text content list to be vectorized")
    metadatas: list = Field([], title="Metadata list", description="Metadata list, structured data")
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
    collection: str = Field("default", title="Collection name",
                            description="The name of the knowledge base index store")
    query: str = Field(title="Query content", description="Query the text content of the knowledge base index store")


class IndexDeleteItem(BaseModel):
    collection: str = Field("not_exist", title="Collection name",
                            description="The name of the knowledge base index store")


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


API_SECRET = os.environ.get("API_SECRET")
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


def verify_api_key(api_key: str = Depends(api_key_header)):
    """Verify the API Key"""
    if api_key is None or api_key == "" or len(api_key) < 8 or not validate_api_key(api_key[7:], API_SECRET):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")
    return TokenData(api_key=api_key)


@app.get("/", include_in_schema=False)
async def root():
    return "ok"


@app.get("/privacy", response_class=HTMLResponse)
async def root():
    return """
    <html>
        <head>
            <title>Privacy Statement</title>
        </head>
        <body>
            <h1>Privacy Statement</h1>
            <p><strong>Respecting User Privacy:</strong> Our custom GPTS API service is committed to respecting user privacy. We do not collect or store any personal information from users.</p>
            <p><strong>Data Processing:</strong> Any data sent by users through the API is only used for processing specific requests and is immediately deleted from our systems upon completion.</p>
            <p><strong>Transparency:</strong> We promise to maintain transparency in our processing and will not use user data for any purpose other than request processing.</p>
            <p><strong>Security:</strong> We take all reasonable measures to ensure the security of user data and to prevent unauthorized access or disclosure.</p>
            <p><strong>Policy Changes:</strong> Any changes to this privacy policy will be updated on our website.</p>
            <p><strong>Contact Us:</strong> If you have any questions about our privacy policy, please contact us at <a href="mailto:jamiesun.net@gmail.com">jamiesun.net@gmail.com</a>.</p>
        </body>
    </html>
    """


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
        log.info(f"create_index: {item}")
        if item.type == "text":
            await qdrant.index_texts(item.collection, item.texts, item.metadatas, item.chunk_size, item.chunk_overlap)
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
        log.info(f"search_index: {item}")
        result = await qdrant.search(item.collection, item.query)
        return RestResult(code=0, msg="ok", result=dict(data=result))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/knowledge/list", summary="List the knowledge base",
         description="List the knowledge base")
async def list_index(td: TokenData = Depends(verify_api_key)):
    """Search the knowledge base to return relevant content"""
    try:
        result = await qdrant.list_index()
        return RestResult(code=0, msg="success", result=dict(data=result))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/knowledge/delete", include_in_schema=False)
async def delete_index(item: IndexDeleteItem, td: TokenData = Depends(verify_api_key)):
    """Search the knowledge base to return relevant content"""
    try:
        resp = await qdrant.delete(item.collection)
        return RestResult(code=0, msg="success", result=resp)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    webport = int(os.environ.get("WEB_PORT", 8700))
    uvicorn.run(app, host="0.0.0.0", port=webport)

import json
import re
import uuid
from typing import Dict, List, Optional

from dotenv import load_dotenv
import logging
import os
import shutil
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
import pytesseract
from PIL import Image, ImageFilter, ImageEnhance
from tempfile import NamedTemporaryFile
from fastapi import File, UploadFile
from fastapi.responses import JSONResponse
from graphviz import Digraph
from concurrent.futures import ProcessPoolExecutor
from fastapi import FastAPI, BackgroundTasks
from fastapi.templating import Jinja2Templates
import asyncio

load_dotenv()

from common import (num_tokens_from_string,
                    validate_api_key,
                    preprocess_image,
                    build_mind_map,
                    create_mindma_data_by_openai,
                    optimize_text_by_openai)
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

executor = ProcessPoolExecutor()

templates = Jinja2Templates(directory="templates")

async def run_in_process(fn, *args):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, fn, *args)


class TokenData(BaseModel):
    api_key: str


class IndexItem(BaseModel):
    collection: str = Field(..., title="Collection name", description="Collection name")
    texts: list = Field(..., title="Textual content list", description="The stored text content list to be vectorized")
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


class MindmapItem(BaseModel):
    title: str = Field(..., title="Mindmap Title as root node,required", description="Mindmap Title, Root node",
                       example="Python 学习")
    structure: Dict[str, List[str]] = Field(...,
                                            title="Mindmap Structure data, required",
                                            description="Mindmap Structure data, "
                                                        "The title value must be included in the structure's keys",
                                            example={
                                                "Python 学习": ["基础知识", "高级主题"],
                                                "基础知识": ["变量", "数据类型", "控制流"],
                                                "高级主题": ["面向对象", "装饰器", "迭代器"]
                                            })


class IndexSearchItem(BaseModel):
    collection: str = Field(..., title="Collection name",
                            description="The name of the knowledge base index store")
    query: str = Field(..., title="Query content", description="Query the text content of the knowledge base"
                                                               " index store")


class IndexDeleteItem(BaseModel):
    collection: str = Field(..., title="Collection name, required",
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


@app.get("/assets/{filename}", include_in_schema=False)
async def download_file(filename: str):
    if not re.match(r'^[\w,\s-]+\.[A-Za-z]{3}$', filename):
        raise HTTPException(status_code=400, detail="Invalid file name")

    # 构建文件完整路径
    file_path = os.path.join(DATA_DIR, filename)

    # 检查文件是否存在
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    # 返回文件响应
    return FileResponse(file_path)


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


@app.get("/knowledge/query", summary="query the knowledge base",
         description="query the knowledge base for relevant content")
async def search_index(
    collection: str = Query(..., description="The name of the collection to query"),
    query: str = Query(..., description="The query string to search for in the collection"),
    td: TokenData = Depends(verify_api_key)
):
    """Search the knowledge base to return relevant content"""
    try:
        log.info(f"search_index: collection={collection}, query={query}")
        result = await qdrant.search(collection, query)
        return RestResult(code=0, msg="ok", result=dict(data=result))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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


@app.post("/knowledge/imgocr", summary="Image OCR",
          description="Optical image content recognition")
async def create_image_ocr(file: UploadFile = File(...), td: TokenData = Depends(verify_api_key)):
    """Optical image content recognition"""
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only image uploads are permitted")
    with NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    try:
        img = Image.open(tmp_path)
        img = preprocess_image(img)
        custom_oem_psm_config = r'--oem 3 --psm 11'
        text = pytesseract.image_to_string(img, lang='chi_sim+eng', config=custom_oem_psm_config)
        text = optimize_text_by_openai(text)
        return JSONResponse(content={"filename": file.filename, "content": text})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp_path)


def create_mindmap_task(task):
    try:
        log.info(f"generate_mindmap params: {task['content']}")
        airesp = create_mindma_data_by_openai(task['content'])
        log.info(f"generate_mindmap result: {airesp}")
        # 创建并构建思维导图
        # 将 JSON 字符串转换为 Python 字典
        data = json.loads(airesp)
        # 使用 model_validate 方法创建 MindmapItem 实例
        item = MindmapItem.model_validate(data)
        graph = Digraph(comment=item.title, engine="sfdp")
        graph.attr(splines='compound')
        build_mind_map(graph, item.title, None, structure=item.structure)
        fileuuid = task["id"]
        output_path = os.path.join(DATA_DIR, fileuuid)
        graph.render(output_path, format='png', cleanup=True)
        # 生成 DOT 文件
        dot_path = output_path + ".dot"
        with open(dot_path, "w") as dot_file:
            dot_file.write(graph.source)
        task["status"] = "done"
        task["remark"] = "The task is completed, please access the URL information!"
        with open(os.path.join(DATA_DIR, f"{fileuuid}.json"), "w") as f:
            data = json.dumps(task)
            f.write(data)
    except Exception as e:
        import traceback
        traceback.print_exc()


@app.get("/knowledge/mindmap/task/add", summary="Create a mindmap generate task from content",
         description="Create a mindmap generate task from content")
async def generate_mindmap_task_add(background_tasks: BackgroundTasks, content: str = Query(...),
                                    td: bool = Depends(verify_api_key)):
    try:
        log.info(f"generate_mindmap_task_add params: {content}")
        server_url = os.environ.get("GPTS_API_SERVER")
        if server_url.endswith("/"):
            server_url = server_url[:-1]
        taskid = str(uuid.uuid4())
        task = dict(
            id=taskid,
            content=content,
            status="pending",
            image_url=f"{server_url}/assets/{taskid}.png",
            dot_url=f"{server_url}/assets/{taskid}.dot",
            viz_url=f"{server_url}/knowledge/mindmap/task/viz/{taskid}",
            status_url=f"{server_url}/knowledge/mindmap/task/result/view/{taskid}",
            remark="When working on a task, remember to save the URL information for later access! "
                   "You can display a link to the task status results to the user for later delayed access.",
        )
        with open(os.path.join(DATA_DIR, f"{taskid}.json"), "w") as f:
            data = json.dumps(task)
            f.write(data)
        background_tasks.add_task(create_mindmap_task, task)
        log.info(f"generate_mindmap_task_add result: {task}")
        return RestResult(code=0, msg="task add success", result=dict(data=task))
    except Exception as e:
        log.error(f"generate_mindmap error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/knowledge/mindmap/task/result/{taskid}", summary="Get the mindmap generate task result",
         description="Get the mindmap generate task result")
async def generate_mindmap_task_result(taskid: str):
    if not re.match(r'^[\w-]+$', taskid):
        raise HTTPException(status_code=400, detail="Invalid task ID format")

    file_path = os.path.join(DATA_DIR, f"{taskid}.json")
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    with open(file_path, "r") as f:
        data = json.load(f)
        return RestResult(code=0, msg="success", result=dict(data=data))


@app.get("/knowledge/mindmap/task/result/view/{taskid}", include_in_schema=False)
async def mindmap_task_result_view(request: Request, taskid: str):
    if not re.match(r'^[\w-]+$', taskid):
        raise HTTPException(status_code=400, detail="Invalid task ID format")

    file_path = os.path.join(DATA_DIR, f"{taskid}.json")
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    with open(file_path, "r") as f:
        data = json.load(f)
    return templates.TemplateResponse("gen_mindmap_result.html", {"request": request, "data": data})


@app.get("/knowledge/mindmap/task/viz/{taskid}", include_in_schema=False)
async def mindmap_vizview(request: Request, taskid: str):
    if not re.match(r'^[\w-]+$', taskid):
        raise HTTPException(status_code=400, detail="Invalid task ID format")

    file_path = os.path.join(DATA_DIR, f"{taskid}.dot")
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    with open(file_path, "r") as f:
        dot_data = {
            "dot_string": f.read()
        }
    return templates.TemplateResponse("graphviz_dot_view.html", {"request": request, "data": dot_data})


if __name__ == "__main__":
    import uvicorn

    webport = int(os.environ.get("WEB_PORT", 8700))
    uvicorn.run(app, host="0.0.0.0", port=webport)

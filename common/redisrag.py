from langchain_openai import ChatOpenAI as _ChatOpenAI
from langchain_openai import AzureChatOpenAI as _AzureChatOpenAI
from langchain_openai import OpenAIEmbeddings as _OpenAIEmbeddings
from langchain_openai import AzureOpenAIEmbeddings as _AzureOpenAIEmbeddings
from langchain_community.vectorstores import Redis
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.pgvector import PGVector
from langchain_unstructured import UnstructuredLoader
from langchain_community.document_loaders import UnstructuredPowerPointLoader
from langchain_community.document_loaders import UnstructuredExcelLoader
from langchain_community.document_loaders import MHTMLLoader
from langchain_community.document_loaders import UnstructuredODTLoader
from langchain_community.document_loaders import UnstructuredXMLLoader
from langchain_community.document_loaders import NotebookLoader
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.document_loaders.csv_loader import CSVLoader
from langchain_community.document_loaders import UnstructuredHTMLLoader
from langchain_community.document_loaders import JSONLoader
from langchain_community.document_loaders.chatgpt import ChatGPTLoader
from langchain_community.document_loaders import UnstructuredEmailLoader
from langchain_community.document_loaders import EverNoteLoader
from langchain_community.vectorstores.redis import Redis
from langchain_community.vectorstores.redis.base import check_index_exists
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    TextLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredMarkdownLoader,
    UnstructuredEPubLoader,
)
from typing import List
import os
import logging
import tiktoken

log = logging.getLogger(__name__)


def tokens_len(string: str) -> int:
    """
    计算字符串的令牌数。

    Args:
        string (str): 要计算令牌数的字符串。

    Returns:
        int: 字符串的令牌数。
    """
    encoding = tiktoken.get_encoding("cl100k_base")
    num_tokens = len(encoding.encode(string))
    return num_tokens


def get_loader_from_file(filepath: str):
    filetype = os.path.splitext(filepath)[1][1:].lower()
    if filetype in ["pdf"]:
        loader = PyMuPDFLoader(filepath)
    elif filetype in ["ppt", "pptx"]:
        loader = UnstructuredPowerPointLoader(filepath)
    elif filetype in ["xls", "xlsx"]:
        loader = UnstructuredExcelLoader(filepath)
    elif filetype in ["doc", "docx"]:
        loader = UnstructuredWordDocumentLoader(filepath)
    elif filetype in ["txt"]:
        loader = TextLoader(filepath)
    elif filetype in ["ipynb"]:
        loader = NotebookLoader(filepath)
    elif filetype in ["md"]:
        loader = UnstructuredMarkdownLoader(filepath)
        # loader = UnstructuredLoader(filepath)
    elif filetype in ["epub"]:
        loader = UnstructuredEPubLoader(filepath)
    elif filetype in ["csv"]:
        loader = CSVLoader(filepath)
    elif filetype in ["html", "htm"]:
        loader = UnstructuredHTMLLoader(filepath)
    elif os.path.basename(filepath).endswith("fake_conversations.json"):
        loader = ChatGPTLoader(filepath)
    elif os.path.basename(filepath).endswith("text_array.json"):
        loader = JSONLoader(filepath, jq_schema=".[]", text_content=True)
    elif filetype in ["json"]:
        loader = JSONLoader(
            filepath, jq_schema=".messages[].content", text_content=False
        )
    elif filetype in ["eml"]:
        loader = UnstructuredEmailLoader(filepath)
    elif filetype in ["enex"]:
        loader = EverNoteLoader(filepath)
    elif filetype in ["mht"]:
        loader = MHTMLLoader(filepath)
    elif filetype in ["xml"]:
        loader = UnstructuredXMLLoader(filepath)
    elif filetype in ["odt"]:
        loader = UnstructuredODTLoader(filepath)
    else:
        loader = UnstructuredLoader(filepath)
    print("-" * 100)
    print(filetype)
    print(type(loader))
    return loader


def OpenAIEmbeddings(**kwargs):
    if "OPENAI_API_BASE" in os.environ:
        del os.environ["OPENAI_API_BASE"]
    return _AzureOpenAIEmbeddings(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        deployment=os.environ.get("OPENAI_EMBEDDING_MODEL"),
        openai_api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),
        validate_base_url=False,
    )


def get_redis_retriever(indexname: str, topk: int = 3):
    """Create a Redis retriever from a indexname."""
    embedding_model = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
    rds = Redis(
        redis_url=os.environ["REDIS_URL"],
        index_name=indexname,
        embedding=OpenAIEmbeddings(model=embedding_model),
    )
    retriever = rds.as_retriever(
        search_type="mmr", search_kwargs={"k": topk, "fetch_k": 20}
    )
    if not check_index_exists(rds.client, indexname):
        Redis.from_texts(
            texts=["none"],
            redis_url=os.environ["REDIS_URL"],
            index_name=indexname,
            embedding=OpenAIEmbeddings(),
        )
    return retriever


class RedisRag(object):

    embedding_model = os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")

    @staticmethod
    def from_text(
        indexname: str, text: str, metadata: dict = None, splitlen: int = 1024
    ):
        """Create a Redis index from a text."""

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=splitlen, chunk_overlap=0, length_function=tokens_len
        )
        texts = text_splitter.split_text(text)
        return Redis.from_texts(
            texts,
            OpenAIEmbeddings(model=RedisRag.embedding_model),
            metadatas=metadata,
            redis_url=os.environ["REDIS_URL"],
            index_name=indexname,
        )

    @staticmethod
    def from_texts(
        indexname: str,
        texts: List[str],
        metadatas: List[dict] = None,
    ):
        """Create a Redis index from a list of texts."""
        return Redis.from_texts(
            texts,
            OpenAIEmbeddings(model=RedisRag.embedding_model),
            metadatas=metadatas,
            redis_url=os.environ["REDIS_URL"],
            index_name=indexname,
        )

    @staticmethod
    def from_files(
        indexname: str,
        filepaths: List[str],
        splitlen: int = 1024,
        metadatas: List[dict] = None,
    ):
        # sourcery skip: low-code-quality
        """
        Load and process documents from a list of filepaths.

        Args:
            indexname (str): The name of the index.
            filepaths (List[str]): A list of filepaths to load documents from.
            splitlen (int, optional): The length to split the documents into. Defaults to 1024.

        Returns:
            Redis: An instance of the Redis class containing the loaded documents.
        """
        docs = []
        for filepath in filepaths:
            loader = get_loader_from_file(filepath)
            docs.extend(loader.load())

        if metadatas:
            for doc in docs:
                if not doc.metadata:
                    doc.metadata = {}
                doc.metadata.update(metadatas.pop(0))

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=splitlen, chunk_overlap=0, length_function=tokens_len
        )
        spdocs = splitter.split_documents(docs)
        if not spdocs:
            raise ValueError("No documents were loaded from the provided filepaths.")

        return Redis.from_documents(
            spdocs,
            OpenAIEmbeddings(model=RedisRag.embedding_model),
            redis_url=os.environ["REDIS_URL"],
            index_name=indexname,
        )

    @staticmethod
    def get_vectordb(index_name=None):
        vector_schema = {
            "algorithm": "HNSW",
            "distance_metric": "cosine",
            "metadata_keys": ["blob_name", "blob_uri"],
        }
        return Redis(
            redis_url=os.environ["REDIS_URL"],
            index_name=index_name,
            vector_schema=vector_schema,
            embedding=OpenAIEmbeddings(model=RedisRag.embedding_model),
        )

    @staticmethod
    def drop_index(index_name=None):
        return Redis.drop_index(
            redis_url=os.environ["REDIS_URL"],
            index_name=index_name,
            delete_documents=True,
        )

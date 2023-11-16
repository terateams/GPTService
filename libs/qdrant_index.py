import os
from langchain.document_loaders import WebBaseLoader
from langchain.embeddings import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Qdrant
from langchain.document_loaders import PyMuPDFLoader
from .common import document_spliter_len
from qdrant_client import qdrant_client


class QdrantIndex(object):

    def __init__(self):
        self.qdrant_url = os.environ.get("QDRANT_URL")
        self.qdrant_grpc = os.environ.get("QDRANT_GRPC") in ["1", "true", "True", "TRUE"]

    async def search(self, collection, text, topk=3):
        client = qdrant_client.QdrantClient(
            url=self.qdrant_url, prefer_grpc=self.qdrant_grpc
        )
        embeddings = OpenAIEmbeddings()
        q = Qdrant(
            client=client, collection_name=collection,
            embeddings=embeddings,
        )
        result = await q.asimilarity_search_with_score(text, k=topk)
        data = []
        if result:
            for doc, score in result:
                data.append(dict(content=doc.page_content, metadata=doc.metadata, score=score))
        return data

    async def index_text_from_url(self, collection, url, chunk_size=100, chunk_overlap=0):
        loader = WebBaseLoader(url)
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size,
                                                       chunk_overlap=chunk_overlap,
                                                       length_function=document_spliter_len)
        docs = text_splitter.split_documents(documents)
        embeddings = OpenAIEmbeddings()
        await Qdrant.afrom_documents(
            docs, embeddings,
            url=self.qdrant_url,
            prefer_grpc=self.qdrant_grpc,
            collection_name=collection,
        )

    async def index_pdf_from_path(self, collection, pdffile, chunk_size=1000, chunk_overlap=0):
        loader = PyMuPDFLoader(pdffile)
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size,
                                                       chunk_overlap=chunk_overlap,
                                                       length_function=document_spliter_len)
        docs = text_splitter.split_documents(documents)
        embeddings = OpenAIEmbeddings()
        await Qdrant.afrom_documents(
            docs, embeddings,
            url=self.qdrant_url,
            prefer_grpc=self.qdrant_grpc,
            collection_name=collection,
        )

    async def index_text(self, collection, text, chunk_size=1000, chunk_overlap=0):
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=document_spliter_len
        )
        docs = text_splitter.create_documents([text])
        embeddings = OpenAIEmbeddings()
        await Qdrant.afrom_documents(
            docs, embeddings,
            url=self.qdrant_url,
            prefer_grpc=self.qdrant_grpc,
            collection_name=collection,
        )


qdrant = QdrantIndex()

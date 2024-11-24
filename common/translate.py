import asyncio
import base64
import logging
import time
from typing import List
import hashlib
import uuid
from azure.core.credentials import AzureKeyCredential
from azure.ai.translation.document.aio import DocumentTranslationClient
from azure.ai.translation.text.aio import TextTranslationClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.translation.text.models import InputTextItem
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.blob import generate_container_sas, BlobSasPermissions
from datetime import datetime, timedelta, timezone
from azure.storage.blob.aio import BlobClient
from azure.storage.blob.aio import ContainerClient
from common.utils import file_hash
from common.utils import disk_cache
from common.utils import parse_azureblob_account_info
import os

log = logging.getLogger(__name__)


class DocumentTranslation:
    def __init__(self):
        _conn_str = os.environ.get("AZURE_BLOB_CONNECT_STR")
        endpoint = os.environ.get("AZURE_DOCUMENT_TRANSLATION_ENDPOINT")
        api_key = os.environ.get("AZURE_DOCUMENT_TRANSLATION_KEY")
        region = os.environ.get("AZURE_TEXT_TRANSLATION_REGION")
        self.blob_service = BlobServiceClient.from_connection_string(conn_str=_conn_str)
        self.doc_translator = DocumentTranslationClient(
            endpoint, AzureKeyCredential(api_key)
        )
        credential = AzureKeyCredential(api_key)
        self.text_translator = TextTranslationClient(credential=credential, region=region, endpoint=endpoint, )

    @classmethod
    def get_instance(cls):
        if not hasattr(cls, "_instance"):
            cls._instance = DocumentTranslation()
        return cls._instance

    async def create_container(self, container_name):
        try:
            return await self.blob_service.create_container(container_name)
        except Exception as e:
            log.error(f"Error creating container {e}")
            return self.blob_service.get_container_client(container_name)

    def generate_sas(self, container, permission, expiry_hours):
        conn_str = os.environ.get("AZURE_BLOB_CONNECT_STR")
        account_name, account_key = parse_azureblob_account_info(conn_str)
        sas_blob = generate_container_sas(
            account_name=account_name,
            container_name=container.container_name,
            account_key=account_key,
            permission=permission,
            expiry=datetime.utcnow() + timedelta(hours=expiry_hours),
        )
        return sas_blob

    def generate_sas_url(self, container, permission, expiry_hours):
        conn_str = os.environ.get("AZURE_BLOB_CONNECT_STR")
        account_name, account_key = parse_azureblob_account_info(conn_str)
        sas_blob = self.generate_sas(container=container, permission=permission, expiry_hours=expiry_hours)
        return f"https://{account_name}.blob.core.windows.net/{container.container_name}?{sas_blob}"

    async def upload_file_in_chunks(self, blob_client, file_path, chunk_size=4 * 1024 * 1024):
        try:
            with open(file_path, 'rb') as file:
                file_size = os.path.getsize(file_path)
                chunks_count = file_size // chunk_size + (1 if file_size % chunk_size else 0)
                block_ids = []
                for i in range(chunks_count):
                    file_chunk = file.read(chunk_size)
                    block_id = base64.b64encode(str(i).encode()).decode('utf-8')
                    await blob_client.stage_block(block_id, file_chunk)
                    block_ids.append(block_id)
                await blob_client.commit_block_list(block_ids)
                return blob_client.url
        except Exception as e:
            raise
        

    async def upload_document(
        self,
        container_name: str,
        blob_name: str,
        filename: str,
        overwrite: bool = True,
        public_access: str = None,
    ):
        file_size = os.path.getsize(filename)
        chunk_size=4 * 1024 * 1024
        blob = self.blob_service.get_blob_client(container_name, blob_name)
        # 如果文件小于分块大小，进行普通上传
        if file_size <= chunk_size:
            with open(filename, 'rb') as data:
                await blob.upload_blob(data, overwrite=True)
            return blob.url
        else:
            # 进行分块上传
            return await self.upload_file_in_chunks(blob, filename, chunk_size)


    async def translate_documents(
        self, container: str, filename, target_language: str
    ):
        try:
            result_docs = []
            cache_key = file_hash(filename)
            file_result = disk_cache.get(cache_key)
            if file_result:
                result_docs.append(file_result)
                return result_docs
            
            src_container = await self.create_container(f"translate-{container}-source")
            dst_container = await self.create_container(f"translate-{container}-target")
            src_url = self.generate_sas_url(
                src_container,
                permission="rl",
                expiry_hours=1,
            )
            dst_url = self.generate_sas_url(
                dst_container,
                permission="wl",
                expiry_hours=1,
            )
            basename = os.path.basename(filename)
            print(f"start upload file {filename} to {src_container.container_name}/{basename}")
            await self.upload_document(
                src_container.container_name, basename, filename
            )
            print(f"start translation {src_url} to {dst_url}")
            poller = await self.doc_translator.begin_translation(
                src_url, dst_url, target_language, polling_interval=5
            )
            print(f"Status: {poller.status()}")
            result = await poller.result()
            
            sas = self.generate_sas(container=dst_container, permission="rl", expiry_hours=1)
            async for document in result:
                target_url = document.translated_document_url and document.translated_document_url + "?" +sas or "none"
                doc_result = dict(
                    target=target_url,
                    characters=document.characters_charged,
                    status=document.status,
                    error=repr(document.error),
                    timestamp=time.time()
                )
                result_docs.append(doc_result)
                disk_cache.set(cache_key, doc_result, expire=3600)
            return result_docs
        except Exception as e:
            import traceback
            traceback.print_exc()
            raise

    async def translate_text(self, srctext, target_language):
        input_text_elements = [InputTextItem(text=srctext)]
        response = await self.text_translator.translate(input_text_elements, to_language=[target_language])
        translation = response[0] if response else None
        return translation.translations[0].text

    async def clear_expired(self):
        async for c in self.blob_service.list_containers("translate"):
            now = datetime.now(timezone.utc)
            last_modified = c.last_modified.replace(tzinfo=timezone.utc)
            if now - last_modified > timedelta(hours=1):
                await self.blob_service.delete_container(c.name)
                log.info(f"Deleted container {c.name}")

if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv("../../.env")

    async def test_translate():
        dt = DocumentTranslation()
        # resp = await dt.translate_documents(
        #     uuid.uuid4().hex,
        #     "./assets/demo.txt",
        #     "zh-CN",
        # )
        # resp = await dt.translate_text("Hello World", "zh-CN")
        resp = await dt.clear_expired()
        print(resp)

    asyncio.run(test_translate())


def get_translate():
    return DocumentTranslation.get_instance()

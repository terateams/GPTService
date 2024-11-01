import asyncio
from datetime import datetime, timedelta, UTC
import tempfile
import uuid
from azure.storage.blob.aio import BlobServiceClient
from azure.storage.blob.aio import BlobClient
from azure.storage.blob.aio import ContainerClient
from azure.storage.blob import generate_blob_sas
import os


def parse_account_info(conn_str: str = None):
    # 获取连接字符串
    _conn_str = conn_str or os.environ.get("AZURE_BLOB_CONNECT_STR")
    # 将连接字符串分割为各个部分
    parts = _conn_str.split(";")
    # 提取 AccountName 和 AccountKey
    account_info = {}
    for part in parts:
        if "AccountName=" in part:
            account_info["AccountName"] = part.split("=", 1)[1]
        elif "AccountKey=" in part:
            account_info["AccountKey"] = part.split("=", 1)[1]

    return account_info["AccountName"], account_info["AccountKey"]


def get_blob_service(conn_str: str = None):
    _conn_str = conn_str or os.environ.get("AZURE_BLOB_CONNECT_STR")
    return BlobServiceClient.from_connection_string(conn_str=_conn_str)


def generate_blob_rl_sas(container_name, blob_name, permission, expiry_hours):
    _conn_str = os.environ.get("AZURE_BLOB_CONNECT_STR")
    account_name, account_key = parse_account_info(_conn_str)
    sas_blob = generate_blob_sas(
        account_name=account_name,
        blob_name=blob_name,
        container_name=container_name,
        account_key=account_key,
        permission=permission,
        expiry=datetime.now(UTC) + timedelta(hours=expiry_hours),
    )
    return sas_blob


def generate_blob_rl_sas_url(container_name, blob_name, expiry_hours):
    _conn_str = os.environ.get("AZURE_BLOB_CONNECT_STR")
    account_name, account_key = parse_account_info(_conn_str)
    sas_blob = generate_blob_rl_sas(
        container_name,
        blob_name=blob_name,
        permission="rl",
        expiry_hours=expiry_hours,
    )
    return f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_blob}"


async def upload_blob_text(
    container_name: str,
    blob_name: str,
    content: str,
    overwrite: bool = True,
    public_access: str = None,
    expiry_hours: int = 48,
):
    # 使用临时文件和随机文件名
    temp_dir = tempfile.gettempdir()
    temp_filename = os.path.join(temp_dir, f"{uuid.uuid4()}.txt")

    try:
        with open(temp_filename, "w", encoding="utf-8") as f:
            f.write(content)
        await upload_blobfile(
            container_name,
            blob_name,
            temp_filename,
            overwrite,
            public_access,
            expiry_hours=expiry_hours,
        )
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)


async def upload_blobfile(
    container_name: str,
    blob_name: str,
    filename: str,
    overwrite: bool = True,
    public_access: str = None,
    expiry_hours: int = 48,
):
    service = get_blob_service()
    container_client = service.get_container_client(container_name)
    try:
        if not await container_client.exists():
            res = await service.create_container(
                container_name, public_access=public_access
            )
            print(res)

        blob = container_client.get_blob_client(blob_name)
        with open(filename, "rb") as data:
            resp = await blob.upload_blob(data=data, overwrite=True)
            url = blob.url
            if not public_access:
                url = (
                    url
                    + "?"
                    + generate_blob_rl_sas(
                        container_client.container_name,
                        blob_name=blob_name,
                        permission="r",
                        expiry_hours=expiry_hours,
                    )
                )
                return url
            return url
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise
    finally:
        await container_client.close()
        await service.close()


async def download_blobfile(container_name: str, blob_name: str, filename: str):
    service = get_blob_service()
    try:
        bc = service.get_blob_client(container_name, blob_name)
        with open(filename, "wb") as my_blob:
            stream = await bc.download_blob()
            data = await stream.readall()
            my_blob.write(data)
    finally:
        await service.close()


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv("../../.env")

    async def test_upload():
        bs = get_blob_service()
        resp = await upload_blobfile(
            "test-1", "test.txt", __file__, public_access="blob"
        )
        print(resp)
        con = bs.get_container_client("test-1")
        await con.close()
        await bs.close()

    async def test_download():
        await download_blobfile("test-1", "test.txt", "test11111.txt")

    asyncio.run(test_upload())
    asyncio.run(test_download())

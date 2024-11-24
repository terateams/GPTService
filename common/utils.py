import logging
import jwt
import diskcache as dc
import os
import hashlib



log = logging.getLogger(__name__)


_cache_dir = os.path.join(os.environ.get('DATA_DIR', '/tmp'), "cache")
if not os.path.exists(_cache_dir):
    os.makedirs(_cache_dir)

disk_cache = dc.Cache(_cache_dir)
mem_cache = dc.FanoutCache(
    directory=_cache_dir,  # 磁盘缓存目录
    shards=32,               # 分片数，用于提高并发性能
    size_limit=100 * 10**6           # 内存缓存大小限制，这里设置为100M
)


def md5hash(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()

    
def file_hash(filepath: str) -> str:
    with open(filepath, 'rb') as file:
        hash_object = hashlib.md5()
        for chunk in iter(lambda: file.read(4096), b''):
            hash_object.update(chunk)
    return hash_object.hexdigest()


def validate_api_key(api_key, api_secret: str) -> bool:
    if api_key:
        try:
            payload = jwt.decode(api_key, api_secret, algorithms=['HS256'])
            uid = payload.get('uid')
            if uid in ["gptservice","teamstools","teamscode"]:
                return True
        except Exception as e:
            return False
    return False

def parse_azureblob_account_info(conn_str: str = None):
    # 获取连接字符串
    # 将连接字符串分割为各个部分
    parts = conn_str.split(";")
    # 提取 AccountName 和 AccountKey
    account_info = {}
    for part in parts:
        if "AccountName=" in part:
            account_info["AccountName"] = part.split("=", 1)[1]
        elif "AccountKey=" in part:
            account_info["AccountKey"] = part.split("=", 1)[1]

    return account_info["AccountName"], account_info["AccountKey"]


def get_global_datadir(subpath: str = None):
    """
    获取全局数据目录。

    Args:
        subpath (str, optional): 子路径。默认为None。

    Returns:
        str: 数据目录路径。
    """
    datadir = os.environ.get("DATA_DIR", "/tmp/teamsgpt")
    if subpath:
        datadir = os.path.join(datadir, subpath)
    if not os.path.exists(datadir):
        os.makedirs(datadir)
    return datadir
    


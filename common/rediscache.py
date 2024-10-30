import redis
import json
from typing import Optional

class RedisCache:
    def __init__(self, url: str, db: int = 0):
        """
        使用连接 URL 初始化 Redis 客户端连接
        :param url: Redis 连接 URL
        :param db: Redis 数据库编号，默认为 0
        """
        self.client = redis.Redis.from_url(url, db=db)

    def set_cache(self, key: str, value, expire: Optional[int] = None) -> bool:
        """
        设置缓存
        :param key: 缓存键
        :param value: 缓存值，可以是任意数据类型，将被转换为 JSON 字符串
        :param expire: 过期时间，单位为秒。若为 None，则永久有效
        :return: 成功返回 True，失败返回 False
        """
        try:
            value_json = json.dumps(value)  # 将值转换为 JSON 字符串
            self.client.set(name=key, value=value_json, ex=expire)
            return True
        except Exception as e:
            print(f"Error setting cache: {e}")
            return False

    def get_cache(self, key: str):
        """
        获取缓存
        :param key: 缓存键
        :return: 返回原始数据类型的值，如果键不存在则返回 None
        """
        try:
            value = self.client.get(name=key)
            if value is not None:
                return json.loads(value)  # 将 JSON 字符串转换回原始数据类型
            return None
        except Exception as e:
            print(f"Error getting cache: {e}")
            return None

    def delete_cache(self, key: str) -> bool:
        """
        删除缓存
        :param key: 缓存键
        :return: 成功删除返回 True，否则返回 False
        """
        try:
            return self.client.delete(key) == 1
        except Exception as e:
            print(f"Error deleting cache: {e}")
            return False

    def clear_cache(self) -> bool:
        """
        清空 Redis 数据库中的所有缓存
        :return: 成功清空返回 True，否则返回 False
        """
        try:
            self.client.flushdb()
            return True
        except Exception as e:
            print(f"Error clearing cache: {e}")
            return False
"""
Redis缓存服务
"""
import os
import sys
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta

import redis
from redis.asyncio import Redis as AsyncRedis
from redis import Redis as SyncRedis
import pickle
import base64

# 添加共享模块路径
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from shared.utils.helpers import get_current_time

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Redis配置
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_MAX_CONNECTIONS = int(os.getenv("REDIS_MAX_CONNECTIONS", 10))

# 缓存配置
CACHE_DEFAULT_TTL = int(os.getenv("CACHE_DEFAULT_TTL", 3600))  # 默认1小时
CACHE_USER_SESSION_TTL = int(os.getenv("CACHE_USER_SESSION_TTL", 86400))  # 用户会话24小时
CACHE_TASK_RESULT_TTL = int(os.getenv("CACHE_TASK_RESULT_TTL", 604800))  # 任务结果7天
CACHE_MODEL_INFO_TTL = int(os.getenv("CACHE_MODEL_INFO_TTL", 3600))  # 模型信息1小时
CACHE_API_RESPONSE_TTL = int(os.getenv("CACHE_API_RESPONSE_TTL", 300))  # API响应5分钟


class RedisCacheService:
    """Redis缓存服务"""
    
    def __init__(self):
        self._async_client = None
        self._sync_client = None
        self._connection_pool = None
    
    async def get_async_client(self) -> AsyncRedis:
        """获取异步Redis客户端"""
        if self._async_client is None:
            self._async_client = AsyncRedis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                db=REDIS_DB,
                max_connections=REDIS_MAX_CONNECTIONS,
                decode_responses=False  # 使用二进制模式，支持pickle
            )
        return self._async_client
    
    def get_sync_client(self) -> SyncRedis:
        """获取同步Redis客户端"""
        if self._sync_client is None:
            self._sync_client = SyncRedis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                db=REDIS_DB,
                max_connections=REDIS_MAX_CONNECTIONS,
                decode_responses=False  # 使用二进制模式，支持pickle
            )
        return self._sync_client
    
    def _serialize(self, data: Any) -> bytes:
        """序列化数据"""
        try:
            # 尝试使用pickle序列化
            return pickle.dumps(data)
        except Exception as e:
            logger.error(f"序列化数据失败: {str(e)}")
            # 如果pickle失败，尝试JSON序列化
            try:
                return json.dumps(data, ensure_ascii=False).encode('utf-8')
            except Exception as e2:
                logger.error(f"JSON序列化也失败: {str(e2)}")
                raise
    
    def _deserialize(self, data: bytes) -> Any:
        """反序列化数据"""
        try:
            # 尝试使用pickle反序列化
            return pickle.loads(data)
        except Exception as e:
            logger.error(f"pickle反序列化失败: {str(e)}")
            # 如果pickle失败，尝试JSON反序列化
            try:
                return json.loads(data.decode('utf-8'))
            except Exception as e2:
                logger.error(f"JSON反序列化也失败: {str(e2)}")
                raise
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: int = CACHE_DEFAULT_TTL
    ) -> bool:
        """设置缓存"""
        try:
            client = await self.get_async_client()
            serialized_value = self._serialize(value)
            result = await client.setex(key, ttl, serialized_value)
            return result
        except Exception as e:
            logger.error(f"设置缓存失败: {str(e)}")
            return False
    
    async def get(self, key: str) -> Any:
        """获取缓存"""
        try:
            client = await self.get_async_client()
            value = await client.get(key)
            if value is None:
                return None
            return self._deserialize(value)
        except Exception as e:
            logger.error(f"获取缓存失败: {str(e)}")
            return None
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        try:
            client = await self.get_async_client()
            result = await client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"删除缓存失败: {str(e)}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        try:
            client = await self.get_async_client()
            result = await client.exists(key)
            return result > 0
        except Exception as e:
            logger.error(f"检查缓存存在性失败: {str(e)}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """设置缓存过期时间"""
        try:
            client = await self.get_async_client()
            result = await client.expire(key, ttl)
            return result
        except Exception as e:
            logger.error(f"设置缓存过期时间失败: {str(e)}")
            return False
    
    async def ttl(self, key: str) -> int:
        """获取缓存剩余时间"""
        try:
            client = await self.get_async_client()
            result = await client.ttl(key)
            return result
        except Exception as e:
            logger.error(f"获取缓存剩余时间失败: {str(e)}")
            return -1
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """获取匹配模式的所有键"""
        try:
            client = await self.get_async_client()
            keys = await client.keys(pattern)
            return [key.decode('utf-8') if isinstance(key, bytes) else key for key in keys]
        except Exception as e:
            logger.error(f"获取键列表失败: {str(e)}")
            return []
    
    async def flushdb(self) -> bool:
        """清空当前数据库"""
        try:
            client = await self.get_async_client()
            result = await client.flushdb()
            return result
        except Exception as e:
            logger.error(f"清空数据库失败: {str(e)}")
            return False
    
    async def close(self):
        """关闭连接"""
        if self._async_client:
            await self._async_client.close()
        if self._sync_client:
            self._sync_client.close()


# 创建全局缓存服务实例
cache_service = RedisCacheService()


# 缓存装饰器
def cache_result(key_prefix: str, ttl: int = CACHE_DEFAULT_TTL):
    """缓存结果装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # 尝试从缓存获取结果
            cached_result = await cache_service.get(cache_key)
            if cached_result is not None:
                logger.info(f"从缓存获取结果: {cache_key}")
                return cached_result
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 将结果存入缓存
            await cache_service.set(cache_key, result, ttl)
            logger.info(f"结果已缓存: {cache_key}")
            
            return result
        return wrapper
    return decorator


# 用户会话缓存
class UserSessionCache:
    """用户会话缓存"""
    
    @staticmethod
    async def set_session(user_id: int, session_data: Dict[str, Any]) -> bool:
        """设置用户会话"""
        key = f"user:session:{user_id}"
        return await cache_service.set(key, session_data, CACHE_USER_SESSION_TTL)
    
    @staticmethod
    async def get_session(user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户会话"""
        key = f"user:session:{user_id}"
        return await cache_service.get(key)
    
    @staticmethod
    async def delete_session(user_id: int) -> bool:
        """删除用户会话"""
        key = f"user:session:{user_id}"
        return await cache_service.delete(key)
    
    @staticmethod
    async def refresh_session(user_id: int) -> bool:
        """刷新用户会话过期时间"""
        key = f"user:session:{user_id}"
        return await cache_service.expire(key, CACHE_USER_SESSION_TTL)


# 任务结果缓存
class TaskResultCache:
    """任务结果缓存"""
    
    @staticmethod
    async def set_result(task_id: str, result_data: Dict[str, Any]) -> bool:
        """设置任务结果"""
        key = f"task:result:{task_id}"
        return await cache_service.set(key, result_data, CACHE_TASK_RESULT_TTL)
    
    @staticmethod
    async def get_result(task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务结果"""
        key = f"task:result:{task_id}"
        return await cache_service.get(key)
    
    @staticmethod
    async def delete_result(task_id: str) -> bool:
        """删除任务结果"""
        key = f"task:result:{task_id}"
        return await cache_service.delete(key)


# 模型信息缓存
class ModelInfoCache:
    """模型信息缓存"""
    
    @staticmethod
    async def set_model_info(model_id: str, model_data: Dict[str, Any]) -> bool:
        """设置模型信息"""
        key = f"model:info:{model_id}"
        return await cache_service.set(key, model_data, CACHE_MODEL_INFO_TTL)
    
    @staticmethod
    async def get_model_info(model_id: str) -> Optional[Dict[str, Any]]:
        """获取模型信息"""
        key = f"model:info:{model_id}"
        return await cache_service.get(key)
    
    @staticmethod
    async def delete_model_info(model_id: str) -> bool:
        """删除模型信息"""
        key = f"model:info:{model_id}"
        return await cache_service.delete(key)
    
    @staticmethod
    async def set_model_list(model_list: List[Dict[str, Any]]) -> bool:
        """设置模型列表"""
        key = "model:list"
        return await cache_service.set(key, model_list, CACHE_MODEL_INFO_TTL)
    
    @staticmethod
    async def get_model_list() -> Optional[List[Dict[str, Any]]]:
        """获取模型列表"""
        key = "model:list"
        return await cache_service.get(key)


# API响应缓存
class APIResponseCache:
    """API响应缓存"""
    
    @staticmethod
    async def set_response(endpoint: str, params: Dict[str, Any], response_data: Dict[str, Any]) -> bool:
        """设置API响应"""
        # 生成缓存键
        param_str = json.dumps(params, sort_keys=True)
        key = f"api:response:{endpoint}:{hash(param_str)}"
        return await cache_service.set(key, response_data, CACHE_API_RESPONSE_TTL)
    
    @staticmethod
    async def get_response(endpoint: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """获取API响应"""
        # 生成缓存键
        param_str = json.dumps(params, sort_keys=True)
        key = f"api:response:{endpoint}:{hash(param_str)}"
        return await cache_service.get(key)


# 分布式锁
class DistributedLock:
    """分布式锁"""
    
    def __init__(self, key: str, timeout: int = 10, retry_delay: float = 0.1):
        self.key = f"lock:{key}"
        self.timeout = timeout
        self.retry_delay = retry_delay
        self.identifier = f"{get_current_time().timestamp()}:{os.getpid()}"
    
    async def acquire(self) -> bool:
        """获取锁"""
        try:
            client = await cache_service.get_async_client()
            # 使用SET命令的NX和EX选项实现原子性获取锁
            result = await client.set(self.key, self.identifier, ex=self.timeout, nx=True)
            return result
        except Exception as e:
            logger.error(f"获取分布式锁失败: {str(e)}")
            return False
    
    async def release(self) -> bool:
        """释放锁"""
        try:
            client = await cache_service.get_async_client()
            # 使用Lua脚本确保只有锁的持有者才能释放锁
            lua_script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            result = await client.eval(lua_script, 1, self.key, self.identifier)
            return result > 0
        except Exception as e:
            logger.error(f"释放分布式锁失败: {str(e)}")
            return False
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        while not await self.acquire():
            await asyncio.sleep(self.retry_delay)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.release()


# 限流器
class RateLimiter:
    """限流器"""
    
    def __init__(self, key: str, limit: int, window: int):
        self.key = f"rate_limit:{key}"
        self.limit = limit
        self.window = window
    
    async def is_allowed(self) -> bool:
        """检查是否允许请求"""
        try:
            client = await cache_service.get_async_client()
            now = get_current_time().timestamp()
            window_start = now - self.window
            
            # 使用Lua脚本实现滑动窗口限流
            lua_script = """
            local key = KEYS[1]
            local now = tonumber(ARGV[1])
            local window = tonumber(ARGV[2])
            local limit = tonumber(ARGV[3])
            local window_start = now - window
            
            -- 清理过期的请求记录
            redis.call('zremrangebyscore', key, 0, window_start)
            
            -- 获取当前窗口内的请求数量
            local current = redis.call('zcard', key)
            
            -- 检查是否超过限制
            if current < limit then
                -- 添加当前请求记录
                redis.call('zadd', key, now, now)
                redis.call('expire', key, window)
                return 1
            else
                return 0
            end
            """
            
            result = await client.eval(lua_script, 1, self.key, str(now), str(self.window), str(self.limit))
            return result > 0
        except Exception as e:
            logger.error(f"限流检查失败: {str(e)}")
            # 如果限流检查失败，默认允许请求
            return True


# 导入asyncio
import asyncio
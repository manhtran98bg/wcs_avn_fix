from common import MODULE_NAME

from rostek_utils.utils.logger import Logger
import redis
import redis.client
from typing import Type, Callable
import json

class RedisHandler:
    """
    Handle redis database

    Database form:
    - As dict:
        - topic (hash name): {key: value}
    - As list:
        - topic: [values]
    """
    def __init__(self):
        self.__redis: redis.Redis = None

    def connect(self, **kwargs):
        """
        Kwargs:
            host: (str) redis server ip = "localhost"
            port: (int) redis server port = 6379
            db: (int) database segment index = 0
            password: (str) database password = None
        """
        self.__redis = redis.Redis(
            **kwargs,
            decode_responses=True  # Automatically decode responses to Python strings
        )
    
    @staticmethod
    def __handleConnectException(func: Callable):
        def inner(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                Logger(MODULE_NAME.REDIS).error(f"Handel redis error: {e}")
        return inner
    
    @__handleConnectException
    def remove(self, *topics):
        """
        Delete multiple topics
        """
        self.__redis.delete(*map(self.__genType, topics))
        return self.__redis.delete(*topics)
    
    def __genType(self, key: str):
        """
        Create type key from key
        """
        return f"{key}_type"
    
    def __checkType(self, key: str):
        """
        Check if a key is type key
        """
        return key.endswith("_type")

    # AS DICT
    @__handleConnectException
    def value(self, topic: str, key: str):
        """
        Get a value of key in topic
        """
        typ = self.__redis.hget(topic, self.__genType(key))
        value = self.__redis.hget(topic, key)
        if typ in ["list", "dict"]:
            value = json.loads(value)
        else:
            value = globals()["__builtins__"][typ](value)
        return value

    @__handleConnectException
    def items(self, topic: str):
        """
        Get list of [{key: value}] from topic
        """
        raws = self.__redis.hgetall(topic)
        values = {}
        for key in raws:
            if not self.__checkType(key):
                typ = raws[self.__genType(key)]
                value = raws[key]
                if typ in ["list", "dict"]:
                    value = json.loads(value)
                else:
                    value = globals()["__builtins__"][typ](value)
                values[key] = value
        return values
    
    @__handleConnectException
    def setValue(self, topic: str, key: str, value: Type[int | float | str | bytes | list | dict]):
        """
        Set a value of key in topic. If value exists, change value.

        Return the number of added fields
        """
        typ = type(value).__name__
        self.__redis.hset(topic, self.__genType(key), typ)
        if typ in ["list", "dict"]:
            value = json.dumps(value)
        return self.__redis.hset(topic, key, value)
    
    @__handleConnectException
    def setItems(self, topic: str, values: dict):
        """
        Set all {key: value} to topic by dict
        """
        datas = {}
        for key in values:
            if not self.__checkType(key):
                typ = type(values[key]).__name__
                datas[self.__genType(key)] = typ
                if typ in ["list", "dict"]:
                    values[key] = json.dumps(values[key])
                datas[key] = values[key]
        self.__redis.hset(topic, mapping=datas)
        return True
    
    @__handleConnectException
    def popItems(self, topic: str, *keys: str):
        """
        Remove some {key: value} in a topic by keys
        """
        types = []
        for key in keys:
            types.append(self.__genType(key))
        self.__redis.hdel(topic, *keys, *types)
        return True

    # AS LIST
    @__handleConnectException
    def slice(self, topic: str, start: int = 0, stop: int = -1):
        """
        Get a slice of data list in topic. If out range, return part of list or empty list.
        """
        typs = self.__redis.lrange(self.__genType(topic), start, stop)
        raws = self.__redis.lrange(topic, start, stop)
        values = raws.copy()
        for i in range(len(raws)):
            typ = typs[i]
            value = raws[i]
            if typ in ["list", "dict"]:
                value = json.loads(value)
            else:
                value = globals()["__builtins__"][typ](value)
            values[i] = value
        return values

    @__handleConnectException
    def push(self, topic: str, *values):
        """
        Enqueue values to the tail of topic

        Return the number of added fields
        """
        typ_list = []
        values = list(values)
        for i in range(len(values)):
            typ = type(values[i]).__name__
            typ_list.append(typ)
            if typ in ["list", "dict"]:
                values[i] = json.dumps(values[i])
        self.__redis.rpush(self.__genType(topic), *typ_list)
        return self.__redis.rpush(topic, *values)

    @__handleConnectException
    def pop(self, topic: str):
        """
        Pop data from the tail of topic
        """
        typ = self.__redis.rpop(self.__genType(topic))
        raw = self.__redis.rpop(topic)
        if typ in ["list", "dict"]:
            value = json.loads(raw)
        else:
            value = globals()["__builtins__"][typ](raw)
        return value
    
    @__handleConnectException
    def dequeue(self, topic: str):
        """
        Dequeue data from the head of topic
        """
        typ = self.__redis.lpop(self.__genType(topic))
        raw = self.__redis.lpop(topic)
        value = None
        if raw and typ:
            if typ in ["list", "dict"]:
                value = json.loads(raw)
            else:
                value = globals()["__builtins__"][typ](raw)
        return value
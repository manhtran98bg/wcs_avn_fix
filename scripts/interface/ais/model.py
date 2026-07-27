import json


class AIS_Message:
    @classmethod
    def decode(cls, data: str):
        return cls.fromDict(json.loads(data))

    @classmethod
    def fromDict(cls, data: dict):
        obj = cls()
        for key, typ in cls.__annotations__.items():
            setattr(obj, key, data.get(key, typ()))
        return obj

    def __init__(self) -> None:
        for key, typ in type(self).__annotations__.items():
            setattr(self, key, typ())

    def items(self) -> dict:
        return {
            key: getattr(self, key, typ())
            for key, typ in type(self).__annotations__.items()
        }

    def encode(self) -> str:
        return json.dumps(self.items())


class AIS_AGV_STATE_MSG(AIS_Message):
    pause: list
    normal: list
    timestamp: float


class AIS_Msg_Heartbeat(AIS_Message):
    heartbeat: bool
    timestamp: float
    sequence: int

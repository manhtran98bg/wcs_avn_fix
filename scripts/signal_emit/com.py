from .config import SIGNAL_SERVER_CONFIG, SIGNAL_CHANNEL_MODEL_MAPPING
from common import MODULE_NAME

from rostek_utils.utils.pattern import Declare_Class, Singleton
from rostek_utils.utils.logger import Logger
from rostek_utils.utils.thread import Worker
import redis
import redis.client
import json
from time import sleep
from typing import Callable, Dict, List

class Signal_Handle(metaclass=Singleton):
    """
    Handle callback function through signal (Singleton).
    - Callback will be subscribed to channel
    - When emit signal, callback will be called
    
    Interface:
    - subscribe: register a callback to a channel
    - emit: call all callback on channel
    """
    def __init__(self) -> None:
        self.__redis = redis.Redis(
            SIGNAL_SERVER_CONFIG.HOST,
            SIGNAL_SERVER_CONFIG.PORT,
            0, None,
            decode_responses=True  # Automatically decode responses to Python strings
        )
        self.__signal: redis.client.PubSub = None
        self.__signal_clbk: Dict[str, List[Callable]] = {}
        self.handleSignal()
    
    # Signal
    def handleSignal(self):
        """
        Handle all channedls signal, run in another thread.
        Block until connected.

        signal_data: { [channel]: [payload] }
        """
        self.__handleSignal()
        while not self.__signal:
            sleep(1)

    @Worker.employ
    def __handleSignal(self):
        """
        Handle all channedls signal, run in another thread

        signal_data: { [channel]: [payload] }
        """
        self.__signal = self.__redis.pubsub()
        while True:
            data = self.__signal.get_message()
            if data:
                message = data['data']
                if message and type(message) != int:
                    try:
                        message = json.loads(message)
                        channel = message["channel"]
                    except Exception as e:
                        Logger(MODULE_NAME.SIGNAL).error(f"Wrong data: {e}")
                        continue
                    if channel in self.__signal_clbk:
                        try:
                            model_type: Declare_Class = SIGNAL_CHANNEL_MODEL_MAPPING.mapping(
                                SIGNAL_CHANNEL_MODEL_MAPPING.CHANNEL,
                                SIGNAL_CHANNEL_MODEL_MAPPING.MODEL,
                                channel
                            )[0]
                        except Exception as e:
                            Logger(MODULE_NAME.SIGNAL).error(f"Wrong channel: {e}")
                            continue

                        try:
                            payload = model_type.decode(message["payload"])
                            for clbk in self.__signal_clbk[channel]:
                                clbk(payload)
                        except Exception as e:
                            Logger(MODULE_NAME.SIGNAL).error(f"Parse payload fail: {e}")
                            continue
    
    @staticmethod
    def __handleSignalException(func: Callable):
        def inner(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                Logger(MODULE_NAME.SIGNAL).error(f"Handle signal error: {e}")
        return inner
    
    @__handleSignalException
    def emit(self, channel: str, payload: Declare_Class):
        """
        Call all functions that subscribe this channel
        """
        self.__redis.publish(
            channel=channel,
            message=json.dumps({
                "channel": channel,
                "payload": payload.encode()
            })
        )
        return True
    
    @__handleSignalException
    def subscribe(self, channel: str, func: Callable):
        """
        Subcribe to a channel, will be executed on emit

        func(payload: Declare_Class)
        """
        if channel in self.__signal_clbk:
            self.__signal_clbk[channel].append(func)
        else:
            self.__signal.subscribe(channel)
            self.__signal_clbk[channel] = [func]
        return True
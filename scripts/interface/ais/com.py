from .model import AIS_AGV_STATE_MSG, AIS_Msg_Heartbeat
from .config import AIS_TOPIC
from utils.helper import Helper
from signal_emit.com import Signal_Handle
from signal_emit.config import SIGNAL_CHANNEL
from signal_emit.config import AIS_States_Signal

from rostek_utils.utils.thread import Worker
from time import time, sleep
import json
import threading
import paho.mqtt.client as mqtt

from common import MODULE_NAME
from rostek_utils.utils.logger import Logger

AIS_AGV_STATE_STALE_TIMEOUT = 15
AIS_AGV_STATE_FUTURE_TOLERANCE = 5


class AIS_Interface:
    """
    Communicate with AIS.

    Kwargs:
        broker: (str) broker ip = 127.0.0.1
        port: (int) broker port = 1883
        user: (str) username if required = None
        password: (str) user password if required = None
        timeout: (float) connection timeout

    Interface:
    - connected: Check if AIS is connected
    - signal: List of agv need to pause/continue (channel: AIS_AGV_STATES)
    """
    def __init__(self, **kwargs) -> None:
        self.__conn_timeout = kwargs["timeout"]
        self.__last_uptime = 0
        self.__logger = Logger(MODULE_NAME.AIS)
        self.__mqtt_logger = Logger("MQTT")
        self.__mqtt_connected = threading.Event()
        self.__mqtt: mqtt.Client = None

        keys = ["broker", "port", "user", "password"]
        self.__connect(**Helper.extractDict(kwargs, keys, keys))
        self.__sendUptime()

    def connected(self):
        """
        Check if AIS connection is open.
        """
        return time() - self.__last_uptime < self.__conn_timeout

    @Worker.employ
    def __connect(self, broker: str = "127.0.0.1", port: int = 1883, user: str = None, password: str = None):
        """
        Auto handle MQTT messages from AIS.
        """
        self.__mqtt = mqtt.Client(client_id="dal")
        if user is not None and password is not None:
            self.__mqtt.username_pw_set(username=user, password=password)

        self.__mqtt.reconnect_delay_set(min_delay=1, max_delay=30)
        self.__mqtt.on_connect = self.__onConnect
        self.__mqtt.on_disconnect = self.__onDisconnect
        self.__mqtt.on_message = self.__onMessage
        self.__mqtt.on_log = self.__onLog

        try:
            self.__mqtt_logger.info(
                f"WCS AIS MQTT loop start host={broker}, port={port}, client_id=dal"
            )
            self.__mqtt.connect_async(broker, port, keepalive=30)
            self.__mqtt.loop_start()

            while True:
                sleep(1)
        except Exception as e:
            self.__mqtt_connected.clear()
            self.__mqtt_logger.error(f"WCS AIS MQTT loop failed: {e}")
        finally:
            self.__mqtt_connected.clear()
            if self.__mqtt is not None:
                self.__mqtt_logger.info("WCS AIS MQTT loop stop")
                self.__mqtt.loop_stop()

    def __onConnect(self, client: mqtt.Client, userdata, flags, rc):
        """
        Triggered when paho connects or reconnects to broker.
        """
        if rc != 0:
            self.__mqtt_connected.clear()
            self.__mqtt_logger.error(f"WCS AIS MQTT connect failed rc={rc}")
            return

        self.__mqtt_connected.set()
        self.__mqtt_logger.info("WCS AIS MQTT connected client_id=dal")
        self.__subscribe(client, AIS_TOPIC.AGV_STATES, qos=2)
        self.__subscribe(client, AIS_TOPIC.HEARTBEAT, qos=2)

    def __onDisconnect(self, client: mqtt.Client, userdata, rc):
        """
        Triggered when broker connection is lost or intentionally closed.
        """
        self.__mqtt_connected.clear()
        self.__mqtt_logger.warn(f"WCS AIS MQTT disconnected client_id=dal, rc={rc}")

    def __onLog(self, client: mqtt.Client, userdata, level, buf):
        """
        Log paho internal warning/error messages for reconnect diagnostics.
        """
        if level == mqtt.MQTT_LOG_ERR:
            self.__mqtt_logger.error(f"WCS AIS Paho MQTT error: {buf}")
        elif level == mqtt.MQTT_LOG_WARNING:
            self.__mqtt_logger.warn(f"WCS AIS Paho MQTT warning: {buf}")

    def __subscribe(self, client: mqtt.Client, topic: str, qos: int):
        result, mid = client.subscribe(topic, qos=qos)
        if result == mqtt.MQTT_ERR_SUCCESS:
            self.__mqtt_logger.info(f"WCS AIS MQTT subscribed topic={topic}, qos={qos}, mid={mid}")
        else:
            self.__mqtt_logger.error(
                f"WCS AIS MQTT subscribe failed topic={topic}, qos={qos}, rc={result}, mid={mid}"
            )

    def __onMessage(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
        """
        Handle raw MQTT messages and route to topic-specific handlers.
        """
        topic = msg.topic
        try:
            raw_msg = msg.payload.decode()
            if topic == AIS_TOPIC.AGV_STATES:
                message = AIS_AGV_STATE_MSG.decode(raw_msg)
                self.__onAgvState("dal", topic, message)
            elif topic == AIS_TOPIC.HEARTBEAT:
                message = AIS_Msg_Heartbeat.decode(raw_msg)
                self.__onHeartbeat("dal", topic, message)
            else:
                self.__mqtt_logger.warn(f"WCS AIS MQTT drop unknown topic={topic}")
        except Exception as e:
            self.__mqtt_logger.error(f"WCS AIS MQTT message error topic={topic}: {e}")

    def __onAgvState(self, name: str, topic: str, msg: AIS_AGV_STATE_MSG):
        """
        Handle agv state message.
        """
        now = time()
        timestamp = getattr(msg, "timestamp", None)
        pause = getattr(msg, "pause", None)
        normal = getattr(msg, "normal", None)

        if timestamp is None:
            self.__logger.warn(
                f"AIS MQTT DROP INVALID: reason=missing_timestamp, "
                f"name={name}, topic={topic}, pause={pause}, normal={normal}"
            )
            return

        try:
            timestamp = float(timestamp)
        except Exception:
            self.__logger.warn(
                f"AIS MQTT DROP INVALID: reason=bad_timestamp, "
                f"name={name}, topic={topic}, timestamp={timestamp}, "
                f"pause={pause}, normal={normal}"
            )
            return

        age = now - timestamp
        if age > AIS_AGV_STATE_STALE_TIMEOUT:
            self.__logger.warn(
                f"AIS MQTT DROP STALE: age={age:.3f}, "
                f"name={name}, topic={topic}, pause={pause}, normal={normal}"
            )
            return

        # if age < -AIS_AGV_STATE_FUTURE_TOLERANCE:
        #     self.__logger.warn(
        #         f"AIS MQTT DROP FUTURE: skew={-age:.3f}, "
        #         f"name={name}, topic={topic}, timestamp={timestamp}, "
        #         f"pause={pause}, normal={normal}"
        #     )
        #     return

        self.__last_uptime = now
        try:
            self.__logger.info(
                f"AIS MQTT RECEIVE: name={name}, topic={topic}, "
                f"age={age:.3f}, pause={pause}, normal={normal}"
            )
        except Exception as e:
            self.__logger.error(f"AIS MQTT LOG FAIL: {e}")

        states = AIS_States_Signal()
        states.pause = pause or []
        states.normal = normal or []
        Signal_Handle().emit(SIGNAL_CHANNEL.AIS_AGV_STATES, states)

    def __onHeartbeat(self, name: str, topic: str, msg: AIS_Msg_Heartbeat):
        """
        Handle AIS heartbeat message.
        """
        self.__last_uptime = time()

    @Worker.employ
    def __sendUptime(self):
        """
        Send uptime message to AIS in a loop.
        """
        while True:
            self.__publishJson("wcs_status", AIS_AGV_STATE_MSG().items(), qos=0, timeout=2)
            sleep(2)

    def __publishJson(self, topic: str, payload: dict, qos: int = 0, timeout: float = 2) -> bool:
        if (
            self.__mqtt is None
            or not self.__mqtt_connected.is_set()
            or not self.__mqtt.is_connected()
        ):
            return False

        try:
            result = self.__mqtt.publish(topic, json.dumps(payload), qos=qos)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                self.__mqtt_logger.error(f"WCS AIS MQTT publish failed topic={topic}, rc={result.rc}")
                return False

            result.wait_for_publish(timeout)
            if not result.is_published():
                self.__mqtt_logger.error(f"WCS AIS MQTT publish timeout topic={topic}")
                return False

            return True
        except Exception as e:
            self.__mqtt_logger.error(f"WCS AIS MQTT publish error topic={topic}: {e}")
            return False

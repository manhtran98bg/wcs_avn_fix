from utils.redis_db import RedisHandler
from .config import DATABASE_SERVER_CONFIG, DATABASE_NAME
from .model.mission import Mission_Model
from .model.mission_trigger import Mission_Trigger_Model
from .model.device_connection import Device_Connection_Model
from .model.curtain import Curtain_Status_Model, CURTAIN_LOCATION, CURTAIN_STATUS
from .model.pwm import PWM_Status_Model, PWM_Information_Model, PWM_MACHINE_STATUS, PWM_PALLET_STATUS, PWM_WRAP_STATUS
from .model.auto_line import Auto_Line_Model, AUTO_LINE_MODEL_STATUS
from .model.pause_list import Pause_List_Model
from utils.helper import Helper

from rostek_utils.utils.pattern import Singleton, Declare_Class
import json
from threading import Lock
from uuid import uuid4
from typing import Dict, Type, List

class Database:
    """
    Handle local database with redis

    Kwargs:
        host: (str) redis server ip
        port: (int) redis port

    Database format:
    - As record
        ```
        [record name]:
        {
            "[record name]_model": [model type]
            "[key]": [value]
        }
        ```
    - As list
        ```
        [list name]: [ [record name] ]
        "[list name]#[record name]":
        {
            "[record name]_model": [model type]
            "[key]": [value]
        }
        ```
    - As model table
        ```
        [model name];
        {
            [record name]: "{[key]: [value]}" 
        }
        ```
    
    Interface:
    - Record: get, set, remove
    - List: slice, push, pop, dequeue, clear
    - Table: lookUp, update, delete
    """
    def __init__(self, **kwargs) -> None:
        self.__conn: RedisHandler = None

        self.__connect(**kwargs)
        
    def __connect(self, **kwargs):
        """
        Kwargs:
            host: (str) redis server ip
            port: (int) redis port
        """
        self.__conn = RedisHandler()
        self.__conn.connect(**kwargs)

    # AS RECORD
    def __genType(self, record_name: str):
        """
        Return [record name]_model
        """
        return f"{record_name}_model"

    def get(self, *record_names: str):
        """
        Get records by names

        Return: { [record name]: [record] }
        """
        records: Dict[str, Declare_Class] = {}
        for record_name in record_names:
            record = self.__conn.items(record_name)
            if not record:
                continue

            typ = record[self.__genType(record_name)]
            records[record_name] = globals()[typ]()
            records[record_name].set(record)

        return records
    
    def set(self, record_name: str, record: Declare_Class):
        """
        Add/update one record by name
        """
        self.__conn.setItems(record_name, record.items())
        self.__conn.setValue(
            record_name, self.__genType(record_name), type(record).__name__)

    def remove(self, *record_names: str):
        """
        Remove records by names
        """
        self.__conn.remove(*record_names)
    
    # AS LIST
    def __genIndex(self, list_name: str, record_name: str):
        """
        Return [list name]#[record name]
        """
        return f"{list_name}#{record_name}"
    
    def slice(self, list_name: str, start: int = 0, stop: int = -1):
        """
        Get list of records by indexes

        Return: [ record ]
        """
        record_names = self.__conn.slice(list_name, start, stop)
        record_datas = self.get(*list(map(lambda x: self.__genIndex(list_name, x), record_names)))
        records: List[Declare_Class] = []
        for record_name in record_names:
            records.append(record_datas[self.__genIndex(list_name, record_name)])
        return records

    def push(self, list_name: str, *records: Declare_Class):
        """
        Add records to the end of list
        """
        for record in records:
            record_name = str(uuid4())
            self.__conn.push(list_name, record_name)
            self.set(self.__genIndex(list_name, record_name), record)
    
    def pop(self, list_name: str):
        """
        Remove last record in list

        Return: removed record
        """
        record_name = self.__conn.pop(list_name)
        index_name = self.__genIndex(list_name, record_name)
        record = self.get(index_name)
        self.remove(index_name)
        return record[index_name] if record else None
    
    def dequeue(self, list_name: str):
        """
        Remove first record in list
        """
        record_name = self.__conn.dequeue(list_name)
        index_name = self.__genIndex(list_name, record_name)
        record = self.get(index_name)
        self.remove(index_name)
        return record[index_name] if record else None
    
    def clear(self, list_name: str):
        """
        Remove list of records
        """
        record_names = self.__conn.slice(list_name, 0, -1)
        for record_name in record_names:
            self.__conn.remove(self.__genIndex(list_name, record_name))
        self.__conn.remove(list_name)
    
    # AS TABLE
    def lookUp(self, model: Type[Declare_Class], *record_names: str) -> Dict[str, Declare_Class | None]:
        """
        Get some records on table by names

        Return: [record name]: [ model object | None if not found]
        """
        data = self.__conn.items(model.__name__)
        records = Helper.extractDict(data, record_names, record_names, False, None)
        for record_name in records:
            if records[record_name]:
                data = json.loads(records[record_name])
                records[record_name] = model.fromDict(data)
        return records

    def update(self, record_name: str, data: Declare_Class):
        """
        Update a record on table (add if record_name not exist)
        """
        self.__conn.setValue(
            type(data).__name__,
            record_name,
            json.dumps(data.items())
        )
    
    def delete(self, model: Type[Declare_Class], *record_names: str):
        """
        Remove some records on table by names
        """
        if record_names:
            self.__conn.popItems(model.__name__, *record_names)
        else:
            self.__conn.remove(model.__name__)

class Database_Interface(metaclass=Singleton):
    def __init__(self) -> None:
        """
        Handle DAL database (Singleton)

        Interface:
        - Mission_Trigger_Model:
            - pushTrigger: Save call/cancel mission trigger
            - popTrigger: Get call/cancel mission trigger
        - Device_Connection_Model:
            - getConnections: Get device connection status
            - updateConnection: Add device connection status
            - removeConnections: Remove device connection status
        - Mission_Model:
            - getMissions: Get mission information
            - updateMission: Update mission information
            - removeMissions: Remove missions information
            - getMissionByRcs: RCS get mission information by task code
        - Curtain_Status_Model:
            - getCurtainStatus: Get curtain open status
            - updateCurtainStatus: Save curtain open status
            - resetCurtainStatus: Turn on all curtains
        - PWM_Information_Model:
            - getPWMStatus: Get PWM running status
            - updatePWMStatus: Save PWM running status
            - resetPWMStatus: Restore PWM status
        - Auto_Line_Model:
            - getAutoStatus: Get auto lines call state
            - updateAutoStatus: Save auto lines call state
            - resetAutoLineStatus: Restore idle state of all auto lines
        - Pause_List_Model:
            - getPauseList: Get pause list (robot: method)
            - updatePause: Update robot pause data
            - removePause: Remove pause data by robot code
        
        At start:
        - Initialize default values: PWM_Information_Model, Auto_Line_Model, Curtain_Status_Model
        - Clear database: Device_Connection_Model, Mission_Trigger_Model
        """
        self.__db = Database(host=DATABASE_SERVER_CONFIG.HOST, port=DATABASE_SERVER_CONFIG.PORT)
        self.__pwm_stt_lock = Lock()
        self.__pwm_info_lock = Lock()
        self.__curtain_lock = Lock()

        self.resetPWMStatus()
        self.resetAutoLineStatus()
        self.resetCurtainStatus()
        self.removeConnection()
        self.clearTrigger()
    
    # MISSION TRIGGER
    def pushTrigger(self, trigger: Mission_Trigger_Model):
        """
        Save mission trigger
        """
        self.__db.push(DATABASE_NAME.MISSION_TRIGGER_LIST, trigger)
    
    def popTrigger(self) -> Mission_Trigger_Model:
        """
        Get oldest mission trigger
        """
        return self.__db.dequeue(DATABASE_NAME.MISSION_TRIGGER_LIST)
    
    def clearTrigger(self) -> Mission_Trigger_Model:
        """
        Remove all mission triggers
        """
        return self.__db.clear(DATABASE_NAME.MISSION_TRIGGER_LIST)
    
    # DEVICE CONNECTION
    @staticmethod
    def __genConnectionName(connection: Device_Connection_Model):
        """
        Return: "[gateway_id_[plc_id]_[button_id]"
        """
        return f"{connection.gateway_id}_{connection.plc_id}_{connection.button_id}"
        
    def getConnections(self)\
            -> Dict[str, Device_Connection_Model | None]:
        """
        Get devices' connection status
        """
        return self.__db.lookUp(Device_Connection_Model)
    
    def updateConnection(self, connection: Device_Connection_Model):
        """
        Save device connection status
        """
        self.__db.update(self.__genConnectionName(connection), connection)
    
    def removeConnection(self, *connections: Device_Connection_Model):
        """
        Remove connections from database (for disconnected devices)
        """
        self.__db.delete(Device_Connection_Model, *map(lambda conn: self.__genConnectionName(conn), connections))
    
    # MISSION
    def getMissions(self, *mission_codes: str) -> Dict[str, Mission_Model]:
        """
        Get missions information by mission_codes
        """
        return self.__db.lookUp(Mission_Model, *mission_codes)

    def updateMission(self, mission: Mission_Model):
        """
        Update a mission (add if mission_code not exist)
        """
        self.__db.update(mission.code, mission)
    
    def removeMissions(self, *mission_codes: str):
        """
        Remove missions by mission_codes
        """
        self.__db.delete(Mission_Model, *mission_codes)

    def getMissionByRcs(self, rcs_task_code: str):
        """
        Get mission info by rcs task code
        """
        missions: Dict[str, Mission_Model] = self.__db.lookUp(Mission_Model)
        for mission in missions:
            if missions[mission].rcs_code == rcs_task_code:
                return missions[mission]
        return None
    
    # CURTAIN
    def getCurtainStatus(self, *locations: str) -> Dict[str, Curtain_Status_Model | None]:
        """
        Get curtain open status
        """
        with self.__curtain_lock:
            return self.__db.lookUp(Curtain_Status_Model, *locations)
    
    def updateCurtainStatus(self, status: Curtain_Status_Model):
        """
        Save curtain open status
        """
        with self.__curtain_lock:
            self.__db.update(status.location, status)

    def resetCurtainStatus(self):
        """
        Restore curtain status to default
        - On
        """
        with self.__curtain_lock:
            self.__db.delete(Curtain_Status_Model)
        for location in CURTAIN_LOCATION.values():
            status = Curtain_Status_Model()
            status.location = location
            status.status = CURTAIN_STATUS.ON
            self.updateCurtainStatus(status)

    # PWM STATUS
    def getPWMStatus(self) -> PWM_Status_Model | None:
        """
        Get PWM status
        """
        with self.__pwm_stt_lock:
            data = self.__db.get(DATABASE_NAME.PWM_STATUS_RECORD)
            if not data:
                return None
            return data[DATABASE_NAME.PWM_STATUS_RECORD]
    
    def updatePWMStatus(self, status: PWM_Status_Model):
        """
        Save PWM status
        """
        with self.__pwm_stt_lock:
            self.__db.set(DATABASE_NAME.PWM_STATUS_RECORD, status)
    
    def resetPWMStatus(self):
        """
        Restore PWM status to default
        - No pallet
        - Wrap not done
        - Bypass
        """
        with self.__pwm_stt_lock:
            self.__db.remove(DATABASE_NAME.PWM_STATUS_RECORD)
        stt = PWM_Status_Model()
        stt.machine_state = PWM_MACHINE_STATUS.BYPASS
        stt.wrap_state = PWM_WRAP_STATUS.BUSY
        self.updatePWMStatus(stt)

        with self.__pwm_info_lock:
            self.__db.remove(DATABASE_NAME.PWM_INFO_RECORD)
        info = PWM_Information_Model()
        info.pallet_state = PWM_PALLET_STATUS.NONE
        self.updatePWMInfo(info)

    def getPWMInfo(self) -> PWM_Information_Model | None:
        """
        Get PWM info (pallet, agv, production line)
        """
        with self.__pwm_info_lock:
            data = self.__db.get(DATABASE_NAME.PWM_INFO_RECORD)
            if not data:
                return None
            return data[DATABASE_NAME.PWM_INFO_RECORD]
    
    def updatePWMInfo(self, info: PWM_Information_Model):
        """
        Save PWM info
        """
        with self.__pwm_info_lock:
            self.__db.set(DATABASE_NAME.PWM_INFO_RECORD, info)

    # AUTO LINE STATUS
    def getAutoStatus(self) -> Auto_Line_Model | None:
        """
        Get auto line status
        """
        data = self.__db.get(DATABASE_NAME.AUTO_LINE_STATUS)
        if not data:
            return None
        return data[DATABASE_NAME.AUTO_LINE_STATUS]
    
    def updateAutoStatus(self, status: Auto_Line_Model):
        """
        Save auto line status
        """
        self.__db.set(DATABASE_NAME.AUTO_LINE_STATUS, status)
    
    def resetAutoLineStatus(self):
        """
        Restore auto line status to default
        - No call agv
        """
        self.__db.remove(DATABASE_NAME.AUTO_LINE_STATUS)
        info = Auto_Line_Model()
        info.product_line_1 = AUTO_LINE_MODEL_STATUS.IDLE
        info.product_line_2 = AUTO_LINE_MODEL_STATUS.IDLE
        info.empty_pallet = AUTO_LINE_MODEL_STATUS.IDLE
        self.updateAutoStatus(info)
    
    # PAUSE LIST
    def getPauseList(self, *robot_codes: str) -> Dict[str, Pause_List_Model | None]:
        """
        Get pause records of all robots
        """
        return self.__db.lookUp(Pause_List_Model, *robot_codes)
    
    def updatePause(self, robot_code: str, method: str):
        """
        Update pause data
        """
        pause = Pause_List_Model()
        pause.method = method
        self.__db.update(robot_code, pause)

    def removePause(self, *robot_codes: str):
        """
        Remove some pause data by robot code
        """
        self.__db.delete(Pause_List_Model, *robot_codes)
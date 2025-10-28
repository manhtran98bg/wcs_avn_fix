from .config import WCS_URL_PATH, WCS_SUCCESS_MSG, WCS_MISSION_STATUS, BIND_RCS_STATUS
from .model import Mission_Info_Res, Device_Update_Req, Device_Information_Res, Mission_Trigger_Res, Bind_RCS_Model
from database.model.mission import Mission_Model
from database.model.mission_trigger import MISSION_TRIGGER_ACTION, Mission_Trigger_Model, MISSION_TRIGGER_CREATOR
from common import MODULE_NAME, Device_Information, LOCATION_STATUS, INTERFACE_CONVERTER, CALLBOX_BUTTON, AUTO_LINE_BUTTON
from signal_emit.com import Signal_Handle
from signal_emit.config import SIGNAL_CHANNEL
from signal_emit.model import Bind_RCS_Signal

from rostek_utils.utils.logger import Logger
from rostek_utils.com.rest_api import RestApi, HTTP_RESPONSE_CODE
from typing import List

class WCS_Interface:
    """
    Communicate with WCS

    Kwargs:
        url: (str) backend url
        user: (str) user with admin role
        pass: (str) user password

    Interface:
    - getToken: Login and get auth token
    - getDevices: Get device information
    - fillPDATrigger: Update device data in PDA trigger
    - updateDeviceConnection: Update gateway connection status
    - getMissions: Get mission information
    - updateMissionAgv: Update mission agv code
    - updateMissionStatus: Update mission status
    - getMission: Send trigger to Backend to get mission information
        - __getWrapMission: Call mission from line to pwm and get mission information
        - __getStoreMission: Call mission from pwm to storage and get mission information
    - cancelMission: Report cancel mission trigger
    - updateLocation: Update location status

    Callback:
    - Backend trigger -> __bindRCS
    """
    def __init__(self, **kwargs) -> None:
        self.__url = kwargs["url"]
        self.__token: dict = {}
        self.__user = kwargs["user"]
        self.__pass = kwargs["pass"]
        self.__logger = Logger(MODULE_NAME.WCS)

    def getToken(self):
        """
        Get user token

        Return: True if success
        """
        req = {
            "name": self.__user,
            "password": self.__pass
        }
        try:
            res = RestApi.client.post(
                self.__url + WCS_URL_PATH.LOGIN,
                json=req,
                timeout=3)
            if res.status_code in HTTP_RESPONSE_CODE.OK:
                response = res.json()
                if response["msg"] == WCS_SUCCESS_MSG.LOGIN:
                    self.__token = {
                        "Authorization": "Bearer {}".format(
                            response["metaData"]["access_token"]
                        )
                    }
                    return True
            self.__logger.warn(f"Get token fail: {res.content}")
        except Exception as e:
            self.__logger.error(f"Get token error: {e}")
        return False

    def getDevices(self, number: int = -1,
            location: str | List[str] = None,
            sector: str | List[str] = None
        ) -> List[Device_Information]:
        """
        Get device information (for pda to get plc info)

        number: number of devices
        location: selected field
        sector: type of goods

        Return: list of devices
        """
        req = {
            "filter": {}
        }
        if number > -1:
            req["limit"] = number
        if location:
            req["filter"]["location"] = location
        if sector:
            req["filter"]["sectors"] = sector
        
        try:
            res = RestApi.client.post(
                self.__url + WCS_URL_PATH.GET_DEVICES,
                headers=self.__token,
                json=req,
                timeout=6,
            )

            if res.status_code in HTTP_RESPONSE_CODE.OK:
                response = res.json()
                devices = []
                if response["msg"] == WCS_SUCCESS_MSG.GET_LIST:
                    for data in response["metaData"]:
                        raw_device = Device_Information_Res.fromDict(data)
                        device = Device_Information()
                        device.id = raw_device._id
                        device.button_id = int(raw_device.deviceId)
                        device.gateway_id = raw_device.gateway_id
                        device.plc_id = raw_device.plc_id
                        devices.append(device)
                    return devices
            
            self.__logger.warn(f"Get device fail: {res.content}")
        except Exception as e:
            self.__logger.error(f"Get device error: {e}")

        return []
    
    def fillPDATrigger(self, trigger: Mission_Trigger_Model):
        """
        Update device data in PDA trigger
        """
        device = self.getDevices(
            location=trigger.location,
            sector=trigger.sector)
        if not device:
            return None
        
        device = device[0]
        trigger.gateway_id = device.gateway_id
        trigger.plc_id = device.plc_id
        trigger.button_id = device.button_id
        return trigger

    def updateDeviceConnection(self, device: Device_Information):
        """
        Update device connection status (to connected)

        device: device information

        Return: True if success
        """
        req = Device_Update_Req()
        req.gateway_id = device.gateway_id
        req.plc_id = device.plc_id
        req.deviceId = device.button_id
        
        try:
            res = RestApi.client.patch(
                self.__url + WCS_URL_PATH.UPDATE_DEVICE,
                headers=self.__token,
                json=[req.items()],
                timeout=6,
            )

            if res.status_code in HTTP_RESPONSE_CODE.OK:
                response = res.json()
                if response["msg"] == WCS_SUCCESS_MSG.UPDATE:
                    return True
            
            self.__logger.warn(f"Update device fail: {res.content}")
        except Exception as e:
            self.__logger.error(f"Update device error: {e}")

        return False
    
    def getMissions(self,
            number: int = -1,
            device_id: str | List[str] = None,
            status: WCS_MISSION_STATUS | List[WCS_MISSION_STATUS] = None
        ) -> List[Mission_Model]:
        """
        Get list of mission information in history

        - number: number of missions
        - device_id: plc id
        - status: mission status

        Return: list of mission info
        """
        req = {
            "filter": {}
        }
        if number > -1:
            req["limit"] = number
        if device_id:
            req["filter"]["call_boxes_id"] = device_id
        if status:
            if type(status) != list:
                status = [status]

            req["filter"]["current_state"] = status
        
        try:
            res = RestApi.client.post(
                self.__url + WCS_URL_PATH.GET_MISSIONS,
                headers=self.__token,
                json=req,
                timeout=6,
            )

            if res.status_code in HTTP_RESPONSE_CODE.OK:
                response = res.json()
                missions = []
                if response["msg"] == WCS_SUCCESS_MSG.GET_LIST:
                    for data in response["metaData"]:
                        raw_mission = Mission_Info_Res.fromDict(data)

                        mission = Mission_Model()
                        mission.code = raw_mission.mission_code
                        mission.sector = raw_mission.sector
                        mission.location_id = raw_mission._id
                        mission.pickup_location = raw_mission.pickup_location
                        mission.return_location = raw_mission.return_location
                        mission.agv_code = raw_mission.robot_code
                        mission.rcs_code = raw_mission.mission_rcs
                        missions.append(mission)
                return missions
            
            self.__logger.warn(f"Get mission fail: {res.content}")
        except Exception as e:
            self.__logger.error(f"Get mission error: {e}")

        return []

    def updateMissionAgv(self, mission: Mission_Model):
        """
        Update mission agv code

        mission:
            id: mission code
            agv_code: agv code

        Return: True if success
        """
        req = {
            "filter": {
                "mission_code": mission.code
            },
            "robot_code": mission.agv_code
        }
        
        try:
            res = RestApi.client.patch(
                self.__url + WCS_URL_PATH.UPDATE_MISSION,
                headers=self.__token,
                json=req,
                timeout=6,
            )

            if res.status_code in HTTP_RESPONSE_CODE.OK:
                response = res.json()
                if response["msg"] == WCS_SUCCESS_MSG.UPDATE:
                    return True
            
            self.__logger.warn(f"Update mission fail: {res.content}")
        except Exception as e:
            self.__logger.error(f"Update mission error: {e}")

        return False

    def updateMissionStatus(self, mission: Mission_Model, status: WCS_MISSION_STATUS):
        """
        Update mission status

        Args:
            mission:
                code: mission code
            status: status update to mission

        Return: True if success
        """
        req = {
            "filter": {
                "mission_code": mission.code
            },
            "current_state": status
        }
        
        try:
            res = RestApi.client.patch(
                self.__url + WCS_URL_PATH.UPDATE_MISSION,
                headers=self.__token,
                json=req,
                timeout=6,
            )

            if res.status_code in HTTP_RESPONSE_CODE.OK:
                response = res.json()
                if response["msg"] == WCS_SUCCESS_MSG.UPDATE:
                    return True
            
            self.__logger.warn(f"Update mission fail: {res.content}")
        except Exception as e:
            self.__logger.error(f"Update mission error: {e}")

        return False

    def getMission(self, trigger: Mission_Trigger_Model):
        """
        Send trigger to Backend to get mission information
        """
        mission = None
        if trigger.creator == MISSION_TRIGGER_CREATOR.CALLBOX:
            if trigger.button_id not in CALLBOX_BUTTON.SEMI:
                mission = self.__getStoreMission(trigger)
            else:
                mission = self.__getWrapMission(trigger)

        elif trigger.creator == MISSION_TRIGGER_CREATOR.PDA:
            if trigger.button_id in CALLBOX_BUTTON.EMPTY:
                mission = self.__getStoreMission(trigger)
            elif trigger.button_id in CALLBOX_BUTTON.CARTON:
                mission = self.__getStoreMission(trigger)
            elif trigger.button_id in CALLBOX_BUTTON.SEMI:
                mission = self.__getWrapMission(trigger)
            elif trigger.button_id == AUTO_LINE_BUTTON.EMPTY:
                mission = self.__getStoreMission(trigger)
            elif trigger.button_id in [
                AUTO_LINE_BUTTON.PRODUCT_1,
                AUTO_LINE_BUTTON.PRODUCT_2
            ]:
                mission = self.__getWrapMission(trigger)
            else:
                raise Exception(f"Wrong button id: {trigger.items()}")

        elif trigger.creator == MISSION_TRIGGER_CREATOR.AUTO_LINE_PALLET:
            mission = self.__getStoreMission(trigger)

        elif trigger.creator in [
            MISSION_TRIGGER_CREATOR.AUTO_LINE_1,
            MISSION_TRIGGER_CREATOR.AUTO_LINE_2
        ]:
            mission = self.__getWrapMission(trigger)
        
        elif trigger.creator == MISSION_TRIGGER_CREATOR.PWM:
            mission = self.__getStoreMission(trigger)

        else:
            raise Exception(f"Wrong trigger creator: {trigger.items()}")
        
        return mission
    
    def __getWrapMission(self, trigger: Mission_Trigger_Model)-> Mission_Model:
        """
        Send line to pallet wrapper trigger

        device:
            gateway_id: GATEWAY_DEVICE_ID.GATEWAY
            plc_id: GATEWAY_DEVICE_ID
            button_id: GATEWAY_AUTO_ADDRESS
        creator:
            root cause of trigger

        Return: mission information
        """
        req = {
            "gateway_id": trigger.gateway_id,
            "plc_id": trigger.plc_id,
            "object_call": trigger.creator,
            "tasks": [
                {
                    "button_id": trigger.button_id,
                    "action": MISSION_TRIGGER_ACTION.CALL,
                }
            ],
        }
        
        try:
            res = RestApi.client.patch(
                self.__url + WCS_URL_PATH.TRIGGER_WRAP_MISSION,
                headers=self.__token,
                json=req,
                timeout=6,
            )

            if res.status_code in HTTP_RESPONSE_CODE.OK:
                response = res.json()
                raw_mission = Mission_Trigger_Res.fromDict(response)
                if raw_mission.code != 2:
                    mission = Mission_Model()
                    mission.code = raw_mission.mission_code
                    mission.location_id = raw_mission.location_id
                    mission.sector = raw_mission.sectors
                    mission.rcs_code = raw_mission.mission_rcs
                    mission.pickup_location = raw_mission.pickup_location
                    mission.return_location = raw_mission.return_location
                    mission.gateway_id = trigger.gateway_id
                    mission.plc_id = trigger.plc_id
                    mission.button_id = trigger.button_id
                    return mission
            
            self.__logger.warn(f"Wrap mission fail: {res.content}")
        except Exception as e:
            self.__logger.error(f"Wrap mission error: {e}")

        return None
    
    def __getStoreMission(self, trigger: Mission_Trigger_Model) -> Mission_Model:
        """
        Send provider to auto/manual line trigger.
        Send paller wrapper to warehouse trigger

        device:
            gateway_id: GATEWAY_DEVICE_ID.GATEWAY
            plc_id: GATEWAY_DEVICE_ID
            button_id: GATEWAY_AUTO_ADDRESS
        creator:
            root cause of trigger

        Return: mission information
        """
        req = {
            "gateway_id": trigger.gateway_id,
            "plc_id": trigger.plc_id,
            "object_call": trigger.creator,
            "tasks": [
                {
                    "button_id": trigger.button_id,
                    "action": MISSION_TRIGGER_ACTION.CALL,
                }
            ],
        }
        
        try:
            res = RestApi.client.patch(
                self.__url + WCS_URL_PATH.TRIGGER_STORE_MISSION,
                headers=self.__token,
                json=req,
                timeout=6,
            )

            if res.status_code in HTTP_RESPONSE_CODE.OK:
                response = res.json()
                raw_mission = Mission_Trigger_Res.fromDict(response)
                if raw_mission.code != 2 and raw_mission.return_location:
                    mission = Mission_Model()
                    mission.code = raw_mission.mission_code
                    mission.location_id = raw_mission.location_id
                    mission.sector = raw_mission.sectors
                    mission.rcs_code = raw_mission.mission_rcs
                    mission.pickup_location = raw_mission.pickup_location
                    mission.return_location = raw_mission.return_location
                    mission.gateway_id = trigger.gateway_id
                    mission.plc_id = trigger.plc_id
                    mission.button_id = trigger.button_id
                    return mission
            
            self.__logger.warn(f"Store mission fail: {res.content}")
        except Exception as e:
            self.__logger.error(f"Store mission error: {e}")

        return None
    
    def cancelMission(self, trigger: Mission_Trigger_Model) -> bool:
        """
        Send cancel trigger (to both wrap and store mission)

        device:
            gateway_id: GATEWAY_DEVICE_ID.GATEWAY
            plc_id: GATEWAY_DEVICE_ID
            button_id: GATEWAY_AUTO_ADDRESS
        creator:
            root cause of trigger

        Return: True if success
        """
        req = {
            "gateway_id": trigger.gateway_id,
            "plc_id": trigger.plc_id,
            "object_call": trigger.creator,
            "tasks": [
                {
                    "button_id": trigger.button_id,
                    "action": MISSION_TRIGGER_ACTION.CANCEL,
                }
            ],
        }
        
        try:
            res = RestApi.client.patch(
                self.__url + WCS_URL_PATH.TRIGGER_WRAP_MISSION,
                headers=self.__token,
                json=req,
                timeout=6,
            )

            if res.status_code in HTTP_RESPONSE_CODE.OK:
                response = res.json()
                raw_mission = Mission_Trigger_Res.fromDict(response)
                if raw_mission.msg == WCS_SUCCESS_MSG.CANCEL_MISSION:
                    return True
            
            self.__logger.warn(f"Cancel mission fail: {res.content}")
        except Exception as e:
            self.__logger.error(f"Cancel mission error: {e}")

        return False
    
    def __getLocationId(self, location: str) -> str:
        """
        Get location id in Backend

        location: pickup | return location from mission
        """
        area_code, name = location.split("#")

        try:
            res = RestApi.client.get(
                f"{self.__url}{WCS_URL_PATH.UPDATE_LOCATION}",
                headers=self.__token,
                timeout=6,
            )

            if res.status_code in HTTP_RESPONSE_CODE.OK:
                response = res.json()
                if response["msg"] == WCS_SUCCESS_MSG.GET_LOCATION:
                    for data in response["metaData"]:
                        if data["name"] == name and\
                                data["areaCode"] == area_code:
                            return data["_id"]
            
            self.__logger.warn(f"Get location id fail: {res.content}")
        except Exception as e:
            self.__logger.error(f"Get location id error: {e}")

        return ""
    
    def __updateLocation(self, location: str, status: LOCATION_STATUS) -> bool:
        """
        Update location status

        status: (LOCATION_STATUS)
        locations: get from mission information
        
        Return: True if success
        """
        location_id = self.__getLocationId(location)
        req = {
            "status": status,
        }
        
        try:
            res = RestApi.client.patch(
                f"{self.__url}{WCS_URL_PATH.UPDATE_LOCATION}/{location_id}",
                headers=self.__token,
                json=req,
                timeout=6,
            )

            if res.status_code in HTTP_RESPONSE_CODE.OK:
                response = res.json()
                if response["msg"] == WCS_SUCCESS_MSG.UPDATE and\
                        response["metaData"]:
                    return True
            
            self.__logger.warn(f"Update location fail: {res.content}")
        except Exception as e:
            self.__logger.error(f"Update location error: {e}")

        return False
    
    def fillLocation(self, location: str):
        """
        Fill location with pallet
        """
        return self.__updateLocation(location, LOCATION_STATUS.FILL)
    
    def emptyLocation(self, location: str):
        """
        Take pallet from location
        """
        return self.__updateLocation(location, LOCATION_STATUS.AVAILABLE)
    
    # CALLBACK
    @RestApi.server.post(WCS_URL_PATH.BIND_RCS)
    def __bindRCS(data: Bind_RCS_Model):
        """
        Backend trigger bind rcs location (TEST, NOT USED)
        """
        signal = Bind_RCS_Signal()
        signal.binded = data.status == BIND_RCS_STATUS
        signal.points = data.list_data[-1::-1]\
            if signal.binded\
            else data.list_data
        signal.points = list(map(INTERFACE_CONVERTER.WCS_RCS_LOCATION, signal.points))
        Signal_Handle().emit(SIGNAL_CHANNEL.WCS_BIND_RCS, signal)
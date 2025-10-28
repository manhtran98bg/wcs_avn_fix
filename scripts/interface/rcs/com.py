from .model import (
    RCS_Task_Gen_Res, RCS_Task_Status_Res, RCS_Feedback_Req,
    RCS_Location_Model, RCS_Robot_Data_Res
)
from .config import (
    RCS_TASK_TYPE, RCS_URL_PATH, RCS_SUCCESS_CODE, RCS_TASK_PRIORITY,
    RCS_TASK_STATUS, RCS_CHANNEL_API_MAPPING, RCS_LOCATION, RCS_LOCATION_TYPE
)
from database.model.mission import Mission_Model
from database.com import Database_Interface
from signal_emit.com import Signal_Handle
from signal_emit.config import SIGNAL_CHANNEL
from signal_emit.model import Bind_RCS_Signal, RCS_Notify_Signal
from utils.helper import Helper
from common import MODULE_NAME

from rostek_utils.com.rest_api import RestApi, HTTP_RESPONSE_CODE
from rostek_utils.utils.logger import Logger
from time import time_ns, time
from typing import List, Dict

class RCS_Interface:
    """
    Communicate with RCS

    Kwargs:
        url: (str) backend url
        host: (str) rcs notify ip
        port: (int) rcs notify port
    
    Interface:
    - genTask: create agv task
    - blockArea: not allow robot to get in the area
    - continueTask: continue paused task
    - pauseRobot: stop robot from moving
    - resumeRobot: resume agv from pause
    - cancelTask: cancel a delivery task
    - getTaskStatus: get task status
    - bindLoction: bind a location with a container
    - getTaskList: get list of task in rcs
    - freeRobot: free agv from task
    - queryAgvStatus: get agvs status

    Callback:
    - Backend trigger -> __bindRCS
    """
    def __init__(self, **kwargs) -> None:
        self.__url: str = kwargs["url"]
        self.__logger = Logger(MODULE_NAME.RCS)

        for i in range(RCS_CHANNEL_API_MAPPING.CHANNEL.__len__()):
            self.__createApi(
                RCS_CHANNEL_API_MAPPING.PATH[i],
                RCS_CHANNEL_API_MAPPING.CHANNEL[i]
            )
        required = ["host", "port"]
        self.__connect(**Helper.extractDict(kwargs, required, required))

        Signal_Handle().subscribe(SIGNAL_CHANNEL.WCS_BIND_RCS, self.__bindRCS)

    def __connect(self, host: str = "127.0.0.1", port: int = 5000):
        """
        Auto handle request from RCS in another thread
        """
        RestApi.serve(host, port)

    def __genReqCode(self):
        """
        Automatic generate new request code for rcs
        """
        return f"DAL-{time_ns()}"

    def __genLocation(self, location: RCS_Location_Model):
        """
        Create location command to send to RCS
        """
        if location.position.startswith("PK") and location.position_type == RCS_LOCATION_TYPE.ROADWAY:
            return {
                "positionCode": str(int(location.position[2:6])),
                "type": location.position_type
            }
        else:
            return {
                "positionCode": location.position,
                "type": location.position_type
            }
    
    def genTask(self, task_type: RCS_TASK_TYPE, path: List[RCS_Location_Model], priority: bool, agv: str = None):
        """
        Create agv task and send

        Return: task code
        """
        positions = []
        for location in path:
            positions.append(self.__genLocation(location))
        req = {
            "reqCode": self.__genReqCode(),
            "taskTyp": task_type,
            "positionCodePath": positions,
            "podCode": "",
            "podDir": "",
            "priority": RCS_TASK_PRIORITY.HIGH\
                if priority else RCS_TASK_PRIORITY.LOW,
            "ctnrTyp" : "1",
            "agvCode": agv
        }
        self.__logger.info(f"Gen task req: {req}")
        
        try:
            res = RestApi.client.post(
                self.__url + RCS_URL_PATH.CMD_GEN_TASK,
                json=req,
                timeout=3
            )

            if res.status_code in HTTP_RESPONSE_CODE.OK:
                response = RCS_Task_Gen_Res.fromDict(res.json())
                self.__logger.info(f"Gen task res: {response.items()}")
                if response.code == RCS_SUCCESS_CODE:
                    return response.data
            
            self.__logger.warn(f"Gen task fail: {res.content}")
        except Exception as e:
            self.__logger.error(f"Gen task error: {e}")

        return ""
    
    def setBlockArea(self, area: str, block: bool):
        """
        Set/Reset block PWM area
        """
        req = {
            "reqCode": self.__genReqCode(),
            "matterArea": area,
            "indBind": 1 if block else 0,
            "controlMod": "0"
        }
        self.__logger.info(f"Set block req: {req}")
        
        try:
            res = RestApi.client.post(
                self.__url + RCS_URL_PATH.CMD_BLOCK_AREA,
                json=req,
                timeout=6,
            )

            if res.status_code in HTTP_RESPONSE_CODE.OK:
                response = res.json()
                self.__logger.info(f"Set block res: {response}")
                if response["code"] == RCS_SUCCESS_CODE:
                    return True
            
            self.__logger.warn(f"Set block fail: {res.content}")
        except Exception as e:
            self.__logger.error(f"Set block error: {e}")

        return False

    def continueTask(self, task_code: str, location: RCS_Location_Model = None):
        """
        Trigger mission continue
        """
        req = {
            "reqCode": self.__genReqCode(),
            "taskCode": f"{task_code}1_F",
        }
        if location:
            req["nextPositionCode"] = self.__genLocation(location)
        self.__logger.info(f"Continue task req: {req}")
        
        try:
            res = RestApi.client.post(
                self.__url + RCS_URL_PATH.CMD_CONTINUE,
                json=req,
                timeout=3
            )

            if res.status_code in HTTP_RESPONSE_CODE.OK:
                response = res.json()
                self.__logger.info(f"Continue task res: {response}")
                if response["code"] == RCS_SUCCESS_CODE:
                    return True
                
            self.__logger.warn(f"Continue task fail: {res.content}")
        except Exception as e:
            self.__logger.error(f"Continue task error: {e}")

        return False
    
    def pauseRobot(self, *agv_codes: str):
        """
        Trigger stop robot without cancel mission
        """
        if agv_codes.__len__() == 0:
            return True
        
        req = {
            "reqCode": self.__genReqCode(),
            "robotCount": len(agv_codes),
            "robots": agv_codes
        }
        
        try:
            res = RestApi.client.post(
                self.__url + RCS_URL_PATH.CMD_PAUSE,
                json=req,
                timeout=3
            )

            if res.status_code in HTTP_RESPONSE_CODE.OK:
                response = res.json()
                if response["code"] == RCS_SUCCESS_CODE:
                    return True
                
            self.__logger.warn(f"Pause robot fail: {res.content}")
        except Exception as e:
            self.__logger.error(f"Pause robot error: {e}")

        return False
    
    def resumeRobot(self, *agv_codes: str):
        """
        Trigger resume robot independent of mission
        """
        if agv_codes.__len__() == 0:
            return True
        
        req = {
            "reqCode": self.__genReqCode(),
            "robotCount": len(agv_codes),
            "robots": agv_codes
        }
        
        try:
            res = RestApi.client.post(
                self.__url + RCS_URL_PATH.CMD_RESUME,
                json=req,
                timeout=3
            )

            if res.status_code in HTTP_RESPONSE_CODE.OK:
                response = res.json()
                if response["code"] == RCS_SUCCESS_CODE:
                    return True
                
            self.__logger.warn(f"Resume robot fail: {res.content}")
        except Exception as e:
            self.__logger.error(f"Resume robot error: {e}")

        return False
    
    def cancelTask(self, task_code: str):
        """
        Trigger mission cancel
        """
        if task_code == "":
            return True
        
        req = {
            "reqCode": self.__genReqCode(),
            "forceCancel": "0",
            "taskCode": task_code
        }
        self.__logger.info(f"Cancel task req: {req}")
        
        try:
            res = RestApi.client.post(
                self.__url + RCS_URL_PATH.CMD_CANCEL,
                json=req,
                timeout=3
            )

            if res.status_code in HTTP_RESPONSE_CODE.OK:
                response = res.json()
                self.__logger.info(f"Cancel task res: {response}")
                if response["code"] == RCS_SUCCESS_CODE:
                    return True
                
            self.__logger.warn(f"Cancel task fail: {res.content}")
        except Exception as e:
            self.__logger.error(f"Cancel task error: {e}")

        return False
    
    def getTaskStatus(self, *task_codes: str) -> List[RCS_TASK_STATUS]:
        """
        Get task status (NOT USED)

        Return: [task status]
        """
        req = {
            "reqCode": self.__genReqCode(),
            "taskCodes": task_codes
        }
        self.__logger.info(f"Get task status req: {req}")
        
        try:
            res = RestApi.client.post(
                self.__url + RCS_URL_PATH.CMD_QUERY_TASK,
                json=req,
                timeout=3
            )

            if res.status_code in HTTP_RESPONSE_CODE.OK:
                response = res.json()
                self.__logger.info(f"Get task status res: {response}")
                if response["code"] == RCS_SUCCESS_CODE:
                    task_states = []
                    for data in response["data"]:
                        task_info = RCS_Task_Status_Res.fromDict(data)
                        task_states.append(task_info.taskStatus)
                    return task_states
                
            self.__logger.warn(f"Get task status fail: {res.content}")
        except Exception as e:
            self.__logger.error(f"Get task status error: {e}")

        return []
    
    def __genContainerCode(self):
        """
        Generate a random container code to bind to RCS location
        """
        second = str(time()).split(".")
        return second[0][-2:] + second[1][:5]
    
    def bindLoction(self, location: RCS_LOCATION, bind: bool = True):
        """
        Bind/Unbind rcs location
        """
        req = {
            "reqCode": self.__genReqCode(),
            "positionCode": location,
            "ctnrCode": self.__genContainerCode() if bind else "",
            "ctnrTyp": "1",
            "indBind": 1 if bind else 0
        }
        self.__logger.info(f"Bind location req: {req}")
        
        try:
            res = RestApi.client.post(
                self.__url + RCS_URL_PATH.CMD_BIND,
                json=req,
                timeout=3
            )

            if res.status_code in HTTP_RESPONSE_CODE.OK:
                response = res.json()
                self.__logger.info(f"Bind location res: {response}")
                if response["code"] == RCS_SUCCESS_CODE:
                    return True
                
            self.__logger.warn(f"Bind location fail: {res.content}")
        except Exception as e:
            self.__logger.error(f"Bind location error: {e}")

        return False
    
    def getTaskList(self, *task_codes: str) -> List[Mission_Model]:
        """
        Get list of task info and add to mission model (NOT USED)
        """
        req = {
            "reqCode": self.__genReqCode()
        }
        if task_codes:
            req["taskCodes"] = task_codes
        self.__logger.info(f"List task req: {req}")
        
        try:
            res = RestApi.client.post(
                self.__url + RCS_URL_PATH.CMD_TASK_LIST,
                json=req,
                timeout=3
            )

            if res.status_code in HTTP_RESPONSE_CODE.OK:
                response = res.json()
                self.__logger.info(f"List task res: {response}")
                if response["code"] == RCS_SUCCESS_CODE:
                    missions: List[Mission_Model] = []
                    for data in response["data"]:
                        task_info = RCS_Task_Status_Res.fromDict(data)
                        mission_info = Mission_Model()
                        mission_info.rcs_code = task_info.taskCode
                        mission_info.rcs_status = task_info.taskStatus
                        missions.append(mission_info)
                    return missions
                
            self.__logger.warn(f"List task fail: {res.content}")
        except Exception as e:
            self.__logger.error(f"List task error: {e}")

        return None
    
    def freeRobot(self, agv_code: str):
        """
        Trigger free robot
        """
        if agv_code == "":
            return True

        req = {
            "reqCode": self.__genReqCode(),
            "robotCode": agv_code
        }
        self.__logger.info(f"Free robot req: {req}")
        
        try:
            res = RestApi.client.post(
                self.__url + RCS_URL_PATH.CMD_FREE_ROBOT,
                json=req,
                timeout=3
            )

            if res.status_code in HTTP_RESPONSE_CODE.OK:
                response = res.json()
                self.__logger.info(f"Free robot res: {response}")
                if response["code"] == RCS_SUCCESS_CODE:
                    return True
                
            self.__logger.warn(f"Free robot fail: {res.content}")
        except Exception as e:
            self.__logger.error(f"Free robot error: {e}")

        return False
    
    def queryAgvStatus(self):
        """
        Get agvs destination

        Return:
        ```
        {
            [robot code]: ["x#y" | ""]
        }
        ```
        """
        req = {
            "reqCode": self.__genReqCode(),
            "mapcode": "AA", 
            "mapShortName": "AVN"  
        }
        
        try:
            res = RestApi.client.post(
                RCS_URL_PATH.URL_QUERY_AGV,
                json=req,
                timeout=3
            )

            if res.status_code in HTTP_RESPONSE_CODE.OK:
                response = res.json()
                if response["code"] == RCS_SUCCESS_CODE:
                    robot_datas: Dict[str, str] = {}
                    for raw in response["data"]:
                        data = RCS_Robot_Data_Res.fromDict(raw)
                        if data.path:
                            des_x, des_y = data.path[-1].replace("[", "").split(",")[:2]
                            robot_datas[data.robotCode] = des_x.zfill(6) + des_y.zfill(6)
                        else:
                            robot_datas[data.robotCode] = ""
                    return robot_datas
                
            self.__logger.warn(f"Query robot fail: {res.content}")
        except Exception as e:
            self.__logger.error(f"Query robot error: {e}")

        return {}

    def __onMissionFeedback(self, channel: str, feedback: RCS_Feedback_Req):
        """
        Emit any feedback from RCS in mission
        """
        db = Database_Interface()
        mission = db.getMissionByRcs(feedback.taskCode)
        if mission:
            signal = RCS_Notify_Signal()
            signal.mission_code = mission.code
            signal.agv_code = feedback.robotCode
            signal.flag = feedback.method
            Signal_Handle().emit(channel, signal)

    def __createApi(self, path: str, channel: str):
        """
        path: url path of DAL server
        channel: signal channel to emit
        """
        @RestApi.server.post(RCS_URL_PATH.FB_FIX_PATH + path)
        def onRCSFeedback(feedback: RCS_Feedback_Req):
            """
            RCS notification
            """
            self.__onMissionFeedback(channel, feedback)
    
    def __bindRCS(self, payload: Bind_RCS_Signal):
        """
        Bind location by backend request
        """
        for point in payload.points:
            self.bindLoction(point, payload.binded)
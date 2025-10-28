from .config import PWM_REGISTER, PWM_STATUS_VALUE, PWM_TRIGGER
from common import MODULE_NAME
from database.model.curtain import CURTAIN_LOCATION, CURTAIN_STATUS, Curtain_Status_Model
from database.model.pwm import PWM_MACHINE_STATUS, PWM_WRAP_STATUS
from database.com import Database_Interface

from rostek_utils.utils.logger import Logger
from rostek_utils.utils.thread import Worker
from rostek_utils.com.modbus import Modbus_Client
from time import sleep
from traceback import format_exc

class PWM_Interface:
    """
    Communicate with Pallet wrapping machine

    Kwargs:
        ip: (str) plc ip
        port: (int) plc modbus tcp port

    Interface:
        - trigger: Trigger start pwm
        - reset(self): Reset PWM after wrap done
        - controlLC: Control pwm light curtain
    """
    def __init__(self, **kwargs) -> None:
        self.__logger = Logger(MODULE_NAME.PWM)
        self.__db = Database_Interface()

        self.__conn = Modbus_Client()
        self.__conn.serve(
            type="TCP",
            host=kwargs.get("ip", "127.0.0.1"),
            port=kwargs.get("port", "502"),
            timeout=5
        )
        self.readLoop()

    @Worker.employ
    def readLoop(self):
        curtain_mapping = {
            PWM_STATUS_VALUE.CURTAIN_ON: CURTAIN_STATUS.ON,
            PWM_STATUS_VALUE.CURTAIN_OFF: CURTAIN_STATUS.OFF
        }
        wrap_mapping = {
            PWM_STATUS_VALUE.WRAP_BUSY: PWM_WRAP_STATUS.BUSY,
            PWM_STATUS_VALUE.WRAP_DONE: PWM_WRAP_STATUS.DONE
        }
        machine_mapping = {
            PWM_STATUS_VALUE.MACH_READY: PWM_MACHINE_STATUS.READY,
            PWM_STATUS_VALUE.MACH_WRAP: PWM_MACHINE_STATUS.WRAP,
            PWM_STATUS_VALUE.MACH_BYPASS: PWM_MACHINE_STATUS.BYPASS,
            PWM_STATUS_VALUE.MACH_MANUAL: PWM_MACHINE_STATUS.MANUAL
        }

        while 1:
            try:
                stt = self.__db.getPWMStatus()
                res = self.__conn.read(0, PWM_REGISTER.REG_MACHINE, 1, False)
                if res:
                    if res[0] in machine_mapping:
                        stt.machine_state = machine_mapping[res[0]]
                    else:
                        self.__logger.error(f"Wrong machine state of pwm at {PWM_REGISTER.REG_MACHINE} (require 1-4): {res}")

                res = self.__conn.read(0, PWM_REGISTER.REG_WRAP_DONE, 1, False)
                if res:
                    if res[0] in wrap_mapping:
                        stt.wrap_state = wrap_mapping[res[0]]
                    else:
                        self.__logger.error(f"Wrong wrap state of pwm at {PWM_REGISTER.REG_WRAP_DONE} (require 0-1): {res}")
                self.__db.updatePWMStatus(stt)

                stt = self.__db.getCurtainStatus(CURTAIN_LOCATION.PWM)[CURTAIN_LOCATION.PWM]
                res = self.__conn.read(0, PWM_REGISTER.REG_CURTAIN, 1, False)
                if res:
                    stt.status = curtain_mapping[res[0]]
                    self.__db.updateCurtainStatus(stt)
            except Exception as e:
                self.__logger.error(f"Error read pwm: {e}\n{format_exc()}")
            sleep(1)

    def trigger(self):
        """
        Trigger PWM to start wrapping 
        """
        self.__logger.info(f"Trigger PWM start")
        return self.__conn.write(0, PWM_REGISTER.REG_TRIG_WRAP, [PWM_TRIGGER.WRAP], False)

    def reset(self):
        """
        Reset PWM after wrap done
        """
        self.__logger.info(f"Trigger PWM reset")
        return self.__conn.write(0, PWM_REGISTER.REG_TRIG_RESET, [PWM_TRIGGER.RESET], False)

    def controlLC(self, status: Curtain_Status_Model):
        """
        Control PWM light curtain
        """
        self.__logger.info(f"Control PWM light curtain -> {status.status}")
        stt_mapping = {
            CURTAIN_STATUS.ON: PWM_TRIGGER.CURTAIN_ON,
            CURTAIN_STATUS.OFF: PWM_TRIGGER.CURTAIN_OFF,
        }
        return self.__conn.write(0, PWM_REGISTER.REG_TRIG_CURTAIN, [stt_mapping[status.status]], False)
# Setup logger
from rostek_utils.utils.logger import Logger
from common import MODULE_NAME

for name in MODULE_NAME.values():
    if name in [
        MODULE_NAME.SIGNAL, MODULE_NAME.DATABASE, MODULE_NAME.REDIS
    ]:
        Logger(name, to_screen=True)
        continue

    Logger(name, to_screen=False, to_file=True, file_name=f"../log/{name.lower()}")
Logger("THREAD", to_screen=False, to_file=True, file_name=f"../log/thread_error")
Logger(MODULE_NAME.LOGIC, to_screen=True, to_file=True, file_name=f"../log/logic")
Logger("MODBUS_CLIENT", to_screen=False, to_file=True, file_name=f"../log/modbus_client")
Logger("MQTT", to_screen=False, to_file=True, file_name=f"../log/mqtt")

from interface.ais.com import AIS_Interface
from interface.wcs.com import WCS_Interface
from interface.rcs.com import RCS_Interface
from interface.gateway.com import Gateway_Interface
from interface.pda.com import PDA_Interface
from logic.main import Main_Logic

# Init database (redis)
from database.com import Database_Interface
print("SETUP: Database")
Database_Interface()

# Init signal server (redis)
from signal_emit.com import Signal_Handle
print("SETUP: Signal")
Signal_Handle()

from time import sleep
import yaml

def main():
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    print("SETUP: AIS")
    ais = AIS_Interface(**config["ais"])
    print("SETUP: WCS")
    wcs = WCS_Interface(**config["wcs"])
    while not wcs.getToken():
        print("Wait for WCS")
        sleep(1)
    print("SETUP: RCS")
    rcs = RCS_Interface(**config["rcs"])
    print("SETUP: GATEWAY")
    gateway = Gateway_Interface(**config["gateway"])
    print("SETUP: PDA")
    pda = PDA_Interface(**config["pda"])

    print("SETUP: Start logic")
    m = Main_Logic(wcs, rcs, gateway, ais)
    while True:
        try:
            sleep(1)
        except KeyboardInterrupt:
            print("Manually exited!")
            break

if __name__ == "__main__":
    main()
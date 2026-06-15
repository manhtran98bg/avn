from config import stop_event, RCS_CONFIG
from database.redis_db import Redis_Handler
from database.db import Database

import requests, threading, logging
from time import time, sleep

class FetchRobotPositions(threading.Thread):
    """
    Auto query forklift position and status in RCS
    """
    def __init__(self):
        super().__init__(daemon=True)
        self.__redis = Redis_Handler()
        self.__db = Database()

    def run(self):
        """
        Runs FetchRobotPositions thread. Periodically sends a POST request
        to fetch robot positions and stores the data in Redis.
        """
        count = 0
        while not stop_event.is_set():
            try:
                url = f"{RCS_CONFIG.RCS_ADDRESS}"
                payload = {
                    "reqCode": f"AIS-{time()})", 
                    "mapcode": "AA",
                    "mapShortName": "AVN"  
                }

                response = requests.post(url, json=payload, timeout=2)
                response.raise_for_status() 

                res = response.json()
                if res["code"] == "0":
                    count = 0
                    robots_data = res["data"]
                    for robot_data in robots_data:
                        self.__redis.saveRobotData(robot_data["robotCode"], {
                            "posX": robot_data["posX"],
                            "posY": robot_data["posY"],
                            "status": robot_data["status"],
                            "path"  : robot_data["path"]
                        })
                        self.__db.updateRobotPosition(
                            robot_data["robotCode"], robot_data["posX"], robot_data["posY"])

                else:
                    count += 1
                    if count > 5:
                        logging.error(f"Disconnect to RCS")
                        count = 0
                    raise Exception(f"Error code from response: {robot_data['code']}")

            except Exception as e:
                logging.error(f"Error fetching data: {e}")
            sleep(0.05)
import requests
import datetime
import uuid

# Configuration for the RCS
RCS_ADDRESS = 'http://172.21.99.21:8182'
RCS_ADDRESS_STOP = 'http://172.21.99.21:8181'

class RobotManager:
    @staticmethod
    def generate_reqcode():
        return str(uuid.uuid4())

    @staticmethod
    def get_robot_positions():
        reqcode = RobotManager.generate_reqcode()
        url = f"{RCS_ADDRESS}/rcms-dps/rest/queryAgvStatus"
        payload = {
            "reqCode": reqcode,
            "mapcode": "AA",
            "mapShortName": "AVN"
        }
        response = requests.post(url, json=payload)
        return response.json()

    @staticmethod
    def stop_robots(robots):
        reqcode = RobotManager.generate_reqcode()
        url = f"{RCS_ADDRESS_STOP}/rcms/services/rest/hikRpcService/stopRobot"
        payload = {
            "reqcode": reqcode,
            "robots": [str(robot) for robot in robots],
            "robotCount": "1"
        }
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    @staticmethod
    def resume_robots(robots):
        reqcode = RobotManager.generate_reqcode()
        url = f"{RCS_ADDRESS_STOP}/rcms/services/rest/hikRpcService/resumeRobot"
        payload = {
            "reqcode": reqcode,
            "robots": [str(robot) for robot in robots],
            "robotCount": "1"
        }
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

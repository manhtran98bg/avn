from config import Config, WCSTopic, stop_event
from utils.threadpool import Worker
from database.redis_db import Redis_Handler
from database.db import Database
import api
import paho.mqtt.client as mqtt
import threading, logging, json
from datetime import datetime
from time import time, sleep

class SENDING_COOLDOWN:
    PAUSE_RESUME = 2
    RESUME_PAUSE = 0.3
    SCHEDULE = 5

class AGV_STATE:
    PAUSE = "pause"
    RESUME = "resume"
class WCS_STATUS:
    CONNECTED = "Connected"
    DISCONNECTED = "Disconnected"

class WCS_Handler(threading.Thread):
    """
    Thread responsible for publishing MQTT messages based on robot statuses.
    status_list:
    {
        [pause | resume]:
        {
            [robot code]:
            [{
                "camera_id": "E-19", # Camera detected
                "object_class": "Class 0", # Obstacle trigger pause
                "distance": 35.23 (float) # in cm
            }]
        }
    }
    """
    def __init__(self):
        super().__init__()
        
        self.__redis = Redis_Handler()
        self.__db = Database()

        self.__mqtt = mqtt.Client()
        self.__mqtt.username_pw_set(username=Config.MQTT_USERNAME_WCS, password=Config.MQTT_PASSWORD_WCS)
        self.__mqtt.on_connect = self.__onConnect
        self.__mqtt.on_message = self.__onMessage

        self.__status_list = {}
        self.__robot_status = {}
        self.__wcs_last_status = None
        self.__wcs_last_connect = time()

        self.connect()
        self.__checkWcsTimeOut()
        self.__sendHeartbeat()
        
    def __onConnect(self, userdata, flags, rc,properties=None):
        """
        Callback function when the client connects to the MQTT broker.
        """
        self.__mqtt.subscribe(WCSTopic.WCS_STATUS_TOPIC)

    def __onMessage(self, client, userdata, message):
        """
        Callback function when a message is received from the MQTT broker.
        """
        try:
            if message.topic == WCSTopic.WCS_STATUS_TOPIC:
                self.__wcs_last_connect = time()
                if self.__wcs_last_status != WCS_STATUS.CONNECTED:
                    self.__db.saveStatusWcs(WCS_STATUS.CONNECTED)
                    logging.info(f" WCS_Handler :Status Wcs: {WCS_STATUS.CONNECTED}")    
                    self.__wcs_last_status = WCS_STATUS.CONNECTED

        except Exception as e:
            logging.error(f" WCS_Handler :Error in onMessage method: {e}")

    @Worker.employ
    def __checkWcsTimeOut(self):
        """
        Check WCS connection status every 5 seconds and save to database
        """
        while not stop_event.is_set():
            try:
                if time() - self.__wcs_last_connect > 5:
                    if self.__wcs_last_status != WCS_STATUS.DISCONNECTED:
                        self.__db.saveStatusWcs(WCS_STATUS.DISCONNECTED)
                        logging.info(f" WCS_Handler :Status Wcs: {WCS_STATUS.DISCONNECTED}")
                        self.__wcs_last_status = WCS_STATUS.DISCONNECTED
            except Exception as e:
                logging.error(f" WCS_Handler :Error checking WCS status: {e}")
            sleep(2)

    @Worker.employ
    def __sendHeartbeat(self):
        """
        Send a heartbeat message to the WCS every 5 seconds to maintain connection
        """
        heartbeat_id = 0
        while not stop_event.is_set():
            try:
                if self.__mqtt.is_connected():
                    heartbeat_id += 1
                    heartbeat_message = {
                        "heartbeat": True,
                        "timestamp": time(),
                        "sequence": heartbeat_id
                    }
                    self.__mqtt.publish(WCSTopic.WCS_HEARTBEAT_TOPIC, json.dumps(heartbeat_message), qos=1)
                    logging.info(f"WCS_Handler: Sent heartbeat #{heartbeat_id} to WCS")
            except Exception as e:
                logging.error(f"WCS_Handler: Error sending heartbeat: {e}")
            sleep(5)

    @Worker.employ
    def connect(self):
        """
        Connect to mqtt broker with WCS
        """
        while not stop_event.is_set():
            try:
                self.__mqtt.connect(Config.MQTT_BROKER_WCS, Config.MQTT_PORT_WCS)
                self.__mqtt.loop_start()
                sleep(1)

                while not stop_event.is_set():
                    if self.__mqtt.is_connected():
                        sleep(3)
                        continue

                    try:
                        print("Herer============================")
                        self.__mqtt.loop_stop()
                        self.__mqtt.reconnect()
                        self.__mqtt.loop_start()
                        sleep(1)
                    except Exception as e:
                        logging.error(f" WCS_Handler :Connect mqtt broker wcs fail host {Config.MQTT_BROKER_WCS},  port {Config.MQTT_PORT_WCS}: {e}")
            except Exception as e:
                logging.error(f" WCS_Handler :Unexpected error in connect method: {e}")
                sleep(0.5)
    
    def run(self):
        """
        Periodically checks and sends MQTT messages based on robot status.

        Method runs continuously, checking for status changes and sending MQTT messages
        """
        while not stop_event.is_set():
            try:
                self.__status_list = self.__redis.getCombinedStatus()
                # print(self.__status_list)
                
                # Check for immediate status changes
                changed_list = self.__getChangeList()
                
                if changed_list[AGV_STATE.PAUSE] or changed_list[AGV_STATE.RESUME]:
                    self.__pubStatus(changed_list)
                    self.__saveStatus(changed_list)
                
            except Exception as e:
                logging.error(f" WCS_Handler :Error in MQTTPublisherThread: {e}")
            sleep(0.1)

    def __getChangeList(self):
        """
        Retrieves current robot status from Redis and processes any immediate changes.
            
        Return: changed_list (dict): list of pause/resume robot codes
        """
        changed_list = {
            AGV_STATE.PAUSE: [],
            AGV_STATE.RESUME: []
        }
        
        current_time = time()

        for status_type in changed_list:
            robot_list = self.__status_list.get(status_type, {})
            
            for robot_code in robot_list:
                last_status, _, sended = self.__robot_status.get(robot_code, [None, 0, True])

                if last_status != status_type:
                    self.__robot_status[robot_code] = [status_type, current_time, not sended]
                
                last_status, last_change_time, sended = self.__robot_status[robot_code]
                if not sended and (
                    last_status == AGV_STATE.RESUME
                        and current_time - last_change_time > SENDING_COOLDOWN.PAUSE_RESUME\
                    or last_status == AGV_STATE.PAUSE\
                        and current_time - last_change_time > SENDING_COOLDOWN.RESUME_PAUSE
                ):
                    changed_list[status_type].append(robot_code)
                    self.__robot_status[robot_code][2] = True
        return changed_list

    def __pubStatus(self, status_list: dict):
        """
        Publish agv states to WCS
        """
        if not self.__mqtt.is_connected():
            return False

        change_list = status_list.copy()
        change_list["normal"] = change_list.pop(AGV_STATE.RESUME)
        
        try:
            msg = json.dumps(change_list)
            self.__mqtt.publish(WCSTopic.AGV_STATUS_TOPIC, msg, 2)                 
            logging.info(f" WCS_Handler :Send: time={time()}, msg={msg}")
            self.__last_send = time()
            return True
        except Exception as e:
            logging.error(f" WCS_Handler :Error sending MQTT message: {e}")
            return False

    def __saveStatus(self, status_list: dict):
        """
        Saves the status history to the AIS database.

        Args:
            payload (dict): payload containing the status information.
            current_time (datetime): current time for timestamping the records.
        """
        try:
            for status_type, robots in status_list.items():
                for robot_code in robots:
                    for entry in self.__status_list[status_type][robot_code]:
                        record = {
                            'camera_id': entry.get('camera_id'),
                            'robot_code': robot_code,
                            'object_class': entry.get('object_class'),
                            'distance': entry.get('distance'),
                            'action': status_type,
                            'created_at': datetime.now().isoformat()
                        }
                        Database().updateHistoryAction(record)

        except Exception as e:
            logging.error(f" WCS_Handler : WCS_Handler :Error saving status history to database: {e}")
from config import Config, stop_event, CollectionName
from utils.threadpool import Worker
from database.db import Database
from database.redis_db import Redis_Handler

import paho.mqtt.client as mqtt_client
import threading, logging, json
from datetime import datetime
from time import time, sleep

EDGE_CONNECTION_TIMEOUT =4

class CAMERA_CONNECTION_STATE:
    YES = "connected"
    NO = "disconnected"

class EDGE_CONNECTION_STATE:
    YES = "connected"
    NO = "disconnected"

class EDGE_MQTT_TOPIC:
    MERGED = "merged_topic"
    STATUS = "status_topic"
    EDGE = "edge_status"
    BLUR = "check_blur_topic"

class Edge_Handler(threading.Thread):
    """
    Thread responsible for reading data from edges.

    Subscribe from edge:
    - merged_topic: read detected objects
    {
        [camera id]:
        {
            "cls": [ Class 0, 1, 2 ],
            "bbox": [ ((x1, y1), (x2, y2)) ]
        }
    }
    - status_topic: get camera connection
    {
        [camera id]: "connected" / "disconnected"
    }
    - edge_status: get edge connection
    {
        [edge id]: "connected" (5s timeout -> disconnected)
    }
    - check_blur_topic: get camera blur status
    {
        [camera id]: "blur" / "normal"
    }

    Save to redis:
    - merged topic message

    Save to mongo:
    - update camera, edge status (camera connection, edge connection, camera blur)
    """
    mqtt = mqtt_client.Client()

    def __init__(self):
        super().__init__()
        Edge_Handler.mqtt.on_connect = self.__onConnect
        Edge_Handler.mqtt.on_message = self.__onMessage

        self.__db = Database()
        self.__redis = Redis_Handler()
        self.__logger = logging.Logger("Edge_Handler")

        self.__edge_last_connect = {}
        self.__blur_data = {}
      

        self.__connect()
        self.__checkEdgeTimeout()

    @Worker.employ
    def __checkEdgeTimeout(self):
        """
        Periodically check the status of edge devices and update their status if they are disconnected.
        """
        if not hasattr(self, "__edge_connection_status"):
            self.__edge_connection_status = {}

        while not stop_event.is_set():
            current_time = time()

            try:
                all_edges = self.__db.db[CollectionName.AI_EDGE_CONFIG].find({}, {"ip": 1})
                all_edge_ids = [edge["ip"] for edge in all_edges]

                for edge_id in all_edge_ids:
                    # Kiểm tra xem edge có trong danh sách đã kết nối không
                    if edge_id in self.__edge_last_connect:
                        # Nếu edge đã kết nối, kiểm tra xem đã quá thời gian timeout chưa
                        if current_time - self.__edge_last_connect[edge_id] >= EDGE_CONNECTION_TIMEOUT:
                            # Nếu quá thời gian timeout, cập nhật trạng thái ngắt kết nối
                            if self.__edge_connection_status.get(edge_id) != EDGE_CONNECTION_STATE.NO:
                                logging.warning(
                                    "Edge timeout -> disconnected: edge_id=%s at=%s (last_seen=%.3f, now=%.3f)",
                                    edge_id,
                                    datetime.now().isoformat(timespec="seconds"),
                                    self.__edge_last_connect[edge_id],
                                    current_time
                                )
                                self.__db.updateEdgeStatus(edge_id, EDGE_CONNECTION_STATE.NO)
                                camera_ids = self.__db.getCameraByEdge(edge_id)
                                for camera_id in camera_ids:
                                    self.__db.updateCameraStatus(camera_id, CAMERA_CONNECTION_STATE.NO)
                                self.__edge_connection_status[edge_id] = EDGE_CONNECTION_STATE.NO
                        else:
                            # Nếu chưa quá thời gian timeout, đảm bảo trạng thái là kết nối
                            if self.__edge_connection_status.get(edge_id) != EDGE_CONNECTION_STATE.YES:
                                logging.info(
                                    "Edge reconnected: edge_id=%s at=%s",
                                    edge_id,
                                    datetime.now().isoformat(timespec="seconds")
                                )
                                self.__db.updateEdgeStatus(edge_id, EDGE_CONNECTION_STATE.YES)
                                camera_ids = self.__db.getCameraByEdge(edge_id)
                                self.__edge_connection_status[edge_id] = EDGE_CONNECTION_STATE.YES
                    else:
                        # Nếu edge không có trong danh sách đã kết nối, kiểm tra xem đã được đánh dấu là ngắt kết nối chưa
                        if self.__edge_connection_status.get(edge_id) != EDGE_CONNECTION_STATE.NO:
                            logging.warning(
                                "Edge not connected -> disconnected: edge_id=%s at=%s",
                                edge_id,
                                datetime.now().isoformat(timespec="seconds")
                            )
                            self.__db.updateEdgeStatus(edge_id, EDGE_CONNECTION_STATE.NO)
                            camera_ids = self.__db.getCameraByEdge(edge_id)
                            for camera_id in camera_ids:
                                self.__db.updateCameraStatus(camera_id, CAMERA_CONNECTION_STATE.NO)
                            self.__edge_connection_status[edge_id] = EDGE_CONNECTION_STATE.NO
            except Exception as e:
                logging.error(f"Error checking edge connections: {e}")

            sleep(1)
    @Worker.employ
    def __connect(self):
        """
        Connect to mqtt broker with WCS
        """
        Edge_Handler.mqtt.connect(Config.MQTT_BROKER, Config.MQTT_PORT)
        Edge_Handler.mqtt.loop_start()
        sleep(1)

        while not stop_event.is_set():
            if Edge_Handler.mqtt.is_connected():
                sleep(3)
                continue

            try:
                Edge_Handler.mqtt.loop_stop()
                Edge_Handler.mqtt.reconnect()
                Edge_Handler.mqtt.loop_start()
            except Exception as e:
                logging.error(f"Connect mqtt broker fail host {Config.MQTT_BROKER}, Port: {Config.MQTT_PORT} : {e}")
            sleep(1)

    def __onConnect(self, client: mqtt_client.Client, userdata, flags, rc):
        """
        Callback function when the client connects to the MQTT broker.
        """
        client.subscribe(EDGE_MQTT_TOPIC.MERGED)
        client.subscribe(EDGE_MQTT_TOPIC.STATUS)
        client.subscribe(EDGE_MQTT_TOPIC.EDGE)
        client.subscribe(EDGE_MQTT_TOPIC.BLUR)

    def __onMessage(self, client: mqtt_client.Client, userdata, message: mqtt_client.MQTTMessage):
        """
        Callback function when a message is received from the MQTT broker.
        """
        try:
            # logging.info(f"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
            payload: dict = json.loads(message.payload.decode())
            # logging.info(f" message . {payload}")
            if message.topic == EDGE_MQTT_TOPIC.MERGED:
                for camera_id in payload:
                    self.__redis.saveDetection(camera_id, payload[camera_id])

            elif message.topic == EDGE_MQTT_TOPIC.STATUS:
                for camera_id in payload:
                    status: str = payload[camera_id]["connect_status"]
                    self.__db.updateCameraStatus(camera_id, status)
                

            elif message.topic == EDGE_MQTT_TOPIC.EDGE:
                for edge_id in payload:
                    self.__db.updateEdgeStatus(edge_id, EDGE_CONNECTION_STATE.YES)
                    self.__edge_last_connect[edge_id] = time()

                    # Cập nhật trạng thái trong biến theo dõi
                    if hasattr(self, "__edge_connection_status"):
                        self.__edge_connection_status[edge_id] = EDGE_CONNECTION_STATE.YES

            elif message.topic == EDGE_MQTT_TOPIC.BLUR:
                for camera_id in payload:
                    status = payload[camera_id]["status"]
                    var = payload[camera_id]["var"]
                    current = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

                    if camera_id in self.__blur_data:
                        self.__blur_data[camera_id]["blur_status"] = status
                        self.__blur_data[camera_id]["blur_var"] = var
                        self.__blur_data[camera_id]["updated_at"] = current
                        self.__blur_data[camera_id]["created_at"] = current
                    else:
                        self.__blur_data[camera_id] = {
                            "blur_status": status,
                            "blur_var": var,
                            "created_at": current,
                            "updated_at": current
                        }
                    self.__redis.setBlurStatus(self.__blur_data)
                    # self.__db.insertCameraBlur(self.__blur_data[camera_id])
        except Exception as e:
            logging.error(f"Error processing message: {e}")
    @classmethod
    def publish(cls, topic: str, message: dict):
        try:
            cls.mqtt.publish(topic, json.dumps(message)).wait_for_publish(1)
        except Exception as e:
            logging.error(f"Publish to edge error: {e}")

import paho.mqtt.client as mqtt
from time import sleep
from typing import Callable, Type
import weakref
import sys 
sys.path.append('ai_server')
from utils.logger import Logger
from utils.threadpool import ThreadPool

class MqttMessage:
    """
    Mqtt message class format
    """
    def __init__(self, topic: str):
        self.topic = topic

    def create_message(self) -> str:
        """
        Combine all properties to form a json string message
        """
        raise NotImplementedError("Subclasses should implement this method.")


class MqttClient:
    """
    MQTT client for connecting to a broker, publishing, subscribing, and handling callbacks.
    """
    def __init__(self, client_id: str, broker: str, port: int = 1883, user: str = None, password: str = None):
        self.client_id = client_id
        self.broker = broker
        self.port = port
        self.user = user
        self.password = password
        self.logger = Logger()
        self.__client = None
        self.__topics = {}
        self.__callbacks = {}
        self.__common_callback = None
        self.is_connected = False
        self.__need_connect = True
        self.__create_client()

    def __create_client(self):
        self.__client = mqtt.Client(self.client_id, protocol=mqtt.MQTTv311)
        if self.user and self.password:
            self.__client.username_pw_set(self.user, self.password)
        self.__client.on_connect = self.__on_connect
        self.__client.on_message = self.__on_message


    def start_connection(self, reconnect_interval: float = 3):
        """
        Start connection loop, call once only
        """
        weak_self = weakref.ref(self)
        ThreadPool().add_task(MqttClient.__connect, weak_self, reconnect_interval)

    @staticmethod
    def __connect(weak_self: Type["MqttClient"], reconnect_interval: float):
        """
        Will try to connect forever, need new thread
        """
        while True:
            self = weak_self()
            if not self:
                break
            
            if self.__client and not self.__client.is_connected():
                self.is_connected = False
            
            if not self.is_connected and self.__need_connect:
                if not self.__client:
                    self.__create_client()
                else:
                    self.__client.loop_stop()
                    self.__client.disconnect()

                try:
                    self.__client.connect(self.broker, self.port)
                    self.__client.loop_start()
                    self.__resubscribe()
                    self.is_connected = True
                except Exception as e:
                    self.logger.error(f"Failed to connect to broker: {e}")

            self = None
            sleep(reconnect_interval)

    def __on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.is_connected = True
        else:
            self.logger.error(f"Connection failed with result code {rc}")

    def wait_connection(self, debug_text: str = "") -> None:
        """
        Block until connection is setup
        """
        while not self.is_connected:
            if debug_text:
                self.logger.info(debug_text)
            sleep(0.5)

    def disconnect(self):
        """
        Disconnect from broker and clean up client resources.
        """
        self.__need_connect = False
        self.is_connected = False
        if self.__client:
            self.__client.loop_stop()
            self.__client.disconnect()
            self.__client = None
        self.__topics.clear()
        self.__callbacks.clear()
        self.__common_callback = None

    def reconnect(self):
        """
        Reconnect to broker.
        """
        self.__need_connect = True

    def publish(self, message: MqttMessage, qos: int = 0) -> int:
        """
        Publish a message to a topic.
        """
        if not self.is_connected:
            return -2
        
        topic = message.topic
        msg = message.create_message()
        try:
            res_info = self.__client.publish(topic, msg, qos=qos)
            res_info.wait_for_publish(2)
            return 0
        except Exception as e:
            self.logger.error(f"Failed to publish message: {e}")
            return -1

    def set_common_callback(self, func: Callable):
        """
        Set a common callback function for topics without specific callbacks.
        """
        self.__common_callback = func
    
    def subscribe(self, topic: str, qos: int = 0, callback: Callable = None):
        """
        Subscribe to a topic with an optional callback function.
        """
        self.__topics[topic] = qos
        self.__callbacks[topic] = callback

    def __resubscribe(self):
        """
        Resubscribe to topics after reconnecting.
        """
        for topic in self.__topics:
            self.__client.subscribe(topic, qos=self.__topics[topic])

    def unsubscribe(self, topic: str):
        """
        Unsubscribe from a topic.
        """
        self.__topics.pop(topic, None)
        self.__callbacks.pop(topic, None)
        self.__client.unsubscribe(topic)

    def __on_message(self, client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
        """
        Process incoming messages and invoke appropriate callbacks.
        """
        topic = msg.topic
        message = msg.payload.decode()

        if topic in self.__callbacks and self.__callbacks[topic]:
            self.__callbacks[topic](self.client_id, topic, message)
        elif self.__common_callback:
            self.__common_callback(self.client_id, topic, message)

    def __del__(self):
        """
        Cleanup upon deletion of the object.
        """
        self.logger.info(f"MqttClient instance {self.client_id} is deleted")
        self.disconnect()

#  python tools/train.py  --epochs 50  --batch-size 32  --conf configs/yolov6n_finetune.py  --data data/data.yaml  --write_trainbatch_tb  --device 0,1  --eval-interval 1  --img-size 640  --name v6n_32b_640img_100e_reducedlabel
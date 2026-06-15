from config import stop_event

import json
import paho.mqtt.client as mqtt
import logging
from utils.threadpool import Worker
from time import sleep

class MqttClient:
    def __init__(self, host, port, topic):
        self.host = host
        self.port = port
        self.topic = topic
        self.client = mqtt.Client()
        self._setup_callbacks()
        self.connect()

    def _setup_callbacks(self):
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message  

    @Worker.employ
    def connect(self):
        while not stop_event.is_set():
            if self.client.is_connected():
                logging.info("Connected to MQTT broker in AIS")
                sleep(3)
                continue

            logging.info(f"Connecting to broker {self.host}:{self.port}")
            try:
                self.client.connect(self.host, self.port)
                self.client.loop_start() 
            except Exception as e:
                logging.error(f"Error connecting to MQTT broker: {e}")
            sleep(1)

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info(f"Connected OK Returned code: {rc}")
        else:
            logging.info(f"Bad connection Returned code: {rc}")

    def subscribe(self, topic):
        logging.info(f'Subscribing to topic {topic}')
        try:
            self.client.subscribe(topic)
        except Exception as e:
            logging.error(f"Error subscribing to topic: {e}")

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            logging.warning("Disconnected from MQTT broker. Trying to reconnect...")
            self.connect()

    def publish(self, topic, data,qos, retain=False):
        try:
            payload_json = json.dumps(data)
            result=self.client.publish(topic, payload_json, qos, retain)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logging.info(f"Successfully published message to topic {topic}")
                return True
            else:
                logging.error(f"Failed to publish message to topic {topic}, return code {result.rc}")
                return False
            
        except Exception as e:
            logging.error(f"Error publishing MQTT message: {e}")
            return False

    def _on_message(self, client, userdata, message):
        logging.info(f"Received message on topic {message.topic}: {message.payload}")

    def set_on_message_callback(self, callback):
        self.client.on_message = callback

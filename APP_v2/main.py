from config import Config, KeyRedis, RCS_CONFIG, WCSTopic, stop_event
from process_data import DistanceCalculator
from transformer import DataTransformer
from rcs_reader import FetchRobotPositions
from wcs_sender import WCS_Handler
from edge_com import Edge_Handler
from api import FlaskAppThread
from redis_clear_data import clear_redis_data

from threading import Thread
import logging
import os
import platform
import sys
from typing import List

LOG_FILE = "syslog.txt"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_FILE, mode="a"),
        logging.StreamHandler(sys.stdout),
    ],
)

def _log_startup_info():
    logging.info("========== AIS APP STARTING ==========")
    logging.info("Process info: pid=%s cwd=%s log_file=%s", os.getpid(), os.getcwd(), os.path.abspath(LOG_FILE))
    logging.info("Runtime info: python=%s platform=%s", sys.version.replace("\n", " "), platform.platform())
    logging.info("Redis config: host=%s port=%s db=%s", Config.REDIS_HOST, Config.REDIS_PORT, Config.REDIS_DB)
    logging.info(
        "Mongo config: host=%s port=%s document=%s user=%s",
        Config.ADDRESS_SERVER,
        Config.PORT_DB,
        Config.DOCCOMENT,
        Config.USER_NAME_DB,
    )
    logging.info("RCS config: address=%s", RCS_CONFIG.RCS_ADDRESS)
    logging.info("Edge MQTT config: broker=%s port=%s", Config.MQTT_BROKER, Config.MQTT_PORT)
    logging.info(
        "WCS MQTT config: broker=%s port=%s username=%s topics=(agv_status=%s,wcs_status=%s,heartbeat=%s)",
        Config.MQTT_BROKER_WCS,
        Config.MQTT_PORT_WCS,
        Config.MQTT_USERNAME_WCS,
        WCSTopic.AGV_STATUS_TOPIC,
        WCSTopic.WCS_STATUS_TOPIC,
        WCSTopic.WCS_HEARTBEAT_TOPIC,
    )
    logging.info("Flask config: host=%s port=%s", Config.FLASK_HOST, Config.FLASK_PORT)
    logging.info(
        "Redis keys: robot=%s object=%s detections=%s combined_status=%s ai_status=%s",
        KeyRedis.ROBOT_POSITION_DATA,
        KeyRedis.OBJECT_POSITION_DATA,
        KeyRedis.MERGED_DATA_AI_EDGE,
        KeyRedis.REDIS_KEY_COMBINED_STATUS,
        KeyRedis.TURN_ON_AI,
    )

class ThreadManager:
    def __init__(self):
        self.threads: List[Thread] = []

    def add_thread(self, thread_class, name, *args):
        logging.info("Registering thread %s (%s)", name, thread_class.__name__)
        thread: Thread = thread_class(*args)
        thread.name = name
        thread.daemon = True 
        self.threads.append(thread)
        return thread

    def start_all(self):
        logging.info("Starting %s worker thread(s)", len(self.threads))
        for thread in self.threads:
            logging.info(f"Starting thread {thread.name}")
            thread.start()
            logging.info("Thread %s started ident=%s alive=%s", thread.name, thread.ident, thread.is_alive())

    def stop_all(self):
        logging.info("Stopping all threads...")
        stop_event.set() 
        for thread in self.threads:
            logging.info(f"Wait for thread {thread.name} to stopped.")
            thread.join()
            logging.info(f"Thread {thread.name} has stopped.")

if __name__ == "__main__":
    thread_manager = None
    try:
        _log_startup_info()
        logging.info("Clearing Redis startup data")
        clear_redis_data()
        logging.info("Redis startup data cleared")
        thread_manager = ThreadManager()
        thread_manager.add_thread(FetchRobotPositions, "FetchRobotPositions")
        thread_manager.add_thread(Edge_Handler, "Edge_Handler")
        thread_manager.add_thread(DataTransformer, "DataTransformer")
        thread_manager.add_thread(DistanceCalculator, "DistanceCalculator")
        thread_manager.add_thread(WCS_Handler,"WCS_Handler")
        thread_manager.start_all()

        logging.info("Starting Flask app thread host=%s port=%s", Config.FLASK_HOST, Config.FLASK_PORT)
        main_thread = FlaskAppThread()
        main_thread.run()
        logging.info("KeyboardInterrupt received, stopping all threads...")
        thread_manager.stop_all()

    except Exception as e:
        logging.exception(f"An error occurred: {e}")
        if thread_manager:
            thread_manager.stop_all()

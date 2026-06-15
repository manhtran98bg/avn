from config import stop_event
from process_data import DistanceCalculator
from transformer import DataTransformer
from rcs_reader import FetchRobotPositions
from wcs_sender import WCS_Handler
from edge_com import Edge_Handler
from api import FlaskAppThread
from redis_clear_data import clear_redis_data

from threading import Thread
import logging
from typing import List

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename="logs3.txt",
                    filemode="a")

class ThreadManager:
    def __init__(self):
        self.threads: List[Thread] = []

    def add_thread(self, thread_class, name, *args):
        thread: Thread = thread_class(*args)
        thread.name = name
        thread.daemon = True 
        self.threads.append(thread)
        return thread

    def start_all(self):
        for thread in self.threads:
            logging.info(f"Starting thread {thread.name}")
            thread.start()

    def stop_all(self):
        logging.info("Stopping all threads...")
        stop_event.set() 
        for thread in self.threads:
            logging.info(f"Wait for thread {thread.name} to stopped.")
            thread.join()
            logging.info(f"Thread {thread.name} has stopped.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        clear_redis_data()
        thread_manager = ThreadManager()
        thread_manager.add_thread(FetchRobotPositions, "FetchRobotPositions")
        thread_manager.add_thread(Edge_Handler, "Edge_Handler")
        thread_manager.add_thread(DataTransformer, "DataTransformer")
        thread_manager.add_thread(DistanceCalculator, "DistanceCalculator")
        thread_manager.add_thread(WCS_Handler,"WCS_Handler")
        thread_manager.start_all()

        main_thread = FlaskAppThread()
        main_thread.run()
        logging.info("KeyboardInterrupt received, stopping all threads...")
        thread_manager.stop_all()

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        thread_manager.stop_all()
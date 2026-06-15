from utils.logger import Logger
from utils.pattern import Singleton

from queue import Queue
from threading import Thread
from typing import Callable, Dict, Tuple

class Worker(Thread):
    """Thread executing tasks from a given tasks queue"""
    def __init__(self, tasks: Queue):
        self.__logger = Logger()
        Thread.__init__(self)
        self.__tasks = tasks
        self.daemon = True
        self.start()
    
    def run(self):
        while True:
            func, args, kwargs = self.__tasks.get()
            try:
                func(*args, **kwargs)
            except Exception as e:
                if self.__logger:
                    self.__logger.error(f"[{func}({args}, {kwargs})] "
                                        f"Process died (Message: {e})")
            self.__tasks.task_done()
            func, args, kwargs = (None, None, None)

    @staticmethod
    def employ(func: Callable):
        def inner(*args, **kwargs):
            task_queue = Queue(1)
            task_queue.put((func, args, kwargs))
            Worker(task_queue)
        return inner

class ThreadPool(metaclass=Singleton):
    """Pool of threads consuming tasks from a queue"""
    def __init__(self, num_threads: int = 7):
        self.__tasks = Queue()
        for _ in range(num_threads):
            Worker(self.__tasks)

    def add_task(self, func: Callable, *args: Tuple, **kwargs: Dict):
        """Add a task to the queue"""
        self.__tasks.put((func, args, kwargs))

    def wait_completion(self):
        """Wait for completion of all the tasks in the queue"""
        self.__tasks.join()

from config import Config, KeyRedis
from utils.pattern import Singleton

import redis, json
from typing import Dict
import logging
class Redis_Handler(metaclass=Singleton):
    """
    Save and load from redis database methods (Singleton)
    """
    def __init__(self):
        self.__conn = redis.StrictRedis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, db=Config.REDIS_DB)

    def get(self, key: str) -> dict:
        data = self.__conn.get(key)
        if data:
            return json.loads(data)
        else:
            return {}
    
    def save(self, key: str, data: dict):
        self.__conn.set(key, json.dumps(data))
    
    def getCombinedStatus(self) -> dict:
        """
        ```
        {
            "pause":
            [{
                [robot code]:
                {
                    'camera_id': str (E-19),
                    'object_class': str (Class 0),
                    'distance': float (3000 mm),
                }
            }]
            "resume": [ [robot code] ]
        }
        ```
        """
        return self.get(KeyRedis.REDIS_KEY_COMBINED_STATUS)

    def getBlurStatus(self):
        """
        {
            "blur_status": blue status,
            "blur_var": blur value,
            "created_at": created datetime,
            "updated_at": last update datetime
        }
        """
        return self.get(KeyRedis.BLUR_STATUS)

    def setBlurStatus(self, record: dict):
        """
        {
            "blur_status": blue status,
            "blur_var": blur value,
            "created_at": created datetime,
            "updated_at": last update datetime
        }
        """
        self.save(KeyRedis.BLUR_STATUS, record)
    
    def getDetections(self):
        """
        Get all detections
        ```
        {
            [camera id]:
            {
                "cls": [ [Detected object class] ],
                "bbox": [ ([x_left, y_top], [x_right, y_bottom]) ]
            }
        }
        ```
        """
        data: Dict[bytes, bytes] = self.__conn.hgetall(KeyRedis.MERGED_DATA_AI_EDGE)
        detections = {}
        for enc_camera_id in data:
            detections[enc_camera_id.decode()] = json.loads(data[enc_camera_id].decode())
        return detections
    
    def getRobotData(self):
        """
        Get all forklifts status and position
        ```
        {
            [robot code]:
            {
                "posX": robot x position,
                "posY": robot y position,
                "status": robot status (config.FMR_STATUS)
            }
        }
        ```
        """
        data: Dict[bytes, bytes] = self.__conn.hgetall(KeyRedis.ROBOT_POSITION_DATA)
        robots_data = {}
        for enc_robot_code in data:
            robots_data[enc_robot_code.decode()] = json.loads(data[enc_robot_code].decode())
        return robots_data
    
    def getObjectData(self):
        """
        Get all objects data after calculated position
        ```
        {
            [camera id]:
            {
                "cls": [ [Detected object class] ],
                "x": [ [object x position] ],
                "y": [ [object y position] ]
            }
        }
        ```
        """
        data: Dict[bytes, bytes] = self.__conn.hgetall(KeyRedis.OBJECT_POSITION_DATA)
        objects_data = {}
        for enc_camera_id in data:
            objects_data[enc_camera_id.decode()] = json.loads(data[enc_camera_id].decode())
        return objects_data
    
    def saveCombinedStatus(self, status: dict):
        """
        ```
        {
            "pause":
            [{
                [robot code]:
                {
                    'camera_id': str (E-19),
                    'object_class': str (Class 0),
                    'distance': float (3000 mm),
                }
            }]
            "resume": [ [robot code] ]
        }
        ```
        """
        self.save(KeyRedis.REDIS_KEY_COMBINED_STATUS, status)
    
    def saveDetection(self, camera_id: str, object_data: dict):
        """
        Save detection data from edge
        """
        self.__conn.hset(KeyRedis.MERGED_DATA_AI_EDGE, camera_id, json.dumps(object_data))
    
    def saveSatusAISystem(self, status):
        """
        """
        self.save(KeyRedis.TURN_ON_AI, status)
        
    def getSatusAISystem(self):
        """
    
        """
        return self.get(KeyRedis.TURN_ON_AI)

    
    def saveRobotData(self, robot_code: str, robot_data: dict):
        """
        Save forklift status and position
        ```
        {
            "posX": robot x position,
            "posY": robot y position,
            "status": robot status (config.FMR_STATUS)
        }
        ```
        """
        try:
            self.__conn.hset(KeyRedis.ROBOT_POSITION_DATA, robot_code, json.dumps(robot_data))
        except Exception as e:
            logging.error(f"Error save robot data: {e}")
    
    def saveObjectData(self, camera_id: str, object_data: dict):
        """
        Save object with postion after calculate
        ```
        {
            "cls": [ [object class] ],
            "x": [ [robot x position] ],
            "y": [ [robot y position] ]
        }
        ```
        """
        self.__conn.hset(KeyRedis.OBJECT_POSITION_DATA, camera_id, json.dumps(object_data))

    def delete(self, *names: str):
        self.__conn.delete(*names)
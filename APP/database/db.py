from utils.pattern import Singleton

from pymongo import MongoClient
from config import Config, CollectionName
import logging
from typing import Dict

class Database(metaclass=Singleton):
    """
    Handle AIS mongo database (Singleton)
    """
    def __init__(self):
        self.client = MongoClient(
            Config.MONGO_URI,
            timeoutMS=30000,
            socketTimeoutMS=30000,
            connectTimeoutMS=30000,
            retryWrites=True,
            retryReads=True,
            serverSelectionTimeoutMS=30000,
            maxPoolSize=50,
            minPoolSize=5,
            waitQueueTimeoutMS=30000
        )
        self.db = self.client[Config.DOCCOMENT]

    def reconnect(self):
        """
        Thử kết nối lại với MongoDB nếu kết nối bị mất
        """
        try:
            self.client.close()
            self.client = MongoClient(
                Config.MONGO_URI,
                timeoutMS=30000,
                socketTimeoutMS=30000,
                connectTimeoutMS=30000,
                retryWrites=True,
                retryReads=True,
                serverSelectionTimeoutMS=30000,
                maxPoolSize=50,
                minPoolSize=5,
                waitQueueTimeoutMS=30000
            )
            self.db = self.client[Config.DOCCOMENT]

            self.client.admin.command('ping')
            logging.info("MongoDB reconnected successfully")
            return True
        except Exception as e:
            logging.error(f"Failed to reconnect to MongoDB: {e}")
            return False

    def closeConnection(self):
        self.client.close()
    def updateHistoryAction(self, record: dict):
        """
        record:
        {
            'camera_id': str (E-19),
            'robot_code': str (1645),
            'object_class': str (Class 0),
            'distance': float (3000 mm),
            'action': "pause"/"resume",
            'created_at': current datetime
        }
        """
        collection_name = CollectionName.HISTORY_ACTION
        try:
            if collection_name not in self.db.list_collection_names():
                self.db.create_collection(collection_name)

            collection = self.db[collection_name]
            if isinstance(record, dict):
                collection.insert_one(record)
            else:
                raise ValueError("Data should be a dictionary")

        except Exception as e:
            logging.error(f"Error inserting data into '{collection_name}': {e}")

    def updateCameraStatus(self, camera_id: str, status: str):
        """
        Args:
            camera_id: ID of the camera
            status: Status of the camera ("connected" / "disconnected")
        """
        collection_name = CollectionName.CAMERA_CONFIG
        try:
            collection = self.db[collection_name]
            result = collection.update_one(
                {"device_id": camera_id},
                {"$set": {"connect_status": status}}
            )
            if result.matched_count == 0:
                logging.warning(f"Camera IP {camera_id} not found in the database")
        except Exception as e:
            logging.error(f"Error updating status for camera IP {camera_id}: {e}")

    def updateEdgeStatus(self, edge_id: str, status: str):
        """
        Args:
            edge_id: IP address of the AI edge device
            status: Status of the AI edge device ("connected" / "disconnected")
        """
        collection_name = CollectionName.AI_EDGE_CONFIG
        try:
            collection = self.db[collection_name]
            result = collection.update_one(
                {"ip": edge_id},
                {"$set": {"connect_status": status}}
            )
            if result.matched_count == 0:
                logging.warning(f"ai_egde id {edge_id} not found in the database")
        except Exception as e:
            logging.error(f"Error updating status for ai_edge id {edge_id}: {e}")

    def insertCameraBlur(self, data: dict):
        """
        NOT_USED
        Args:
            data: { [camera id]: [blur info] }
        """
        collection_name = CollectionName.CAMERA_BLUR
        try:
            if collection_name not in self.db.list_collection_names():
                self.db.create_collection(collection_name)

            collection = self.db[collection_name]
            for camera_id, blur_info in data.items():
                collection.update_one(
                    {"camera_id": camera_id},
                    {"$set": blur_info},
                    upsert=True
                )
                logging.warning(f"Upserted data for camera '{camera_id}' into '{collection_name}'.")
        except Exception as e:
            logging.error(f"Error in insert camera blur: {e}")

    def updateRobotPosition(self, robot_code: str, x: float, y: float):
        """
        Args:
            x: robot x position
            y: robot y position
        """
        collection_name = CollectionName.OBJECT_POSITION
        try:
            if collection_name not in self.db.list_collection_names():
                self.db.create_collection(collection_name)

            collection = self.db[collection_name]
            collection.update_one(
                {"_id": robot_code},
                {"$set": { "data": {
                    "cls": "Forklift",
                    "x_center": x,
                    "y_center": y}
                }},
                upsert=True
            )
        except Exception as e:
            logging.error(f"Error in update robot position: {e}")

    def updateObjectPosition(self, camera_id: str, objects: list):
        """
        Args:
            camera_id: camera id
            objects:
            ```
            [{
                "cls": object class
                "x_center": object x position
                "y_center": object y position
            }]
            ```
        """
        collection_name = CollectionName.OBJECT_POSITION
        try:
            if collection_name not in self.db.list_collection_names():
                self.db.create_collection(collection_name)

            collection = self.db[collection_name]
            collection.update_one(
                {"_id": camera_id},
                {"$set": { "data": objects }},
                upsert=True
            )
        except Exception as e:
            logging.error(f"Error in update object position: {e}")

    def getCameras(self) -> Dict[str, dict]:
        """
        Get dictionary of all cameras config
        ```
        {
            [camera id]: {
                "foot": 4 points for foot,
                "foot_rcs": 4 points for foot on RCS,
                "head": 4 points for head,
                "head_rcs": 4 points for head on RCS
            }
        }
        ```
        """
        data = self.db[CollectionName.CAMERA_CONFIG].find()

        camera_configs = {}
        for camera_config in data:
            camera_id = camera_config['device_id']
            camera_configs[camera_id] = {
                "foot": camera_config["image_coordinates"],
                "foot_rcs": camera_config["actual_coordinates"],
                "head": camera_config["image_coordinates_head"],
                "head_rcs": camera_config["actual_coordinates_head"]
            }
        return camera_configs

    def getCameraByEdge(self, edge_id: str):
        """
        Get list of camera ids providing edge id
        """
        ai_edge_config = self.db[CollectionName.AI_EDGE_CONFIG].find_one({"ip": edge_id})

        if not ai_edge_config:
            logging.error(f"No AI Edge config found with IP {edge_id}")
            return []

        ai_edge_config_id = ai_edge_config.get('_id')
        camera_configs = self.db[CollectionName.CAMERA_CONFIG].find({"ai_edge_config_id": str(ai_edge_config_id)})

        camera_ids = []
        for camera_config in camera_configs:
            camera_ids.append(camera_config.get('device_id'))
        return camera_ids

    def getCameraIPByEdge(self, edge_id: str):
        """
        Get list of camera ids providing edge ip
        """
        ai_edge_config = self.db[CollectionName.AI_EDGE_CONFIG].find_one({"ip": edge_id})

        if not ai_edge_config:
            logging.error(f"No AI Edge config found with IP {edge_id}")
            return []

        ai_edge_config_id = ai_edge_config.get('_id')
        camera_configs = self.db[CollectionName.CAMERA_CONFIG].find({"ai_edge_config_id": str(ai_edge_config_id)})

        camera_ids = []
        for camera_config in camera_configs:
            camera_ids.append(camera_config.get('ip'))
        return camera_ids

    def getListEdgeandCamera(self):
        """
        Get list of edge and camera
        """
        ai_edge_configs = self.db[CollectionName.AI_EDGE_CONFIG].find()
        edge_camera = {}
        for ai_edge_config in ai_edge_configs:
            edge_ip = ai_edge_config.get('ip')
            edge_id = ai_edge_config.get('_id')
            camera_ids = self.getCameraIPByEdge(edge_ip)
            edge_camera[edge_id] = camera_ids
        return edge_camera

    def getSystemConfig(self) -> dict:
        """
        Get system config
        ```
        {
            "distance_human": safe distance to human (body detection)
            "distance_head": safe distance to human (head detection)
            "distance_forklift": safe distance to forklift
        }
        ```
        """
        return self.db[CollectionName.SYSTEM_CONFIG].find_one()

    def updateSatusAiSystem(self, status):
        """

        """
        collection_name = CollectionName.STATUS_AI_SYSTEM
        try:
            if collection_name not in self.db.list_collection_names():
                self.db.create_collection(collection_name)

            collection = self.db[collection_name]
            collection.update_one(
                {"_id": "status_ai"},
                {"$set": { "status": status }},
                upsert=True
            )
        except Exception as e:
            logging.error(f"Error in status AI system: {e}")

    def getStatusAiSystem(self) -> dict:
        """
        """
        return self.db[CollectionName.STATUS_AI_SYSTEM].find_one()

    def saveStatusWcs(self, status: str):
        """
        Save status to WCS
        """
        collection_name = CollectionName.WCS_STATUS
        try:
            if collection_name not in self.db.list_collection_names():
                self.db.create_collection(collection_name)

            collection = self.db[collection_name]
            collection.update_one(
                {"_id": "status_wcs"},
                {"$set": { "status": status }},
                upsert=True
            )
        except Exception as e:
            logging.error(f"Error in save status WCS: {e}")

    def checkConnectionStatus(self):
        """
        Check if any AI edge or camera is disconnected.

        Returns:
            bool: True if all connections are good, False if any disconnection is detected
        """
        try:
            edge_query = {"connect_status": "disconnected"}
            camera_query = {"connect_status": "disconnected"}

            # Count disconnections
            disconnected_edge_count = self.db[CollectionName.AI_EDGE_CONFIG].count_documents(edge_query)
            disconnected_camera_count = self.db[CollectionName.CAMERA_CONFIG].count_documents(camera_query)

            return (disconnected_edge_count == 0 and disconnected_camera_count == 0)

        except Exception as e:
            logging.error(f"Error checking connection status: {e}")
            self.reconnect()
            return False

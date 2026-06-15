from config import MODEL_OBJECT, stop_event, SupervisedCamera, ExclusionZone, ExclusionZoneImage, CheckAreaBox
from database.db import Database
from database.redis_db import Redis_Handler

import cv2, threading, numpy as np, logging
import time
from typing import List, Dict

class SELECTED_POINT:
    TOP = 0
    MIDDLE = 1
    BOTTOM = 2

class TRANSFORM_MAT:
    FOOT = 0
    HEAD = 1

class SELECTED_TF_MAT:
    FOOT = 0
    HEAD = 1.7
    SIT_FL = 2.06
            
class DataTransformer(threading.Thread):
    """
    Get detection data from Redis. Calculate object position in RCS and save to Redis
    """

    def __init__(self):
        super().__init__()

        self.__redis = Redis_Handler()
        self.__db = Database()

        self.__tf_mats: Dict[str, List[np.ndarray]] = {}
        self.__generateMatrix()
    
    def __generateMatrix(self):
        """
        Generate all cameras transform matrix for head and foot
        """
        while True:
            try:
                cameras = self.__db.getCameras()
                for camera_id in cameras:
                    self.__tf_mats[camera_id] = [None, None]
                    self.__tf_mats[camera_id][TRANSFORM_MAT.FOOT] = cv2.getPerspectiveTransform(
                        np.array(cameras[camera_id]["foot"], dtype=np.float32),
                        np.array(cameras[camera_id]["foot_rcs"], dtype=np.float32))
                    self.__tf_mats[camera_id][TRANSFORM_MAT.HEAD] = cv2.getPerspectiveTransform(
                        np.array(cameras[camera_id]["head"], dtype=np.float32),
                        np.array(cameras[camera_id]["head_rcs"], dtype=np.float32))
                break
            except Exception as e:
                logging.error(f"Generate transform matrix error: {e}")
            time.sleep(0.05)

    def run(self):
        """
        Run DataSynchronizer thread.
        Continuously check for new data in Redis and process it.
        """
        while not stop_event.is_set():
            try:
                data = self.__redis.getDetections()
                if data:
                    transformed_data = self.__getRcsPosition(data)
                    for camera_id, values in transformed_data.items():
                        self.__redis.saveObjectData(
                            camera_id, values)
                        self.__db.updateObjectPosition(camera_id, [{
                            "cls": cls,
                            "x_center": x,
                            "y_center": y
                        } for cls, x, y in zip(values["cls"], values["x"], values["y"])])
            except Exception as e:
                logging.error(f"Error in DataSynchronizer thread: {e}")
            time.sleep(0.05)

    def __getRcsPosition(self, data: dict):
        """
        Calculate RCS position by transform matrix
        ```
        data = {
            [camera id]:
            {
                "cls": [ [Detected object class] ],
                "bbox": [ ([x_left, y_top], [x_right, y_bottom]) ]
            }
        }
        ```

        Return:
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
        transformed_data = {}
        for camera_id, values in data.items():
            classes: List[str] = values["cls"]
            bboxes: List[List[list]] = values["bbox"]

            transformed_values = {"cls": [], "x": [], "y": []}


            for i in range(classes.__len__()):
                cls = classes[i]
                if cls is None:
                    continue

                bbox = bboxes[i]
                   
                if cls == MODEL_OBJECT.HUMAN_HEAD:
                    selected_point = SELECTED_POINT.TOP
                    selected_mat = SELECTED_TF_MAT.HEAD
                elif cls == MODEL_OBJECT.HUMAN_BOTTOM:
                    selected_point = SELECTED_POINT.BOTTOM
                    selected_mat = SELECTED_TF_MAT.FOOT
                elif cls == MODEL_OBJECT.FORKLIFT_SEAT:
                    selected_point = SELECTED_POINT.TOP
                    selected_mat = SELECTED_TF_MAT.SIT_FL
                elif cls == MODEL_OBJECT.FORKLIFT_STAND:
                    selected_point = SELECTED_POINT.MIDDLE
                    selected_mat = SELECTED_TF_MAT.FOOT
                else:
                    raise Exception(f"No definition for object {cls}")
                
                x_center, y_center = self.__getCenter(bbox, selected_point)
                
                # bbox_width, bbox_height
                bbox_width = bbox[1][0]-bbox[0][0]
                bbox_height = bbox[1][1]-bbox[0][1]
                
                area = bbox_height * bbox_width
                
                # ExclusionZone Image
                point = (x_center,y_center)
                if cls == MODEL_OBJECT.HUMAN_HEAD and camera_id in ExclusionZoneImage:
                    if camera_id in CheckAreaBox:
                        if cv2.pointPolygonTest(ExclusionZoneImage[camera_id],point,False)>= 0:
                           if area < CheckAreaBox[camera_id]:
                            #    if camera_id == "E-29":
                            #         print(cls, area)
                               continue
                    else:
                       if cv2.pointPolygonTest(ExclusionZoneImage[camera_id],point,False)>= 0:
                           continue 
                        
                
                x, y = self.__applyTransformation(camera_id, x_center, y_center, selected_mat)
                if self.__isValid(camera_id, x, y):
                    transformed_values['cls'].append(cls)
                    transformed_values['x'].append(x)
                    transformed_values['y'].append(y)

            transformed_data[camera_id] = transformed_values

        return transformed_data

    def __getCenter(self, bbox: List[list], selected: SELECTED_POINT):
        """
        Get the center of the top/bottom/middle edge of the bounding box.
        
        Parameters:
            bbox: Bounding box coordinates [ [x left, y top], [x right, y bottom] ]
            selected: Point to get from bounding box
        
        Returns:
            Center x, y coordinates
        """
        x_min, y_min = bbox[0]
        x_max, y_max = bbox[1]
        
        if selected == SELECTED_POINT.TOP:
            return (x_min + x_max) / 2, y_min
        if selected == SELECTED_POINT.BOTTOM:
            return (x_min + x_max) / 2, y_max
        if selected == SELECTED_POINT.MIDDLE: 
            return (x_min + x_max) / 2, y_max - (y_max - y_min) / 5

        raise Exception(f"Wrong selected point: {selected}")

    def __applyTransformation(self, camera_id: str, x_center: float, y_center: float, mat: SELECTED_TF_MAT):
        """
        Apply a transformation to a given image coordinate (x, y) using the specified camera matrix.
        
        Parameters:
            camera_id: camera id
            x_center: image point x to transform
            y_center: image point y to transform
            mat: selected transformation matrix to apply
        
        Returns:
            Transformed point (x, y) - RCS position
        """
        point = np.array([x_center, y_center, 1], dtype=np.float32)
        if mat == SELECTED_TF_MAT.HEAD:
            transformed_point = self.__tf_mats[camera_id][TRANSFORM_MAT.HEAD].dot(point)
            transformed_point /= transformed_point[2]
            return  transformed_point[0], transformed_point[1]
        
        elif mat == SELECTED_TF_MAT.FOOT:
            transformed_point = self.__tf_mats[camera_id][TRANSFORM_MAT.FOOT].dot(point)
            transformed_point /= transformed_point[2]
            return  transformed_point[0], transformed_point[1]
        
        elif mat == SELECTED_TF_MAT.SIT_FL:
            point_foot = self.__tf_mats[camera_id][TRANSFORM_MAT.FOOT].dot(point)
            point_foot /= point_foot[2]
            point_head = self.__tf_mats[camera_id][TRANSFORM_MAT.HEAD].dot(point)
            point_head /= point_head[2]
            point_fl = point_foot[:2] + (point_head[:2] - point_foot[:2]) * SELECTED_TF_MAT.SIT_FL / SELECTED_TF_MAT.HEAD
            return  point_fl[0], point_fl[1]
        
        else:
            raise Exception(f"Wrong selected transform matrix: {mat}")
        
    def __isValid(self, camera_id: str, x: float, y: float):
        """
        Check if object (x, y) in supervised zone and outside of excluded zone
        """
        point = (x, y)
        for polygon_point in ExclusionZone.values():
            if polygon_point.size < 3 :
                raise Exception(f"Invalid exclusion field of cam {camera_id}: {polygon_point}")
            
            if cv2.pointPolygonTest(polygon_point, point, False) >= 0:
                return False
    
        if camera_id in SupervisedCamera:
            polygon_point = SupervisedCamera[camera_id]
            if polygon_point.size < 3 :
                raise Exception(f"Invalid supervised field of cam {camera_id}: {polygon_point}")
            
            if cv2.pointPolygonTest(polygon_point, point, False) < 0:
                return False
        
        return True
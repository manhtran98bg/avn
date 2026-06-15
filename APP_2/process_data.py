from config import MODEL_OBJECT, stop_event, ExclusionZone, SupervisedCamera, BackGround, ExclusionZoneRobot
from database.db import Database
from database.redis_db import Redis_Handler
from utils.threadpool import Worker

import threading, time, logging
import numpy as np, cv2

CONFIG_QUERY_INTERVAL = 10
DRAW_IMAGE = False

TURN_OFF_AI = False
# TIME_SET = 0.5
class DRAW_COLOR:
    GREEN = (0, 255, 0)
    RED = (0, 0, 255)
    BLUE = (255, 0, 0)
    WHITE = (255, 255, 255)
    GRAY = (128, 128, 128)
    PINK = (255, 0, 255)
    PURPLE = (150, 0, 50)
    LEAF = (0, 150, 50)
    ORANGE = (100, 0, 255)

OBJECT_MAPPING = {
    MODEL_OBJECT.HUMAN_HEAD: (DRAW_COLOR.GREEN, 750),
    MODEL_OBJECT.HUMAN_BOTTOM: (DRAW_COLOR.RED, 250),
    MODEL_OBJECT.FORKLIFT_SEAT: (DRAW_COLOR.ORANGE, 2000),
    MODEL_OBJECT.FORKLIFT_STAND: (DRAW_COLOR.PURPLE, 2000)
}

PK_ZONE = {
    "07": [[2759, 5365.4], [3334, 5365.4], [3334, 4665.4], [2759, 4665.4]],
    "08": [[3495, 5361.9], [4068.4, 5361.9], [4068.4, 4661.9], [3495, 4661.9]],
    "09": [[4595, 5317.1], [5123.4, 5317.1], [5123.4, 4717.6], [4710.4, 4717.6], [4710.4, 5197.6], [4595, 5197.6]],
    "10": [[5457, 5359.7], [5868.4, 5359.7], [5868.4, 4799.7], [5457, 4659.7]]
}
LAYOUT_CONTOUR = np.array([
    [21697,43741], [22123,63306], [62167,63472], [62208,57574], [60879,57615],
    [61419,51010], [64410,50844], [64846,43616], [50671,43814], [49248,44717],
    [47742,43803], [40094,44349], [26661,43668], [25103,44561], [23743,43678],
    [21697,43741], [18280,43699], [18966,20791], [64493,20624], [64846,43616]
])

class Draw_Map:
    def __init__(self):
        self.__img: np.ndarray = None
        self.__zone_id = 1
        self.__zone_counter = 0
        self.__zone_delay = 10

    def genBackground(self):
        if not DRAW_IMAGE:
            return

        self.__img = np.zeros((10000, 10000, 3), dtype=np.uint8)
        for i in range(10):
            cv2.line(self.__img, (0, i*1000 + 500), (9999, i*1000 + 500), DRAW_COLOR.WHITE, 50)
            cv2.line(self.__img, (i*1000 + 500, 0), (i*1000 + 500, 9999), DRAW_COLOR.WHITE, 50)
        cv2.polylines(self.__img,[np.array(LAYOUT_CONTOUR/10, np.int32)], False, DRAW_COLOR.LEAF, 20)
        for z in PK_ZONE.values():
            cv2.polylines(self.__img, [np.array(z, np.int32)], True, DRAW_COLOR.BLUE, 20)
        for value in ExclusionZone.values():
            cv2.polylines(self.__img, [np.array(value/10, np.int32)], True, DRAW_COLOR.GRAY, 20)
        for value in BackGround.values():
            cv2.polylines(self.__img, [np.array(value/10, np.int32)], True, DRAW_COLOR.GRAY, 20)
        for value in ExclusionZoneRobot.values():
            cv2.polylines(self.__img, [np.array(value/10, np.int32)], True, DRAW_COLOR.GRAY, 20)
        cv2.polylines(self.__img, [np.array([
            [4644.7, 3988],
            [5158.6, 3996.2],
            [5205.1, 2429.9],
            [2318.6, 2380.7],
            [2304.9, 3083.2],
            [4666.6, 3121.5]
        ], np.int32)], True, DRAW_COLOR.LEAF, 20)
        for key, value in SupervisedCamera.items():
            if int(key.split("-")[1]) == self.__zone_id:
                cv2.polylines(self.__img, [np.array(value/10, np.int32)], True, DRAW_COLOR.ORANGE, 30)
                cv2.putText(self.__img, key, np.array(value[0]/10, np.int32),
                    cv2.FONT_HERSHEY_SIMPLEX, 7, DRAW_COLOR.ORANGE, 20)
                break
        self.__zone_counter += 1
        if self.__zone_counter > self.__zone_delay:
            self.__zone_counter = 0
            self.__zone_id += 1
        if self.__zone_id > 33:
            self.__zone_id = 1
    def __drawObject(self, x: float, y: float, color: tuple, radius: float, name: str = None):
        if not DRAW_IMAGE:
            return
        cv2.circle(self.__img, (int(x/10), int(y/10)), int(radius / 10), color, 20)
        if name:
            cv2.putText(self.__img, name, (int(x/10) + 3000, int(y/10)),
                cv2.FONT_HERSHEY_SIMPLEX, 7, color, 20, bottomLeftOrigin=False)
    def addFmr(self, x: float, y: float):
        for r in [4000, 3000, 2000]:
            self.__drawObject(x, y, DRAW_COLOR.PINK, r)
    def addObstacle(self, x: float, y: float, cls: str, camera_id: str):
        self.__drawObject(x, y, OBJECT_MAPPING[cls][0], OBJECT_MAPPING[cls][1], str(camera_id).split("-")[1])
    def addContour(self, polygon: np.ndarray):
        for x, y in polygon:
            cv2.circle(self.__img, (int(x/10), int(y/10)), 200, DRAW_COLOR.WHITE, 20)
    def show(self):
        if not DRAW_IMAGE:
            return
        self.__img = cv2.resize(self.__img, (1024, 768))
        cv2.imshow("test", self.__img)
        cv2.waitKey(1)

class DistanceCalculator(threading.Thread):
    def __init__(self):
        """
        Initializes DistanceCalculator thread.
        Sets up database, configuration variables.

        - Query distance config every 10s
        """
        super().__init__()

        self.__redis = Redis_Handler()
        self.__db = Database()
        self.__map = Draw_Map()

        self.last_query_time = 0
        self.__config_distance_human = 4000.0
        self.__config_distance_head = 4000.0
        self.__config_distance_forklift = 4000.0
        self.__turn_on_ai = "True"
        # self.__time_save_status = 0
        # Khởi tạo trạng thái kết nối là False để kiểm tra ngay khi khởi động
        self.__previous_connection_status = False
        # Kiểm tra trạng thái kết nối ngay khi khởi động
        self.__initial_check_done = False
        self.__initial_count = 1

        self.__queryConfig()
    @Worker.employ
    def __queryConfig(self):
        """
        Periodically query config in database
        """
        while True:
            if time.time() - self.last_query_time > CONFIG_QUERY_INTERVAL:
                system_config = self.__db.getSystemConfig()

                if system_config:
                    self.__config_distance_human = system_config['distance_human']
                    self.__config_distance_head = system_config['distance_head']
                    self.__config_distance_forklift = system_config['distance_forklift']
                    self.last_query_time = time.time()
            time.sleep(5)

    def run(self):
        """
        Runs DistanceCalculator thread. Calculates distances and create combined status.
        """
        while not stop_event.is_set():
            try:
                self.__loop()
            except Exception as e:
                logging.error(f"Error in DistanceCalculator: {e}")
            time.sleep(0.05)

    def __loop(self):
        """
        - Calculates distances between robots and objects.
        - Determines if robots are above or below the threshold.
        - Updates Redis with combined status.
        """
        global TURN_OFF_AI
        data = self.__redis.getRobotData()
        if data is None:
            time.sleep(0.2)
            return

        object_data = self.__redis.getObjectData()
        combined_status = {
            "pause": {},
            "resume": {}
        }
        self.__turn_on_ai  = self.__redis.getSatusAISystem()
        self.__turn_on_ai  = self.__turn_on_ai.get("status")
        if self.__turn_on_ai == "False":
            for robot_code in data:
                self.__saveDistanceData(robot_code, "All", "", 0, combined_status["resume"])
            if not TURN_OFF_AI:
                self.__redis.saveCombinedStatus(combined_status)
                TURN_OFF_AI = True
            return
        # Kiểm tra trạng thái kết nối của các edge và camera
        all_is_connected = self.__checkConnectionStatus()
        # Nếu chưa hoàn thành kiểm tra ban đầu hoặc có sự thay đổi trạng thái kết nối
        if (not all_is_connected and self.__previous_connection_status) or not self.__initial_check_done:
            # Nếu là lần đầu tiên hoặc trạng thái kết nối thay đổi từ tốt sang xấu
            if not self.__initial_check_done or self.__previous_connection_status:
                logging.warning(f"Disconnection detected in AI edges or cameras. Stopping all robots. (Count: {self.__initial_count + 1}/3)")
                self.__previous_connection_status = False
            for robot_code in data:
                self.__saveDistanceData(robot_code, "Disconnection", "System Error", 0, combined_status["pause"])
            self.__redis.saveCombinedStatus(combined_status)
            
            self.__initial_count += 1
            
            # Chỉ đánh dấu đã hoàn thành kiểm tra ban đầu sau khi đã gửi 3 lần
            if self.__initial_count >= 3:
                self.__initial_check_done = True
            
            return
        self.__previous_connection_status = True
        TURN_OFF_AI = False

        self.__map.genBackground()
        if not object_data:
            for robot_code in data:
                self.__saveDistanceData(robot_code, "All", "", 0, combined_status["resume"])
        else:
            self.__drawObject(object_data)
            for robot_code, robot_data in data.items():
                # Kiểm tra xem robot có nằm trong exclusion zone không
                robot_x = float(robot_data['posX'])
                robot_y = float(robot_data['posY'])
                robot_position = (robot_x, robot_y)
                in_exclusion_zone = False
                for polygon_point in ExclusionZoneRobot.values():
                    if cv2.pointPolygonTest(polygon_point, robot_position, False) >= 0:
                        in_exclusion_zone = True
                        break
                if in_exclusion_zone:
                    self.__saveDistanceData(robot_code, "All", "", 0, combined_status["resume"])
                else:
                    self.__processData(object_data, robot_code, robot_data, combined_status["resume"], combined_status["pause"])
        self.__map.show()
        self.__redis.saveCombinedStatus(combined_status)

    def __checkConnectionStatus(self):
        """
        Check if any AI edge or camera is disconnected.
        Returns True if all is connected, False if any disconnected.
        """
        try:
            all_is_connected = self.__db.checkConnectionStatus()
            if not all_is_connected:
                return False
            return True
        except Exception as e:
            logging.error(f"Error checking connection status: {e}")
            return False
    def __drawObject(self, object_data: dict):
        """
        Draw all object to map
        """
        if not DRAW_IMAGE:
            return
        for camera_id, objects in object_data.items():
            if not objects:
                continue
            # if camera_id not in ["E-05"]:
            #     continue
            for param in zip(objects["x"], objects["y"], objects["cls"]):
                self.__map.addObstacle(*param, camera_id)

    def __processData(
            self, object_data: dict, robot_code: str, robot_data: dict,
            above_threshold: dict, below_threshold: dict):
        """
        Processes data for a single robot. Determines if the robot is above or below the threshold.
        ```
        object_data = {
            [camera id]:
            {
                "cls": [ [Detected object class] ],
                "x": [ [object x position] ],
                "y": [ [object y position] ]
            }
        }
        robot_data = {
            [robot code]:
            {
                "posX": robot x position,
                "posY": robot y position,
                "status": robot status (config.FMR_STATUS)
            }
        }
        ```
        """
        status = int(robot_data["status"])
        robot_x = float(robot_data['posX'])
        robot_y = float(robot_data['posY'])
        self.__map.addFmr(robot_x, robot_y)
        robot_position = (robot_x, robot_y)
        # for polygon_point in ExclusionZoneRobot.values():
        #     if cv2.pointPolygonTest(polygon_point, robot_position, False) >= 0:
        #         continue
        if status not in [1, 2, 4, 5, 8]:
            self.__saveDistanceData(robot_code, " All ", "", 0, above_threshold)
            return
        robot_path: np.ndarray = np.array([eval(points)[:2] for points in robot_data["path"]])
        for i in range(robot_path.shape[0]):
            path_x, path_y = robot_path[i]
            dist = np.linalg.norm(np.array([robot_x, robot_y]) - np.array([path_x, path_y]))
            if dist > 2000:
                robot_path = robot_path[:i]
                break
        self.__map.addContour(robot_path)

        for camera_id, objects in object_data.items():
            if not objects:
                continue

            cls_list = objects['cls']
            x_list = objects['x']
            y_list = objects['y']

            for i in range(len(cls_list)):
                cls = cls_list[i]
                obj_x = x_list[i]
                obj_y = y_list[i]
                absolute_dist = np.linalg.norm(np.array([robot_x, robot_y]) - np.array([obj_x, obj_y]))
                # if robot_code =="1645":
                #     if camera_id == "E-05":
                #         if cls == MODEL_OBJECT.HUMAN_HEAD:
                #             print(f"camera ID, {camera_id} ,{robot_code} distane head: {absolute_dist}")
                #         if cls == MODEL_OBJECT.HUMAN_BOTTOM:
                #             print(f"camera ID, {camera_id},{robot_code} distane foot: {absolute_dist}")
                safe_dist = absolute_dist - OBJECT_MAPPING[cls][1]
                absolute_min_dist = absolute_dist
                for path_x, path_y in robot_path:
                    absolute_min_dist = min(
                        absolute_min_dist,
                        np.linalg.norm(np.array([path_x, path_y]) - np.array([obj_x, obj_y]))
                    )
                safe_min_dist = absolute_min_dist - OBJECT_MAPPING[cls][1]
                # if not (safe_dist < self.__config_distance_human
                #     and cls == MODEL_OBJECT.HUMAN_BOTTOM
                # or safe_dist < self.__config_distance_head
                #     and cls == MODEL_OBJECT.HUMAN_HEAD
                # or safe_dist < self.__config_distance_forklift
                #     and cls == MODEL_OBJECT.FORKLIFT_SEAT
                # or 1500 < safe_dist < self.__config_distance_forklift
                #     and cls == MODEL_OBJECT.FORKLIFT_STAND
                # ):
                #     continue
                if robot_path.size == 0:
                    if not (safe_dist < self.__config_distance_human
                        and cls == MODEL_OBJECT.HUMAN_BOTTOM
                    or safe_dist < self.__config_distance_head
                        and cls == MODEL_OBJECT.HUMAN_HEAD
                    or 1000 <safe_dist < self.__config_distance_forklift
                        and cls == MODEL_OBJECT.FORKLIFT_SEAT
                    or 1500 < safe_dist < self.__config_distance_forklift
                        and cls == MODEL_OBJECT.FORKLIFT_STAND
                    ):
                        continue
                else:
                    if not ( (safe_min_dist < 2000
                            and cls != MODEL_OBJECT.FORKLIFT_STAND and cls != MODEL_OBJECT.FORKLIFT_SEAT)
                        or (1500 < safe_dist < 4000
                            and cls == MODEL_OBJECT.FORKLIFT_STAND)
                        or (1500 < safe_dist <4000
                            and cls == MODEL_OBJECT.FORKLIFT_SEAT) ):
                        continue

                self.__saveDistanceData(robot_code, camera_id, cls, safe_dist, below_threshold)
                return
        self.__saveDistanceData(robot_code, " All ", "", 0, above_threshold)

    def __saveDistanceData(self, robot_code: str, camera_id: str, obj_cls: str, distance: float, threshold_dict: dict):
        """
        Records distance data for a robot to threshold_dict.
        """
        # if obj_cls == "":
        # self.__time_save_status = time.time()
        if robot_code not in threshold_dict:
            threshold_dict[robot_code] = []
        threshold_dict[robot_code].append({
            'camera_id': camera_id,
            'object_class': obj_cls,
            'distance': distance,
        })
        # else:
        #     time_start_detect =  self.__time_save_status
        #     if time.time() - time_start_detect >= TIME_SET:
        #         self.__time_save_status = time.time()

        #         if robot_code not in threshold_dict:
        #             threshold_dict[robot_code] = []
        #         threshold_dict[robot_code].append({
        #             'camera_id': camera_id,
        #             'object_class': obj_cls,
        #             'distance': distance,
        #         })
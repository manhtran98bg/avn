from edge_com import Edge_Handler
from database.redis_db import Redis_Handler
from database.db import Database
from config import Config, CF_AIS

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import logging, cv2, numpy as np, io
from PIL import Image
from waitress import serve
import redis, json
from threading import Thread

app = Flask(__name__)
CORS(app)

TURN_OFF_AI = {"status":"False"}
TURN_ON_AI = {"status":"True"}


redis_db = Redis_Handler()
db = Database()

@app.route('/get_status_ai_system', methods=['GET'])
def get_status_ai_system():
    try:
        status = db.getStatusAiSystem()
        
        if status:
            return jsonify(status)
        return jsonify({"error": "Err get status aisystem"}), 404
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/control_ais', methods=['POST'])
def control_ais():
    global TURN_ON_AI  
    global TURN_OFF_AI

    try:
        data = request.json
        action = data.get("action")

        if action is None:
            return jsonify({"status": "error", "message": "Missing required field: action"}), 400
        
        if action == "start":
            redis_db.saveSatusAISystem(TURN_ON_AI)
            db.updateSatusAiSystem(TURN_ON_AI.get("status"))
            logging.info("AI system turned ON.")
            
        elif action == "stop":
            redis_db.saveSatusAISystem(TURN_OFF_AI)
            db.updateSatusAiSystem(TURN_OFF_AI.get("status"))
            logging.info("AI system turned OFF.")
            
        else:
            return jsonify({"status": "error", "message": "Invalid action. Use 'start' or 'stop'."}), 400

        return jsonify({"status": "success", "current_state": TURN_ON_AI}), 200

    except KeyError as key_error:
        logging.error(f"KeyError: {key_error}")
        return jsonify({"status": "error", "message": f"Missing field: {key_error}"}), 400
    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

    
@app.route('/get_blur_info', methods=['GET'])
def get_blur_info():
    try:
        message = {"action": "check_blur_detection"}
        Edge_Handler.publish(topic="control_topic", message=message)

        data = Redis_Handler().getBlurStatus()
        if data:
            return jsonify(data)
        return jsonify({"error": "No blur data found in Redis"}), 404

    except redis.RedisError as redis_error:
        logging.error(f"Redis error: {redis_error}")
        return jsonify({"error": "Redis communication failed"}), 500
    except RuntimeError as mqtt_error:
        return jsonify({"error": str(mqtt_error)}), 500
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/camera_view", methods=["POST"])
def update_camera_status():
    try:
        data = request.json
        camera_ip = data.get("camera_ip")
        enable = data.get("enable")
        
        if not camera_ip:
            return jsonify({"status": "error", "message": "Missing required field: camera_ip"}), 400
        if enable is None:
            return jsonify({"status": "error", "message": "Missing required field: enable"}), 400

        message = {"camera_ip": camera_ip, "websocket_enable": enable}
        Edge_Handler.publish(topic="control_topic", message=message)

        return jsonify({"status": "success", "camera_id": camera_ip, "enable": enable}), 200

    except KeyError as key_error:
        logging.error(f"KeyError: {key_error}")
        return jsonify({"status": "error", "message": f"Missing field: {key_error}"}), 400
    except RuntimeError as mqtt_error:
        return jsonify({"status": "error", "message": str(mqtt_error)}), 500
    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/update_config_camera", methods=["POST"])
def update_config_camera():
    try:
        data = request.json
        camera_ip = data.get("camera_ip")
        ai_edge_old = data.get("ai_edge_config_id")
        edge_camera = db.getListEdgeandCamera()
        edge_camera = {str(key): value for key, value in edge_camera.items()}
        # edge_camera = {str(key): value for key, value in edge_camera.items()}


        if camera_ip is None:
            return jsonify({"status": "error", "message": "Missing required field: camera_ip"}), 400

        for edge_new in edge_camera:
            if camera_ip in edge_camera.get(edge_new):
                if ai_edge_old == edge_new:
                    message = {"camera_ip": camera_ip, "action": "reload_config"}
                    Edge_Handler.publish(topic="control_topic", message=message)

                    return jsonify({"status": "success"}), 200
                else: 
                    # edge_camera[edge_new].remove(camera_ip)
                    # edge_camera[ai_edge_old].append(camera_ip)
                    # print("append",edge_camera.get(ai_edge_old))
                    # print("remove",edge_camera.get(edge_new))

                    message = {"camera_ip": camera_ip, "action": "stop"}
                    Edge_Handler.publish(topic="control_topic", message=message)
                    logging.info(f"Delete camera_ip {camera_ip} in ai edge {ai_edge_old}")

                    message = {"camera_ip": camera_ip, "action": "start"}
                    Edge_Handler.publish(topic="control_topic", message=message)
                    logging.info(f"create camera_ip {camera_ip} in ai edge {edge_new}")
                    
                    return jsonify({"status": "success"}), 200

                    
       
        # message = {"camera_ip": camera_ip, "action": "reload_config"}
        # Edge_Handler.publish(topic="control_topic", message=message)

        # return jsonify({"status": "success"}), 200

    except KeyError as key_error:
        logging.error(f"KeyError: {key_error}")
        return jsonify({"status": "error", "message": f"Missing field: {key_error}"}), 400
    except RuntimeError as mqtt_error:
        return jsonify({"status": "error", "message": str(mqtt_error)}), 500
    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/get_camera_frame", methods=["POST"])
def get_camera_frame():
    try:
        data = request.json
        camera_ip = data.get("ip")
        username = data.get("username")
        password = data.get("password")
        k_matrix = data.get("k_matrix")
        d_matrix = data.get("d_matrix")

        if not all([camera_ip, username, password, k_matrix, d_matrix]):
            return jsonify({
                "status": "error",
                "message": "camera_ip, username, password, k_matrix, and d_matrix are required"
            }), 400

        K = np.array(k_matrix, dtype=np.float32)
        D = np.array(d_matrix, dtype=np.float32)

        if K.shape != (3, 3):
            return jsonify({"status": "error", "message": "k_matrix must be a 3x3 matrix"}), 400

        if D.ndim != 1 or (D.size != 4 and D.size != 5):
            return jsonify({"status": "error", "message": "d_matrix must be a 1D array with 4 or 5 elements"}), 400

        rtsp_url = f"rtsp://{username}:{password}@{camera_ip}"

        cap = cv2.VideoCapture(rtsp_url)
        if not cap.isOpened():
            return jsonify({"status": "error", "message": "Cannot open camera"}), 400

        ret, frame = cap.read()
        if not ret:
            return jsonify({"status": "error", "message": "Failed to capture frame"}), 400

        frame = cv2.resize(frame, (1024, 768))
        h, w = frame.shape[:2]

        # Generate the undistortion and rectification transformation map
        new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(K, D, (w, h), 1, (w, h))
        map1, map2 = cv2.initUndistortRectifyMap(K, D, None, new_camera_matrix, (w, h), 5)
        
        # Apply the correction
        undistorted_frame = cv2.remap(frame, map1, map2, cv2.INTER_LINEAR)
        
        # Crop the image based on the ROI (Region of Interest)
        x, y, w, h = roi
        undistorted_img = undistorted_frame[y:y+h, x:x+w] 

        # Thay đổi kích thước frame
        frame_resized = cv2.resize(undistorted_img, (512, 384))

        image = Image.fromarray(cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB))
        byte_io = io.BytesIO()
        image.save(byte_io, "JPEG")
        byte_io.seek(0)

        return send_file(byte_io, mimetype="image/jpeg")

    except cv2.error as cv2_error:
        logging.error(f"OpenCV error: {cv2_error}")
        return jsonify({"status": "error", "message": "Failed to process camera frame"}), 500
    except RuntimeError as mqtt_error:
        return jsonify({"status": "error", "message": str(mqtt_error)}), 500
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/create_camera", methods=["POST"])
def create_camera():
    try:
        data = request.json
        camera_ip = data.get("camera_ip")

        if camera_ip is None:
            return jsonify({"status": "error", "message": "Missing required field: camera_ip"}), 400

        message = {"camera_ip": camera_ip, "action": "start"}
        Edge_Handler.publish(topic="control_topic", message=message)

        return jsonify({"status": "success"}), 200

    except KeyError as key_error:
        logging.error(f"KeyError: {key_error}")
        return jsonify({"status": "error", "message": f"Missing field: {key_error}"}), 400
    except RuntimeError as mqtt_error:
        return jsonify({"status": "error", "message": str(mqtt_error)}), 500
    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/delete_camera", methods=["POST"])
def delete_camera():
    try:
        data = request.json
        camera_ip = data.get("camera_ip")

        if camera_ip is None:
            return jsonify({"status": "error", "message": "Missing required field: camera_ip"}), 400

        message = {"camera_ip": camera_ip, "action": "stop"}
        Edge_Handler.publish(topic="control_topic", message=message)

        return jsonify({"status": "success"}), 200

    except KeyError as key_error:
        logging.error(f"KeyError: {key_error}")
        return jsonify({"status": "error", "message": f"Missing field: {key_error}"}), 400
    except RuntimeError as mqtt_error:
        return jsonify({"status": "error", "message": str(mqtt_error)}), 500
    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

class FlaskAppThread(Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.__redis = Redis_Handler

    def run(self):
        serve(app, host=Config.FLASK_HOST, port=Config.FLASK_PORT)
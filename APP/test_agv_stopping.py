# ================== TEST NGẮT CAMERA (PASTE VÀO test_connection.py) ==================
from datetime import datetime
import time
from database.db import Database
from config import CollectionName

# Chọn camera bất kỳ
TEST_CAMERA_ID = "E-05"  # đổi thành camera bạn muốn

# Giữ trạng thái disconnected trong bao lâu (giây)
HOLD_SECONDS = 150
# Ghi đè lại sau mỗi bao lâu (giây)
REWRITE_INTERVAL = 0.01

def _update_camera_status(collection, camera_id: str, status: str) -> int:
    """Update theo device_id (chuẩn), fallback theo camera_id/_id."""
    result = collection.update_one(
        {"device_id": camera_id},
        {"$set": {"connect_status": status, "updated_at": datetime.now()}}
    )
    if result.matched_count == 0:
        result = collection.update_one(
            {"$or": [{"camera_id": camera_id}, {"_id": camera_id}]},
            {"$set": {"connect_status": status, "updated_at": datetime.now()}}
        )
    return result.matched_count

def test_disconnect_camera_hold():
    print("\n" + "="*70)
    print("🔧 TEST NGẮT CAMERA (DB SIMULATION - HOLD)")
    print("="*70)

    db = Database()
    camera_col = db.db[CollectionName.CAMERA_CONFIG]

    print(f"[{datetime.now()}] HOLD disconnect for {HOLD_SECONDS}s")
    end_time = time.time() + HOLD_SECONDS

    while time.time() < end_time:
        _update_camera_status(camera_col, TEST_CAMERA_ID, "disconnected")
        time.sleep(REWRITE_INTERVAL)

    # Check lại DB
    doc = camera_col.find_one(
        {"$or": [{"device_id": TEST_CAMERA_ID}, {"camera_id": TEST_CAMERA_ID}, {"_id": TEST_CAMERA_ID}]}
    )
    print(f"[{datetime.now()}] DB after hold: {doc}")

    # Restore lại connected
    print(f"[{datetime.now()}] Restore camera {TEST_CAMERA_ID} => connected")
    _update_camera_status(camera_col, TEST_CAMERA_ID, "connected")

    doc2 = camera_col.find_one(
        {"$or": [{"device_id": TEST_CAMERA_ID}, {"camera_id": TEST_CAMERA_ID}, {"_id": TEST_CAMERA_ID}]}
    )
    print(f"[{datetime.now()}] DB after restore: {doc2}")

# Gọi test
test_disconnect_camera_hold()
# ======================================================================

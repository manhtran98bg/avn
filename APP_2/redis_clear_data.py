from database.redis_db import Redis_Handler
from config import KeyRedis
import logging

def clear_redis_data():
    """
    Clear all relevant Redis keys at the start of the program.
    """
    redis = Redis_Handler()
    try:
        redis.delete(
            KeyRedis.MERGED_DATA_AI_EDGE,
            KeyRedis.OBJECT_POSITION_DATA,
            KeyRedis.BLUR_STATUS,
            KeyRedis.ROBOT_POSITION_DATA,
            KeyRedis.REDIS_KEY_COMBINED_STATUS
        )
        
        logging.info("Cleared all relevant Redis keys at startup")
    except Exception as e:
        logging.error(f"Error clearing Redis data: {e}")
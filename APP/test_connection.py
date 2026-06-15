import os
from dotenv import load_dotenv
import sys
import time

load_dotenv()

print("=" * 70)
print("🔍 TEST KẾT NỐI CỎN BẢN HỆ THỐNG")
print("=" * 70)

# ============================================================================
# 1. TEST MONGODB
# ============================================================================
print("\n📊 1. TEST MONGODB CONNECTION")
print("-" * 70)
try:
    from pymongo import MongoClient
    from config import Config
    
    print(f"  Connecting to: mongodb://{Config.ADDRESS_SERVER}:{Config.PORT_DB}")
    print(f"  Database: {Config.DOCCOMENT}")
    print(f"  User: {Config.USER_NAME_DB}")
    
    client = MongoClient(
        Config.MONGO_URI,
        timeoutMS=5000,
        socketTimeoutMS=5000,
        connectTimeoutMS=5000,
    )
    
    # Ping để test kết nối
    result = client.admin.command('ping')
    print(f"  ✅ MONGODB: Connected successfully!")
    
    # Check collections
    db = client[Config.DOCCOMENT]
    collections = db.list_collection_names()
    print(f"  📦 Collections: {collections[:5]}..." if len(collections) > 5 else f"  📦 Collections: {collections}")
    
    # Test query AI_EDGE_CONFIG
    ai_edge_collection = db['ai_edge_config']
    edge_count = ai_edge_collection.count_documents({})
    print(f"  🖥️  AI_EDGE_CONFIG count: {edge_count}")
    
    # Check connection status
    disconnected = ai_edge_collection.count_documents({"connect_status": "disconnected"})
    connected = ai_edge_collection.count_documents({"connect_status": "connected"})
    print(f"     - Connected edges: {connected}")
    print(f"     - Disconnected edges: {disconnected}")
    
    # List all edges
    edges = ai_edge_collection.find()
    print(f"  📋 Edge details:")
    for edge in edges:
        status = edge.get('connect_status', 'N/A')
        print(f"     - {edge.get('ip', 'N/A')} : {status}")
    
    client.close()
    
except Exception as e:
    print(f"  ❌ MONGODB ERROR: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# 2. TEST REDIS
# ============================================================================
print("\n💾 2. TEST REDIS CONNECTION")
print("-" * 70)
try:
    import redis
    from config import Config
    
    print(f"  Connecting to: {Config.REDIS_HOST}:{Config.REDIS_PORT}")
    
    redis_conn = redis.StrictRedis(
        host=Config.REDIS_HOST,
        port=Config.REDIS_PORT,
        db=Config.REDIS_DB,
        socket_timeout=5
    )
    
    # Ping
    redis_conn.ping()
    print(f"  ✅ REDIS: Connected successfully!")
    
    # Check keys
    keys = redis_conn.keys('*')
    print(f"  🔑 Keys in Redis: {len(keys)}")
    for key in keys[:10]:
        print(f"     - {key}")
    
    redis_conn.close()
    
except Exception as e:
    print(f"  ❌ REDIS ERROR: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# 3. TEST MQTT
# ============================================================================
print("\n📡 3. TEST MQTT CONNECTION")
print("-" * 70)
try:
    import paho.mqtt.client as mqtt_client
    from config import Config
    
    print(f"  Connecting to: {Config.MQTT_BROKER}:{Config.MQTT_PORT}")
    
    mqtt_connected = False
    
    def on_connect(client, userdata, flags, rc):
        global mqtt_connected
        if rc == 0:
            mqtt_connected = True
            print(f"  ✅ MQTT: Connected successfully!")
        else:
            print(f"  ❌ MQTT: Connection failed with code {rc}")
    
    def on_disconnect(client, userdata, rc):
        if rc != 0:
            print(f"  ⚠️  MQTT: Unexpected disconnection. Code: {rc}")
    
    client = mqtt_client.Client()
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    
    try:
        client.connect(Config.MQTT_BROKER, Config.MQTT_PORT, keepalive=5)
        client.loop_start()
        
        # Wait for connection
        timeout = 5
        while not mqtt_connected and timeout > 0:
            time.sleep(0.1)
            timeout -= 0.1
        
        if mqtt_connected:
            print(f"  📡 MQTT Broker: {Config.MQTT_BROKER}:{Config.MQTT_PORT} - OK")
        else:
            print(f"  ❌ MQTT: Connection timeout")
        
        client.loop_stop()
        client.disconnect()
        
    except Exception as e:
        print(f"  ❌ MQTT ERROR: {e}")
    
except Exception as e:
    print(f"  ❌ MQTT ERROR: {e}")
    import traceback
    traceback.print_exc()

# ============================================================================
# 4. TEST DATABASE CONNECTION STATUS
# ============================================================================
print("\n🔐 4. TEST DATABASE CONNECTION STATUS")
print("-" * 70)
try:
    from database.db import Database
    
    db = Database()
    all_connected = db.checkConnectionStatus()
    
    print(f"  Database.checkConnectionStatus(): {all_connected}")
    
    if not all_connected:
        print(f"  ⚠️  Some connections are down!")
    else:
        print(f"  ✅ All connections are UP!")
    
except Exception as e:
    print(f"  ❌ DATABASE ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("✅ Test hoàn thành!")
print("=" * 70)


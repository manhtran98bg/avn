import os, threading
from dotenv import load_dotenv
import numpy as np

stop_event = threading.Event()

load_dotenv()

class CF_AIS:
    AIS = {
        "66e7d28f006bc005750a2509": ["172.21.99.201","172.21.99.202","172.21.99.203","172.21.99.204","172.21.99.205","172.21.99.206"],
        "66f00712ed60cba5b68befee": ["172.21.99.207","172.21.99.208","172.21.99.209","172.21.99.210","172.21.99.211","172.21.99.212"],
        "66f0071ded60cba5b68beffa": ["172.21.99.113","172.21.99.214","172.21.99.115","172.21.99.216","172.21.99.117","172.21.99.218","172.21.99.132"],
        "66e829ed006bc005750a6e13": ["172.21.99.131","172.21.99.130","172.21.99.129","172.21.99.128","172.21.99.127","172.21.99.124"],
        "66e26388fc887a7ca1bb2fa6": ["172.21.99.119","172.21.99.120","172.21.99.121","172.21.99.122","172.21.99.123","172.21.99.125","172.21.99.126"]
    }

class WCSTopic:
    AGV_STATUS_TOPIC = "agv_states"
    WCS_STATUS_TOPIC = "wcs_status"
    WCS_HEARTBEAT_TOPIC = "wcs_heartbeat"

class MODEL_OBJECT:
    HUMAN_HEAD = "Class 0"
    HUMAN_BOTTOM = "Class 1"
    FORKLIFT_SEAT = "Class 2"
    FORKLIFT_STAND = "Class 3"

class FMR_STATUS:
    EXECUTING = 2
    STOPPED = 5
    ON_CURVE = 8
    ABNORMAL = 3
    TASK_COMPLETE = 1
    
ExclusionZoneImage = {
    "E-32": np.array([[186, 79], [187, 127], [478, 132], [484, 65]]),
    "E-29": np.array([[2, 325], [399, 148], [398, 82], [0, 106]]),
    "E-28": np.array([[3, 159], [349, 101], [355, 30], [1, 11]]),
    "E-22": np.array([[287, 139], [288, 28], [132, 32], [137, 84]]),
    "E-20": np.array([[510, 210], [511, 72], [76, 95], [81, 172]]),
    "E-27": np.array([[267, 14], [268, 69], [497, 107], [507, 32]]),
    "E-21": np.array([[212, 115], [195, 250], [278, 328], [508, 379],[510,82]]),
    "E-31": np.array([[13, 137], [263, 82], [263, 44], [5, 55]]),
    "E-23": np.array([[175, 15], [281, 13], [274, 60], [178, 59]])
}

CheckAreaBox = {
    "E-28": 190,
    "E-29": 190,
    "E-20": 210,
    "E-22": 110,
    "E-32": 110,
    "E-27": 65,
    "E-31": 70,
    "E-21": 180,
    "E-23": 100
    
}
BackGround = {
    "BG1": np.array([[57789,58245],[58669,58286],[58605,57453],[57749,57437]]),
    "BG2": np.array([[51766,58274],[52582,58274],[52570,57425],[51786,57425]]),
    "BG3": np.array([[27706,58237],[28642,58210],[28546,57377],[27778,57409]]),
    "BG4": np.array([[33785,58233],[34598,58261],[34586,57429],[33781,57441]]),
    "BG5": np.array([[39808,58257],[40629,58281],[40617,57433],[39808,57445]]),
    "BG6": np.array([[45795,58233],[46612,58233],[46596,57449],[45795,57427]])
}

ExclusionZoneRobot = {
    "Zone1": np.array([[40400,59600],[40400,57650],[44646,57650],[44646,59600]]),
    "Zone2": np.array([[47055,58572],[47055,57322],[57224,57322],[57224,58572]]),
    "Zone3": np.array([[29234,58511],[29234,57261],[38953,57261],[38953,58511]]),
    "Zone4": np.array([[44077,48000],[44477,48000],[44477,47450],[44077,47450]]),
    # Tram sac 
    "Zone5": np.array([[61632,49222],[61632,48691],[62111,48691],[62111,49222]]),
    "Zone6": np.array([[60201,45306],[60201,45000],[60605,45000],[60612,45308]]),
    "Zone7": np.array([[62621,45652],[62616,45106],[63299,45108],[63298,45659]])
    
}

SupervisedCamera = {
    "E-33": np.array([[20665,42669],[34662,42934],[34514,31000],[20193,31000]]),
    "E-32": np.array([[58081,61000],[61734,61000],[61696,43900],[52022,44004],[51845,53841],[57846,53815]]),
    "E-31": np.array([[40901,43335],[22220,43095],[22116,55583],[40797,55652]]),
    "E-30": np.array([[22186,61523],[22105,52092],[42000,52414],[42000,62088]]),
    "E-29": np.array([[28171,50388],[27793,63392],[39800,63358],[39800,50250]]),
    "E-28": np.array([[34020,63358],[34158,49734],[40500,49734],[40500,56496],[40500,56496],[40500,63358]]),
    "E-27": np.array([[40849,43095],[23200,43404],[23200,52624],[34209,52418],[34072,57303],[40711,57303]]),
    "E-26": np.array([[40901,61000],[40901,43335],[30098,43163],[29960,61000]]),
    "E-25": np.array([[40218,61000],[51706,61000],[51706,48212],[39886,48461]]),
    "E-24": np.array([[39886,43748],[55092,43507],[55023,50938],[52202,50938],[51858,65000],[39955,65000]]),
    "E-23": np.array([[44133,40380],[53887,40380],[54129,60617],[44456,60697]]),
    "E-22": np.array([[46350,50419],[46552,62592],[29562,63196],[29240,51104]]),
    "E-21": np.array([[60357,58500],[43428,58500],[43347,50175],[60679,50560]]),
    "E-20": np.array([[58422,50479],[46169,50963],[46088,62894],[59470,62894]]),
    "E-19": np.array([[65039,43353],[46027,43215],[46233,52091],[65038,51678]]),
    "E-18": np.array([[38628,32000],[38346,44600],[64960,44247],[64960,32000]]),
    "E-17": np.array([[40252,28900],[40111,44883],[64960,44247],[64960,28900]]),
    "E-16": np.array([[51622,20387],[51622,36000],[64960,36000],[64960,20733]]),
    "E-15": np.array([[34000,20104],[34000,34000],[64960,34000],[64960,20175]]),
    "E-14": np.array([[40252,20387],[40111,44883],[58959,44247],[58959,20733]]),
    "E-13": np.array([[40252,20387],[40111,44883],[58959,44247],[58959,20733]]),
    "E-12": np.array([[41300,44099],[41300,34545],[64960,34815],[64960,44120]]),
    "E-11": np.array([[40153,35084],[40153,20977],[64015,20856],[64176,35367]]),
    "E-10": np.array([[40112,27547],[64377,27144],[64297,43509],[40112,43589]]),
    "E-09": np.array([[40153,28434],[40233,20614],[64136,20775],[64257,28756]]),
    # "E-08": np.array([[8953,36092],[40737,36387],[40932,14516],[8388,14516]]),

    "E-08": np.array([[40495,36092],[40737,18807],[17097,19681],[17097,36092]]),
    "E-07": np.array([[40334,27184],[40012,42089],[19374,41937],[19374,27587]]),
    "E-06": np.array([[40737,35165],[19254,35125],[19334,20856],[40616,21098]]),
    "E-05": np.array([[40314,34631],[40636,43337],[19677,43015],[19193,34470]]),
    "E-04": np.array([[19435,43740],[18862,24662],[43005,24662],[44558,43499]]),
    "E-03": np.array([[39000,43965],[39000,31890],[19838,30482],[19435,43015]]),
    "E-02": np.array([[18792,35917],[18792,20528],[37000,20599],[37000,35988]]),
    "E-01": np.array([[19999,43337],[34590,43337],[34429,20927],[19274,21088]])
}

# ExclusionZone ={
#     "ExclusionZone_1": np.array([[61324,62575],[55642,62611],[55677,59469],[61254,59328]]),
#     "ExclusionZone_2": np.array([[52677,62928],[52624,59346],[47153,59363],[47100,62496]]),
#     "ExclusionZone_3": np.array([[46200,59222],[46058,61587],[40182,61534],[40164,59099]]),
#     "ExclusionZone_4": np.array([[28145,62469],[28234,58975],[39793,59010],[39758,62964]]),   
# }

ExclusionZone ={
    "ExclusionZone_1": np.array([[61324,57980],[44887,57980],[44871,58960],[40196,58993],[40196,57980],[27742,57980],[27742,63500],[61254,63500]]),
    "ExclusionZone_2": np.array([[17746,24969],[25097,24969],[25097,19941],[17922,19765]])
    # "ExclusionZone_2": np.array([[52677,63500],[52624,58300],[49500,58300],[49500,58300],[46600,58300],[46600,63500]]),
    # "ExclusionZone_3": np.array([[47200,59000],[47200,63500],[39800,63500],[39800,59000]]),
    # "ExclusionZone_4": np.array([[28145,63500],[28234,58700],[34100,58700],[34100,58700],[39793,58700],[39758,63500]]),   
}

class CollectionName:
    # Thông tin blur của camera
    CAMERA_BLUR = "camera_blur"
    # Tọa độ của object trong hệ AGV
    OBJECT_POSITION = "object_position"
    # Tọa độ pixel của object
    POSITION_RAW = "position_raw"
    # Lịch sử stop, resume robot
    HISTORY_ACTION = "history_action"
    # Thông tin cấu hình của camera
    CAMERA_CONFIG = "camera_config"
    # Thông tin cấu hình của AI Edge
    AI_EDGE_CONFIG = "ai_edge_config"
    # Thông tin cấu hình của AI Edge (System config)
    SYSTEM_CONFIG = "config"
    # Thong tin status he AI 
    STATUS_AI_SYSTEM = "status_ai_system"

    WCS_STATUS = "wcs_status"

class KeyRedis:
    # Thông tin tọa độ raw object từ AI Edge
    MERGED_DATA_AI_EDGE = 'merged_data'
    # Thông tin tọa độ của AGV
    ROBOT_POSITION_DATA = 'robot_position_data'
    # Thông tin tọa độ của object trong hệ robot
    OBJECT_POSITION_DATA = 'object_position_data'
    # Thông tin độ mờ camera
    BLUR_STATUS = 'blur_status'
    # Thông tin trạng thái robot từ Thread DataSynchronizer
    REDIS_KEY_COMBINED_STATUS = 'combined_status'
    # Bat tat he thong AI 
    TURN_ON_AI = 'on_ai'

class RCS_CONFIG:
    RCS_ADDRESS = 'http://172.21.99.21:8182/rcms-dps/rest/queryAgvStatus'
    # RCS_ADDRESS = "http://172.21.99.230:5005/rcms-dps/rest/queryAgvStatus"

class Config:
    ADDRESS_SERVER = os.getenv('ADDRESS_SERVER')
    PORT_DB = int(os.getenv('PORT_DB'))
    DOCCOMENT = os.getenv('DOCCOMENT')
    USER_NAME_DB = os.getenv('USER_NAME_DB')
    PASS_WORD_DB = os.getenv('PASS_WORD_DB')
    
    MONGO_URI = (
        f'mongodb://{USER_NAME_DB}:{PASS_WORD_DB}@{ADDRESS_SERVER}:{PORT_DB}/'
        f'{DOCCOMENT}?authSource=admin'
    )
    
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    
    MQTT_BROKER = os.getenv('MQTT_BROKER', '172.21.99.230')
    MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
    
    MQTT_BROKER_WCS = os.getenv('MQTT_BROKER_WCS', '172.21.99.23')
    MQTT_PORT_WCS = int(os.getenv('MQTT_PORT_WCS', 1883))
    MQTT_PASSWORD_WCS = os.getenv('MQTT_PASSWORD', 'rostek2019')
    MQTT_USERNAME_WCS = os.getenv('MQTT_USERNAME', 'rostek')
    
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
    FLASK_HOST = os.getenv('FLASK_HOST', '172.21.99.230')
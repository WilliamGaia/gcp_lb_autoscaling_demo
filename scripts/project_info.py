import os

PROJECT = os.getenv('PROJECT',"williamlab")
MIG_NAME = os.getenv('MIG_NAME',"demo-option2-mig")#"demo-option2-mig"
MIG_ZONE = os.getenv('MIG_ZONE',"asia-east1-b")#"asia-east1-b"
MIG_MIN = int(os.getenv("MIG_MIN",1))
MIG_MAX = int(os.getenv("MIG_MAX",3))
SCALE_IN_ALERT_ID = os.getenv("SCALE_IN_ALERT_ID","12249586910524468922")
SCALE_OUT_ALERT_ID = os.getenv("SCALE_OUT_ALERT_ID","16070270594798604896")
SNOOZE_TIME = int(os.getenv("SNOOZE_TIME",5))
import os
from fastapi import FastAPI 
from .compute_scale_in import computeManager

project_id = os.getenv('PROJECT')
mig_name = os.getenv('MIG_NAME')#"demo-option2-mig"
mig_zone = os.getenv('MIG_ZONE')#"asia-east1-b"
app = FastAPI()
cm = computeManager(project_info=project_id)

@app.post("/switch_autoscaler_on/")
def switch_autoscale_on():
  trigger:str="scale_out"
  ig_name:str=mig_name
  zone:str=mig_zone
  return cm.switch_autoscaling_mode(trigger,ig_name=ig_name,zone=zone)

@app.post("/switch_autoscaler_off/")
def switch_autoscaler_off():
  trigger:str="scale_in"
  ig_name:str=mig_name
  zone:str=mig_zone
  return cm.switch_autoscaling_mode(trigger,ig_name=ig_name,zone=zone)
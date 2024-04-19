import os
from fastapi import FastAPI 
from scripts.gcp_client import GcpClient
from scripts.compute_manager import ComputeManager
from scripts.requests import ProvisionRequest

project_id = os.getenv('PROJECT',"williamlab")
mig_name = os.getenv('MIG_NAME',"demo-option2-mig")#"demo-option2-mig"
mig_zone = os.getenv('MIG_ZONE',"asia-east1-b")#"asia-east1-b"
mig_min = os.getenv("MIG_MIN",1)
mig_max = os.getenv("MIG_MAX",3)
scale_in_alert_id = os.getenv("SCALE_IN_ALERT_ID","12249586910524468922")

app = FastAPI()
client = GcpClient(project_info=project_id)
cm = ComputeManager(project_info=project_id,client=client)

@app.post("/switch_autoscaler_on/")
def switch_autoscale_on():
  trigger:str="scale_out"
  ig_name:str=mig_name
  zone:str=mig_zone
  return cm.switch_autoscaler_mode(trigger,
                                    ig_name=ig_name,
                                    zone=zone,
                                    mig_min=mig_min,
                                    mig_max=mig_max)

@app.post("/switch_autoscaler_off/")
def switch_autoscaler_off():
  trigger:str="scale_in"
  ig_name:str=mig_name
  zone:str=mig_zone
  return cm.switch_autoscaler_mode(trigger,
                                    ig_name=ig_name,
                                    zone=zone,
                                    mig_min=mig_min,
                                    mig_max=mig_max)

@app.post("/schedule_provision/")
def schedule_provision(request: ProvisionRequest):
  ig_name:str=mig_name
  zone:str=mig_zone
  is_provision: bool = request.is_provision
  provision_count: int = request.instance_count
  return cm.switch_provision_mode(ig_name=ig_name,
                         zone=zone,
                         is_provision=is_provision,
                         mig_min=mig_min,
                         mig_max=mig_max,
                         provision_count=provision_count,
                         scale_in_alert_id=scale_in_alert_id)
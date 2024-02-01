import os
from fastapi import FastAPI 
from scripts.gcp_client import GcpClient
from scripts.compute_scale_in import computeManager
from scripts.requests import ProvisionRequest
from scripts.provision_manager import ProvisionManager

project_id = os.getenv('PROJECT',"williamlab")
mig_name = os.getenv('MIG_NAME',"demo-option2-mig")#"demo-option2-mig"
mig_zone = os.getenv('MIG_ZONE',"asia-east1-b")#"asia-east1-b"
app = FastAPI()
client = GcpClient(project_info=project_id)
cm = computeManager(project_info=project_id,client=client)
pm = ProvisionManager(project_info=project_id,client=client)

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

@app.post("/schedule_provision/")
def schedule_provision(request: ProvisionRequest):
  ig_name: str = request.ig_name
  zone: str = request.zone
  is_provision: bool = request.is_provision
  provision_count: int = request.instance_count
  return pm.switch_provision_mode(ig_name=ig_name,
                         zone=zone,
                         is_provision=is_provision,
                         provision_count=provision_count)
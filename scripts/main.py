from fastapi import FastAPI 
from .gcp_client import GcpClient
from .compute_manager import ComputeManager
from .requests import ProvisionRequest
from . import project_info

app = FastAPI()
client = GcpClient(project=project_info.PROJECT)
cm = ComputeManager(client=client,project_info=project_info)

@app.post("/switch_autoscaler_on/")
def switch_autoscale_on():
  trigger:str="scale_out"
  return cm.switch_autoscaler_mode(trigger)

@app.post("/switch_autoscaler_off/")
def switch_autoscaler_off():
  trigger:str="scale_in"
  return cm.switch_autoscaler_mode(trigger)

@app.post("/schedule_provision/")
def schedule_provision(request: ProvisionRequest):
  is_provision: bool = request.is_provision
  provision_count: int = request.instance_count
  return cm.switch_provision_mode(is_provision=is_provision, provision_count=provision_count)
import os
from fastapi import FastAPI 
from .project_info import ProjectInfo
from .metric_manager import MetricManager
from .compute_scale_in import computeManager

project_id = os.getenv('PROJECT',default = "williamlab")
interval_second = os.getenv('INTERVAL',default = 480)
metric_path = os.getenv('METRIC_PATH',default="network.googleapis.com/loadbalancer/utilization")

app = FastAPI() 
project_info = ProjectInfo(project_id)
mm = MetricManager(project_info=project_info)
cm = computeManager(project_info=project_info)

@app.get("/update_avg_metric/") 
def update_avg_metric(backends: str = ""): 
  avg_value = get_avg(backends)

  mm.write_time_series(
    metric_path="avg_util",
    value=avg_value
  )
  return "Updatd metrics"

@app.get("/check_and_scale_in/")
def check_and_scale_in(protect_vm:str = "",
                       ig_name:str="demo-option1-mig",
                       backends: str = "option1-bk", 
                       zone:str="asia-east1-b",
                       max_surge:str="1"):
  avg_value = get_avg(backends)
  print("current avg_CPU_Util : ",avg_value)
  instance_dict = cm.list_instances(avg_value=avg_value,ig_name=ig_name,zone=zone)
  print("Listed Instance = ", instance_dict)
  if instance_dict == None:
    print("No Instance to delete")
    return 200
  cm.delete_last_created_vms(protect_vm=protect_vm,zone=zone,instance_dict=instance_dict,max_surge=max_surge)
  return 200

def get_avg(backends):
  return mm.read_time_series(
    metric_path=metric_path,
    backends=backends,
    interval_secs=interval_second
  )

if __name__ == "__main__":
  update_avg_metric()
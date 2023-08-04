import os,time
from fastapi import FastAPI 
from project_info import ProjectInfo
from metric_manager import MetricManager
from compute_scale_in import computeManager

project_id = os.getenv('PROJECT',default = "williamlab")
interval_second = os.getenv('INTERVAL',default = 480)
vm_cpu_metric_path = os.getenv('VM_METRIC_PATH',default="compute.googleapis.com/instance/cpu/utilization")
autoscaler_metric_path = os.getenv('AUTO_METRIC_PATH',default="autoscaler.googleapis.com/current_utilization")
# compute.googleapis.com/instance/cpu/utilization
# network.googleapis.com/loadbalancer/utilization
# autoscaler.googleapis.com/current_utilization
app = FastAPI() 
project_info = ProjectInfo(project_id)
mm = MetricManager(project_info=project_info)
cm = computeManager(project_info=project_info)

@app.get("/update_avg_metric/") 
def update_avg_metric(ig_names: str = ""): 
  avg_value = get_avg(ig_names)

  mm.write_time_series(
    metric_path="avg_util",
    value=avg_value
  )
  return "Updatd metrics"
#Option 1 API
@app.get("/check_and_scale_in/")
def check_and_scale_in(protect_vm:str = "",
                       ig_name:str="demo-option1-mig2",
                       zone:str="asia-east1-b",
                       max_surge:str="1"):

  instance_dict = cm.list_instances(get_avg=get_avg,ig_name=ig_name,zone=zone)
  print("Listed Instance = ", instance_dict)
  if instance_dict == None:
    print("No Instance to delete")
    return "No Instance to delete"
  cm.delete_last_created_vms(protect_vm=protect_vm,zone=zone,instance_dict=instance_dict,max_surge=max_surge,ig_name=ig_name)
  return "Success Delete Instances"

@app.get("/switch_autoscaler/")
def switch_autoscaler(ig_name:str="demo-option2-mig",
                      zone:str="asia-east1-b"):
  cm.switch_autoscaling_mode(ig_name=ig_name,zone=zone)

def get_avg(ig_names,type="vm_cpu_avg"):
  if type == "vm_cpu_avg":
    return mm.read_time_series(
      metric_path=vm_cpu_metric_path,
      ig_names=ig_names,
      interval_secs=interval_second,
      type=type
    )
  elif type == "autoscaler":
    return mm.read_time_series(
    metric_path=autoscaler_metric_path,
    ig_names=ig_names,
    interval_secs=interval_second,
    type="autoscaler"
  )

if __name__ == "__main__":
  # update_avg_metric(ig_names="demo-option2-mig,demo-option2-umig")
  switch_autoscaler()
  
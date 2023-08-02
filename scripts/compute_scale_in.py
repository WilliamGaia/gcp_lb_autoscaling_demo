from google.cloud import compute_v1
from .project_info import ProjectInfo
from datetime import datetime

class computeManager():
    def __init__(self,project_info: ProjectInfo):
        self.client = compute_v1.InstancesClient() # Get Instance Details
        self.auto_scaler_client = compute_v1.AutoscalersClient() # Get Autoscaling info like min_max
        self.ig_client = compute_v1.InstanceGroupsClient() # 
        self.project = project_info.project

    def list_instances(self,avg_value,ig_name,zone)-> dict:
        # Check if current IG CPU Util Higher than 60%, if so than stop process
        if avg_value >=0.15:
            print("Current AVG_CPU is: ",avg_value," No Need To Scale In")
            return
        # Check if current Instance count met the minimum count of MIG, if so than stop process
        if self.check_if_met_minimum(ig_name,zone):
            return 
        # List Instances Info and filter with only name and last_start time
        instances = {}
        request = compute_v1.ListInstancesInstanceGroupsRequest(
            project=self.project,
            zone=zone,
            instance_group=ig_name,
        )
        results = self.ig_client.list_instances(request=request)
        for result in results:
            instance_name = result.instance.partition("instances/")[-1]
            request = compute_v1.GetInstanceRequest(
                instance=instance_name,
                project=self.project,
                zone=zone
            )
            response=self.client.get(request=request)
            last_start_seconds = self.convert_date_time(response.last_start_timestamp)
            instances[instance_name] = last_start_seconds
        return instances
    
    def delete_last_created_vms(self,protect_vm,zone,instance_dict,max_surge):
        sorted_names = sorted(instance_dict, key=instance_dict.get, reverse=True)
        vm_to_delete = sorted_names[:int(max_surge)]

        if protect_vm != "":
            protect_vm = protect_vm.split(",")

        print("delete VMs : ",vm_to_delete)
        for vm in vm_to_delete:
            if vm in protect_vm:
                print("Pass the protected VM:",vm)
                continue
            request = compute_v1.DeleteInstanceRequest(
                instance=vm,
                project=self.project,
                zone=zone,
            )
            response = self.client.delete(request=request)
            print(response)
        return 200 

    def check_if_met_minimum(self,ig_name,zone)-> bool:
        request = compute_v1.GetAutoscalerRequest(
            autoscaler=ig_name,
            project=self.project,
            zone=zone,
        )
        min_num_replicas = self.auto_scaler_client.get(request=request).autoscaling_policy.min_num_replicas

        request = compute_v1.GetInstanceGroupRequest(
            project=self.project,
            zone=zone,
            instance_group=ig_name,
        )
        current_replicas = self.ig_client.get(request=request).size
        if current_replicas <= min_num_replicas:
            print("Current Instance count is met the minimum count")
            return True
        
    def convert_date_time(self,time_string) -> int:
        dt = datetime.strptime(time_string,"%Y-%m-%dT%H:%M:%S.%f%z")
        return int(dt.timestamp())
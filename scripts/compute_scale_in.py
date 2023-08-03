import time
from google.cloud import compute_v1
from project_info import ProjectInfo
from datetime import datetime

class computeManager():
    def __init__(self,project_info: ProjectInfo):
        self.client = compute_v1.InstancesClient() # Get Instance Details
        self.auto_scaler_client = compute_v1.AutoscalersClient() # Get Autoscaling info like min_max
        self.ig_client = compute_v1.InstanceGroupsClient() # 
        self.ig_manager_client = compute_v1.InstanceGroupManagersClient()
        self.project = project_info.project

    def list_instances(self,get_avg,ig_name,zone)-> dict:
        # Check if current IG CPU Util Higher than 15%, if so than stop process
        avg_value = get_avg(ig_name,type="vm_cpu_avg")
        if avg_value >=0.15:
            print("Current AVG_CPU is: ",avg_value," No Need To Scale In")
            return
        #Iif vm scale out than wait for the CPU Util update than check if is scaling up
        time.sleep(60)
        autoscaler_value =get_avg(ig_name,type="autoscaler")
        print("AutoScaler CPU is: ",autoscaler_value)
        if autoscaler_value >=0.15:
            print("AutoScaler CPU is: ",autoscaler_value," No Need To Scale In")
            return
        # Check if current Instance count met the minimum count of MIG, if so than stop process
        if self.check_if_met_minimum(ig_name,zone):
            return
        if self.check_if_mig_working(ig_name,zone):
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
    
    def delete_last_created_vms(self,protect_vm,zone,instance_dict,max_surge,ig_name):
        sorted_names = sorted(instance_dict, key=instance_dict.get, reverse=True)
        vm_to_delete = sorted_names[:int(max_surge)]

        if protect_vm != "":
            protect_vm = protect_vm.split(",")
        #TODO STILL NEED TO RESTRUCT THE DELETE FLOW
        print("delete VMs : ",vm_to_delete)
        for vm in vm_to_delete:
            if vm in protect_vm:
                print("Pass the protected VM:",vm)
                continue
            request = compute_v1.DeleteInstancesInstanceGroupManagerRequest(
                instance_group_managers_delete_instances_request_resource=
                compute_v1.InstanceGroupManagersDeleteInstancesRequest(instances=['zones/{}/instances/{}'.format(zone,vm)]),
                instance_group_manager=ig_name,
                project=self.project,
                zone=zone,
            )
            response = self.ig_manager_client.delete_instances(request=request)
            print(response)
        return 200 

    def check_if_met_minimum(self,ig_name,zone)-> bool:
        request = compute_v1.GetAutoscalerRequest(
            autoscaler=ig_name,
            project=self.project,
            zone=zone,
        )
        response = self.auto_scaler_client.get(request=request)
        min_num_replicas = response.autoscaling_policy.min_num_replicas
 
        request = compute_v1.GetInstanceGroupRequest(
            project=self.project,
            zone=zone,
            instance_group=ig_name,
        )
        response = self.ig_client.get(request=request)
        current_replicas = response.size

        if current_replicas <= min_num_replicas:
            print("Current Instance count is met the minimum count")
            return True
        return False
    
    def check_if_mig_working(self,ig_name,zone)-> bool:
        request = compute_v1.ListManagedInstancesInstanceGroupManagersRequest(
        instance_group_manager=ig_name,
        project=self.project,
        zone=zone,
        )
        response = self.ig_manager_client.list_managed_instances(request=request)
        for page in response.pages:
            print(page.managed_instances)
            for instance in page.managed_instances:
                if instance.current_action != "NONE":
                    return True
        return False
    
    def convert_date_time(self,time_string) -> int:
        dt = datetime.strptime(time_string,"%Y-%m-%dT%H:%M:%S.%f%z")
        return int(dt.timestamp())
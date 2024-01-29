from google.cloud import compute_v1

class computeManager():
    def __init__(self,project_info:str):
        self.auto_scaler_client = compute_v1.AutoscalersClient() # Get Autoscaling info like ON or OFF
        self.ig_client = compute_v1.InstanceGroupsClient() # Get MIG VM Info
        self.ig_manager_client = compute_v1.InstanceGroupManagersClient() # Update MIG Contents
        self.project = project_info
    
    def switch_autoscaling_mode(self,trigger,ig_name,zone):
        request = compute_v1.GetAutoscalerRequest(
            autoscaler=ig_name,
            project=self.project,
            zone=zone,
        )
        response = self.auto_scaler_client.get(request=request)
        current_policy = response.autoscaling_policy
        current_mode = current_policy.mode
        
        if current_mode == "ON":
            if trigger == "scale_out":
                print("Current Mode is ON So Don't Need to Switch")
                return ('Status',200)
            
            response.autoscaling_policy.mode = "OFF"
            response.autoscaling_policy.min_num_replicas = 1

            request = compute_v1.UpdateAutoscalerRequest(
                autoscaler=ig_name,
                autoscaler_resource=response,
                project=self.project,
                zone=zone,)
            self.auto_scaler_client.update(request=request)
            request = compute_v1.ListInstancesInstanceGroupsRequest(
                project=self.project,
                zone=zone,
                instance_group=ig_name,)
            results = self.ig_client.list_instances(request=request)
            instance_list = []
            for result in results:
                instance_name = 'zones/{}/instances/{}'.format(zone,result.instance.partition("instances/")[-1])
                instance_list.append(instance_name)

            self.update_mig_size(ig_name,zone,0)
            
            request = compute_v1.DeleteInstancesInstanceGroupManagerRequest(
                instance_group_managers_delete_instances_request_resource=
                compute_v1.InstanceGroupManagersDeleteInstancesRequest(
                instances=instance_list),
                instance_group_manager=ig_name,
                project=self.project,
                zone=zone,)
            self.ig_manager_client.delete_instances(request=request)
        elif current_mode == "OFF":
            if trigger == "scale_in":
                print("Current Mode is OFF So Don't Need to Switch")
                return ('Status',200)
            
            num_of_static_instance = self.check_instance_number(ig_name,zone)
            if num_of_static_instance > 0:
                response.autoscaling_policy.min_num_replicas = num_of_static_instance

            response.autoscaling_policy.mode = "ON"
            
            request = compute_v1.UpdateAutoscalerRequest(
                autoscaler=ig_name,
                autoscaler_resource=response,
                project=self.project,
                zone=zone,
            )
            response = self.auto_scaler_client.update(request=request)
        return ('Status',200)
    

    def check_instance_number(self,ig_name,zone)-> int:
        get_request = compute_v1.GetInstanceGroupManagerRequest(
            instance_group_manager=ig_name,
            project=self.project,
            zone=zone,)
        response = self.ig_manager_client.get(request=get_request)
        return response.target_size
    
    def update_mig_size(self,ig_name,zone,size)-> int:
        request = compute_v1.ResizeInstanceGroupManagerRequest(
        instance_group_manager=ig_name,
        project=self.project,
        size=size,
        zone=zone,
        )
        self.ig_manager_client.resize(request=request)
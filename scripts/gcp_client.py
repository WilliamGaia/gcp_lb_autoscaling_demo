from google.cloud import compute_v1, monitoring_v3

class GcpClient():
    def __init__(self,project_info:str):
        self.auto_scaler_client = compute_v1.AutoscalersClient() # Get Autoscaling info like ON or OFF
        self.ig_client = compute_v1.InstanceGroupsClient() # Get MIG VM Info
        self.ig_manager_client = compute_v1.InstanceGroupManagersClient() # Update MIG Contents
        self.alert_client = monitoring_v3.AlertPolicyServiceClient() #Update Alert policy
        self.project = project_info

    def get_autoscaler_info(self,ig_name,zone):
        request = compute_v1.GetAutoscalerRequest(
            autoscaler=ig_name,
            project=self.project,
            zone=zone,
        )
        response = self.auto_scaler_client.get(request=request)
        return response
    
    def update_autoscaler(self,ig_name,zone,resource):
        request = compute_v1.UpdateAutoscalerRequest(
            autoscaler=ig_name,
            autoscaler_resource=resource,
            project=self.project,
            zone=zone,)
        self.auto_scaler_client.update(request=request)

    def list_mig_instances(self,ig_name,zone):
        request = compute_v1.ListInstancesInstanceGroupsRequest(
                project=self.project,
                zone=zone,
                instance_group=ig_name,)
        results = self.ig_client.list_instances(request=request)
        instance_list = []
        for result in results:
            instance_name = 'zones/{}/instances/{}'.format(zone,result.instance.partition("instances/")[-1])
            instance_list.append(instance_name)
        return instance_list
    
    def delete_mig_instances(self,ig_name,zone,instance_list):
        request = compute_v1.DeleteInstancesInstanceGroupManagerRequest(
                instance_group_managers_delete_instances_request_resource=
                compute_v1.InstanceGroupManagersDeleteInstancesRequest(
                instances=instance_list),
                instance_group_manager=ig_name,
                project=self.project,
                zone=zone,)
        self.ig_manager_client.delete_instances(request=request)
    
    def update_mig_size(self,ig_name,zone,size):
        request = compute_v1.ResizeInstanceGroupManagerRequest(
        instance_group_manager=ig_name,
        project=self.project,
        size=size,
        zone=zone,
        )
        self.ig_manager_client.resize(request=request)

    def check_instance_number(self,ig_name,zone)-> int:
        get_request = compute_v1.GetInstanceGroupManagerRequest(
            instance_group_manager=ig_name,
            project=self.project,
            zone=zone,)
        response = self.ig_manager_client.get(request=get_request)
        return response.target_size
    

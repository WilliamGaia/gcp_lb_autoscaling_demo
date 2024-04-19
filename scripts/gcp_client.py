from google.cloud import compute_v1, monitoring_v3
from google.protobuf import wrappers_pb2 as wrappers

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
        try:
            response = self.auto_scaler_client.get(request=request)
        except Exception as e:
            print(f"Failed to retrieve autoscaler info: {e}")
            return 500
        return response
    
    def update_autoscaler(self,ig_name,zone,resource):
        request = compute_v1.UpdateAutoscalerRequest(
            autoscaler=ig_name,
            autoscaler_resource=resource,
            project=self.project,
            zone=zone,)
        try:
            self.auto_scaler_client.update(request=request)
        except Exception as e:
            print(f"Failed to update autoscaler info: {e}")
            return 500
        
    def list_mig_instances(self,ig_name,zone):
        request = compute_v1.ListInstancesInstanceGroupsRequest(
                project=self.project,
                zone=zone,
                instance_group=ig_name,)
        try:
            results = self.ig_client.list_instances(request=request)
        except Exception as e:
            print(f"Failed to list mig instance: {e}")
            return 500
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
        try:
            self.ig_manager_client.delete_instances(request=request)
        except Exception as e:
            print(f"Failed to delete mig instance: {e}")
            return 500
    
    def set_number_of_instances(self,ig_name,zone,size):
        request = compute_v1.ResizeInstanceGroupManagerRequest(
        instance_group_manager=ig_name,
        project=self.project,
        size=size,
        zone=zone,
        )
        try:
            self.ig_manager_client.resize(request=request)
        except Exception as e:
            print(f"Failed to set mig instance numbers: {e}")
            return 500

    def check_instance_number(self,ig_name,zone)-> int:
        get_request = compute_v1.GetInstanceGroupManagerRequest(
            instance_group_manager=ig_name,
            project=self.project,
            zone=zone,)
        try:
            response = self.ig_manager_client.get(request=get_request)
        except Exception as e:
            print(f"Failed to get mig instance numbers: {e}")
            return 500
        return response.target_size
    
    def get_alert_info(self, policy_id:str):
        try:
            response = self.alert_client.get_alert_policy(name=self._get_policy_name(policy_id))
        except Exception as e:
            print(f"Failed to get alert policy: {e}")
            return 500
        return response
    
    def update_alert_policy(self, alert_policy:monitoring_v3.AlertPolicy):
        try:
            response = self.alert_client.update_alert_policy(alert_policy=alert_policy)
        except Exception as e:
            print(f"Failed to update alert policy: {e}")
            return 500
        return response
    
    def get_alert_list(self):
        try:
            response = self.alert_client.list_alert_policies(name=f"projects/{self.project}")
        except Exception as e:
            print(f"Failed to get alert policy list: {e}")
            return 500
        return response

    def _get_policy_name(self,policy:str) -> str:
        return f"projects/{self.project}/alertPolicies/{policy}"
    

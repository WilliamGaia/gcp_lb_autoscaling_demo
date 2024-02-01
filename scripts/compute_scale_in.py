from scripts.gcp_client import GcpClient

class computeManager():
    def __init__(self,project_info:str,client: GcpClient):
        self.project = project_info
        self.client = client
    
    def switch_autoscaling_mode(self,trigger,ig_name,zone):
        response = self.client.get_autoscaler_info(ig_name,zone)
        current_policy = response.autoscaling_policy
        current_mode = current_policy.mode
        
        if current_mode == "ON":
            if trigger == "scale_out":
                print("Current Mode is ON So Don't Need to Switch")
                return ('Status',200)
            
            response.autoscaling_policy.mode = "OFF"
            response.autoscaling_policy.min_num_replicas = 1

            self.client.update_autoscaler(ig_name=ig_name,zone=zone,resource=response)

            instance_list = self.client.list_mig_instances(ig_name,zone)

            self.client.update_mig_size(ig_name,zone,0)

            self.client.delete_mig_instances(ig_name,zone,instance_list)

        elif current_mode == "OFF":
            if trigger == "scale_in":
                print("Current Mode is OFF So Don't Need to Switch")
                return ('Status',200)
            
            num_of_static_instance = self.client.check_instance_number(ig_name,zone)
            if num_of_static_instance > 0:
                response.autoscaling_policy.min_num_replicas = num_of_static_instance

            response.autoscaling_policy.mode = "ON"
            
            self.client.update_autoscaler(ig_name=ig_name,zone=zone,resource=response)

        return ('Status',200)
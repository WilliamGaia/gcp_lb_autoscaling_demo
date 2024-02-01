from scripts.gcp_client import GcpClient

class ProvisionManager():
    def __init__(self,project_info:str,client: GcpClient):
        self.project = project_info
        self.client = client

    def switch_provision_mode(self,ig_name,zone,is_provision,provision_count):
        #check if is autoscaling on
        autoscaler_info = self.client.get_autoscaler_info(ig_name=ig_name,zone=zone)
        autoscaling_mode = autoscaler_info.autoscaling_policy.mode
        current_instance_count = self.client.check_instance_number(ig_name=ig_name,zone=zone)
        print(autoscaling_mode)
        print(current_instance_count)
        if autoscaling_mode == "ON":
            if current_instance_count > provision_count:
                provision_count = current_instance_count        
                
        elif autoscaling_mode == "OFF":
            if current_instance_count > provision_count:
                provision_count = current_instance_count
                

        self.client.update_mig_size(ig_name=ig_name,zone=zone,size=provision_count)
        autoscaler_info.autoscaling_policy.mode = "OFF"
        self.client.update_autoscaler(ig_name=ig_name,zone=zone,resource=autoscaler_info)
        #check MIG number of instance counts.
        return ('status',200)
    
    def switch_scaling_alert(self):
        return
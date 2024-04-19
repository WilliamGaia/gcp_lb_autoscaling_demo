from scripts.gcp_client import GcpClient

class ComputeManager():
    def __init__(self,project_info:str,client: GcpClient):
        self.project = project_info
        self.client = client
    
    def switch_autoscaler_mode(self,trigger,ig_name,zone,mig_min,mig_max):
        self._validate_parameters(ig_name,zone,mig_min,mig_max)
        
        autoscaler_info = self.client.get_autoscaler_info(ig_name,zone)
        autoscaler_mode = autoscaler_info.autoscaling_policy.mode
        #Use the number of instances metadata as State Storage
        num_of_instances = self.client.check_instance_number(ig_name,zone)

        #Repeated Event bypass
        if self._should_skip_switch(trigger, autoscaler_mode):
            print(f"Current Mode is {autoscaler_mode} So Don't Need to Switch")
            return 200

        if autoscaler_mode == "ON":
            self._handle_autoscaler_off(ig_name, zone, autoscaler_info, mig_min, mig_max, num_of_instances)
        elif autoscaler_mode == "OFF":            
            self._handle_autoscaler_on(ig_name, zone, autoscaler_info, num_of_instances)

        return 200
    
    def switch_provision_mode(self,ig_name,zone,is_provision,mig_min,mig_max,provision_count):
        self._validate_parameters(ig_name,zone,mig_min,is_provision)
        
        autoscaler_info = self.client.get_autoscaler_info(ig_name,zone)
        autoscaler_mode = autoscaler_info.autoscaling_policy.mode

        if is_provision == True:
            #check if autoscaling is on, if is on ...
            #1.Update MIG Size to set the number of instances/minimum to provision_count
            #2.Cancel down to zero setting when autoscaling off (Inplement in switch_autoscaler_mode)
                    #Validate input parameter
            if provision_count <= 0:
                raise ValueError('provision_count must be greater than 0 when using schedule settings.')
            self._handle_schedule_provision_on(ig_name, zone, autoscaler_info, autoscaler_mode, provision_count)  
        else:
            self._handle_schedule_provision_off(ig_name, zone, autoscaler_info, autoscaler_mode, mig_min, mig_max)
        
        return 200
    
    def _should_skip_switch(self, trigger, autoscaler_mode):
        return (trigger == "scale_out" and autoscaler_mode == "ON") or (trigger == "scale_in" and autoscaler_mode == "OFF")
       
    def _handle_autoscaler_off(self, ig_name, zone, autoscaler_info, mig_min, mig_max, num_of_instances):
        #Turn off the autoscaler
        autoscaler_info.autoscaling_policy.mode = "OFF"
        #Initialized the min/max value for next time usage
        autoscaler_info.autoscaling_policy.min_num_replicas = mig_min
        autoscaler_info.autoscaling_policy.max_num_replicas = mig_max
        self.client.update_autoscaler(ig_name=ig_name,zone=zone,resource=autoscaler_info)

        #Set the number of instances back to zero if no scheduled count
        self.client.set_number_of_instances(ig_name,zone,num_of_instances)
        print("number of instances: ",num_of_instances)
        #TODO if schedule windows ended, delete all instance inside MIG to perform down to zero
        #Get the list of instances name inside mig
        instance_list = self.client.list_mig_instances(ig_name,zone)
        self.client.delete_mig_instances(ig_name,zone,instance_list)

    def _handle_autoscaler_on(self, ig_name, zone, autoscaler_info, num_of_instances):
        #Set the min size to number of instances to meet the scheduled count
        if num_of_instances > 0:
            autoscaler_info.autoscaling_policy.min_num_replicas = num_of_instances
        #If scheduled counts higher than maximum, set the maximum to scheduled counts
        autoscaler_info.autoscaling_policy.max_num_replicas = max(
            autoscaler_info.autoscaling_policy.max_num_replicas,
            num_of_instances
        )
        #Turn on the autoscaler
        autoscaler_info.autoscaling_policy.mode = "ON"
        self.client.update_autoscaler(ig_name=ig_name,zone=zone,resource=autoscaler_info)
    
    def _handle_schedule_provision_on(self, ig_name, zone, autoscaler_info, autoscaler_mode, provision_count):
        #If autoscaling is on than set the min counts to schedule counts.
        if autoscaler_mode == "ON":
            autoscaler_info.autoscaling_policy.min_num_replicas = provision_count
            if provision_count > autoscaler_info.autoscaling_policy.max_num_replicas:
                autoscaler_info.autoscaling_policy.max_num_replicas = provision_count
            self.client.update_autoscaler(ig_name=ig_name,zone=zone,resource=autoscaler_info)
            print("Autoscaler min value has been changed to scheduled value")

        current_instance_count = self.client.check_instance_number(ig_name=ig_name,zone=zone)

        #check if current MIG instances count is larger than scheduled counts
        #if so than set the scheduled count as current count.
        adjusted_count = max(provision_count, current_instance_count)
        self.client.set_number_of_instances(ig_name=ig_name,zone=zone,size=adjusted_count)
        print(f"Scheduled provision has been adjusted to {adjusted_count}.")

    def _handle_schedule_provision_off(self, ig_name, zone, autoscaler_info, autoscaler_mode, mig_min,mig_max):
        #Set the min back to default if autoscaling is on
        if autoscaler_mode == "ON":
            autoscaler_info.autoscaling_policy.min_num_replicas = mig_min
            autoscaler_info.autoscaling_policy.max_num_replicas = mig_max
            self.client.update_autoscaler(ig_name=ig_name,zone=zone,resource=autoscaler_info)
            print("Autoscaler minimum value reset to default.")
        else:
        # Update number of instnaces to zero to end scheduled window
            self.client.set_number_of_instances(ig_name=ig_name,zone=zone,size=0)
        print("Scheduled provision has been turned off.")

    def _switch_alert_policy(self, policy_id:str, is_enable:bool):
        policy_info = self.client.get_alert_info(policy_id)
        policy_info.enabled = is_enable
        response = self.client.update_alert_policy(policy_info)
        print(f"The Policy '{response.display_name}' enable value has been set to: {is_enable}")

    def _validate_parameters(self, ig_name, zone, mig_min,mig_max=3,is_provision=False):
        if not ig_name:
            raise ValueError("Instance group name must be provided")
        if not zone:
            raise ValueError("Zone must be provided")
        if not isinstance(mig_min, int) or mig_min < 0:
            raise ValueError("Minimum number of instances must be a non-negative integer")
        if not isinstance(mig_max, int) or mig_max <= 0:
            raise ValueError("Maximum number of instances must be a greater than 0 integer")
        if not isinstance(is_provision, bool):
            raise ValueError("Provision mode must be a Boolean")

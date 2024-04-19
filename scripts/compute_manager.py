from scripts.gcp_client import GcpClient

class ComputeManager():
    def __init__(self,project_info:str,client: GcpClient):
        self.project = project_info
        self.client = client
    
    def switch_autoscaler_mode(self,trigger,ig_name,zone,mig_min,mig_max):
        self._validate_parameters(ig_name,zone,mig_min,mig_max)
        autoscaler_info = self.client.get_autoscaler_info(ig_name,zone)
        autoscaler_mode = autoscaler_info.autoscaling_policy.mode    
        #Repeated Event bypass
        if self._should_skip_switch(trigger, autoscaler_mode):
            print(f"Current Mode is {autoscaler_mode} So Don't Need to Switch")
            return 200
        if autoscaler_mode == "ON":
            self._handle_autoscaler_off(ig_name, zone, autoscaler_info, mig_min, mig_max)
        elif autoscaler_mode == "OFF":            
            self._handle_autoscaler_on(ig_name, zone, autoscaler_info)
        return 200
    
    def switch_provision_mode(self, ig_name,zone, is_provision, mig_min, mig_max, provision_count, scale_in_alert_id:str):
        self._validate_parameters(ig_name,zone,mig_min,mig_max,is_provision)
        autoscaler_info = self.client.get_autoscaler_info(ig_name,zone)
        if is_provision == True:
            #Validate input parameter
            if provision_count <= 0:
                raise ValueError('provision_count must be greater than 0 when using schedule settings.')
            self._handle_schedule_provision_on(ig_name, zone, autoscaler_info, provision_count, scale_in_alert_id)  
        else:
            self._handle_schedule_provision_off(ig_name, zone, autoscaler_info, mig_min, mig_max, scale_in_alert_id)
        return 200
    
    def _should_skip_switch(self, trigger, autoscaler_mode):
        return (trigger == "scale_out" and autoscaler_mode == "ON") or (trigger == "scale_in" and autoscaler_mode == "OFF")
    
    def _handle_schedule_provision_on(self, ig_name, zone, autoscaler_info, provision_count, scale_in_alert_id:str):
        #Turn off scale-in event
        print("Disable scale-in alert policy")
        self._switch_alert_policy(policy_id=scale_in_alert_id, is_enable=False)
        #Turn on autoscaling and set the min/max based on input provision count. 
        autoscaler_info.autoscaling_policy.min_num_replicas = self._find_max(
            autoscaler_info.autoscaling_policy.min_num_replicas,
            provision_count)
        autoscaler_info.autoscaling_policy.max_num_replicas = self._find_max(
            autoscaler_info.autoscaling_policy.max_num_replicas,
            provision_count)
        self._handle_autoscaler_on(ig_name, zone, autoscaler_info)
        print("Schedule window Start.")

    def _handle_autoscaler_on(self, ig_name, zone, autoscaler_info):
        #Get current number of instances in mig (manual setting)
        #Modify the autoscaler min/max value if the manual setting is bigger.
        num_of_instances = self.client.check_instance_number(ig_name,zone)
        autoscaler_info.autoscaling_policy.min_num_replicas = self._find_max(
            autoscaler_info.autoscaling_policy.min_num_replicas,
            num_of_instances)
        autoscaler_info.autoscaling_policy.max_num_replicas = self._find_max(
            autoscaler_info.autoscaling_policy.max_num_replicas,
            num_of_instances)
        #Turn on the autoscaler
        autoscaler_info.autoscaling_policy.mode = "ON"
        self.client.update_autoscaler(ig_name=ig_name,zone=zone,resource=autoscaler_info)
        print("Turn on autoscaler success.")

    def _handle_schedule_provision_off(self, ig_name, zone, autoscaler_info, mig_min,mig_max, scale_in_alert_id:str):
        #Reset the autoscaler min/max back to default settings
        self._reset_scaling_min_max(ig_name, zone, autoscaler_info, mig_min, mig_max)
        #Turn on scale-in event
        print("Enable scale-in alert policy.")
        self._switch_alert_policy(policy_id=scale_in_alert_id, is_enable=True)
        print("Schedule window end.")

    def _handle_autoscaler_off(self, ig_name, zone, autoscaler_info, mig_min, mig_max):
        #Turn off the autoscaler
        autoscaler_info.autoscaling_policy.mode = "OFF"
        #Initialized the min/max value for next time usage
        self._reset_scaling_min_max(ig_name, zone, autoscaler_info, mig_min, mig_max)
        #Set the number of instances back to zero
        self.client.set_number_of_instances(ig_name,zone,0)
        #TODO TRY TRY SEE!!!!!!!!!!!!!!!!!!!!!!!!!!!
        # instance_list = self.client.list_mig_instances(ig_name,zone)
        # self.client.delete_mig_instances(ig_name,zone,instance_list)
        print("Turn off autoscaler success, MIG down to zero.")

    def _reset_scaling_min_max(self, ig_name, zone, autoscaler_info, mig_min, mig_max):
        autoscaler_info.autoscaling_policy.min_num_replicas = mig_min
        autoscaler_info.autoscaling_policy.max_num_replicas = mig_max
        self.client.update_autoscaler(ig_name=ig_name,zone=zone,resource=autoscaler_info)

    def _switch_alert_policy(self, policy_id:str, is_enable:bool):
        policy_info = self.client.get_alert_info(policy_id)
        if policy_info.enabled == is_enable:
            print(f"Current policy '{policy_info.display_name}' enable_state is already {is_enable} So Don't Need to Switch")
        else:
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
    
    def _find_max(self, *args):
        if not args:
            raise ValueError("No argument provided")
        return max(args)
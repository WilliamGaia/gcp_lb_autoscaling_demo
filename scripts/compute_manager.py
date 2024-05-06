from .gcp_client import GcpClient
from .emum import EventListenerStatus as event_status, SnoozeTarget 

class ComputeManager():
    def __init__(self, client: GcpClient, project_info):
        self.project_info = project_info
        self.client = client
    
    def switch_autoscaler_mode(self,trigger):
        self._validate_parameters()
        autoscaler_info = self.client.get_autoscaler_info(self.project_info.MIG_NAME,self.project_info.MIG_ZONE)
        autoscaler_mode = autoscaler_info.autoscaling_policy.mode    
        #Repeated Event bypass
        if self._should_skip_switch(trigger, autoscaler_mode):
            print(f"Current Mode is {autoscaler_mode} So Don't Need to Switch")
            return 200
        if autoscaler_mode == "ON":
            self._snooze_policy("scaler_off_event_snoozing",SnoozeTarget.SCALE_IN,self.project_info.SNOOZE_TIME)
            print("Triggered autocaler off event, snooze the scale in policy...")
            #Check if current instances down to minimum
            num_of_instances = self.client.check_instance_number(self.project_info.MIG_NAME,self.project_info.MIG_ZONE)
            print(f"Current Number of Instances = {num_of_instances}")
            if num_of_instances > autoscaler_info.autoscaling_policy.min_num_replicas:
                print("Current MIG instance counts is higher than minimum, pass the down to zero process until autoscaler auto-delete instance...")
                return 200
            self._handle_autoscaler_off(autoscaler_info)
            self._modify_alert_status(event_status.SCALEOUT_ONLY)
        elif autoscaler_mode == "OFF":
            self._snooze_policy("scaler_on_event_snoozing",SnoozeTarget.SCALE_OUT,self.project_info.SNOOZE_TIME)
            print("Triggered autocaler on event, snooze the scale out policy...")          
            self._handle_autoscaler_on(autoscaler_info)
            self._modify_alert_status(event_status.SCALEIN_ONLY)
        return 200
    
    def switch_provision_mode(self, is_provision, provision_count):
        self._validate_parameters(is_provision)
        autoscaler_info = self.client.get_autoscaler_info(self.project_info.MIG_NAME,self.project_info.MIG_ZONE)
        if is_provision == True:
            #Validate input parameter
            if provision_count <= 0:
                raise ValueError('provision_count must be greater than 0 when using schedule settings.')
            #Turn off scale-in/out event
            print("Disable ALL alert policy")
            self._modify_alert_status(event_status.DISABLE_ALL)
            self._snooze_policy("scaler_event_snoozing",SnoozeTarget.ALL,self.project_info.SNOOZE_TIME)
            print("Triggered Scheduler provision event, snooze the scale policies...")  
            self._handle_schedule_provision_on(autoscaler_info, provision_count)  
        else:
            self._handle_schedule_provision_off(autoscaler_info)
            self._modify_alert_status(event_status.SCALEIN_ONLY)
            #Turn on scale-in event
            print("Enable scale-in alert policy.")
            print("Schedule window end.")
        return 200
    
    def _should_skip_switch(self, trigger, autoscaler_mode):
        return (trigger == "scale_out" and autoscaler_mode == "ON") or (trigger == "scale_in" and autoscaler_mode == "OFF")
    
    def _handle_schedule_provision_on(self, autoscaler_info, provision_count):
        #Turn on autoscaling and set the min/max based on input provision count. 
        #TODO Should change to set min if not equal than min.
        autoscaler_info.autoscaling_policy.min_num_replicas = provision_count
        autoscaler_info.autoscaling_policy.max_num_replicas = self._find_max(
            autoscaler_info.autoscaling_policy.max_num_replicas,
            provision_count)
        self._handle_autoscaler_on(autoscaler_info)
        print("Schedule window Start.")

    def _handle_autoscaler_on(self, autoscaler_info):
        #Get current number of instances in mig (manual setting)
        #Modify the autoscaler max value if the manual setting is bigger,
        #to make sure that the manual setup's vm won't be delete at autoscaler on.
        num_of_instances = self.client.check_instance_number(self.project_info.MIG_NAME,
                                                             self.project_info.MIG_ZONE)
        autoscaler_info.autoscaling_policy.max_num_replicas = self._find_max(
            autoscaler_info.autoscaling_policy.max_num_replicas,
            num_of_instances)
        #Turn on the autoscaler
        autoscaler_info.autoscaling_policy.mode = "ON"
        self.client.update_autoscaler(self.project_info.MIG_NAME,
                                      self.project_info.MIG_ZONE,
                                      resource=autoscaler_info)
        print("Turn on autoscaler success.")

    def _handle_schedule_provision_off(self, autoscaler_info):
        #Reset the autoscaler min/max back to default settings
        self._reset_scaling_min_max(autoscaler_info)

    def _handle_autoscaler_off(self, autoscaler_info):
        #Turn off the autoscaler
        autoscaler_info.autoscaling_policy.mode = "OFF"
        #Initialized the min/max value for next time usage
        self._reset_scaling_min_max(autoscaler_info)
        #Set the number of instances back to zero
        self.client.set_number_of_instances(self.project_info.MIG_NAME,
                                            self.project_info.MIG_ZONE,
                                            0)        
        print("Turn off autoscaler success, MIG down to zero.")

    def _reset_scaling_min_max(self, autoscaler_info):
        autoscaler_info.autoscaling_policy.min_num_replicas = self.project_info.MIG_MIN
        autoscaler_info.autoscaling_policy.max_num_replicas = self.project_info.MIG_MAX
        self.client.update_autoscaler(self.project_info.MIG_NAME,
                                      self.project_info.MIG_ZONE,
                                      resource=autoscaler_info)

    def _modify_alert_status(self, status):
        if status == event_status.DISABLE_ALL:
            self._switch_alert_policy(policy_id=self.project_info.SCALE_IN_ALERT_ID, is_enable=False)
            self._switch_alert_policy(policy_id=self.project_info.SCALE_OUT_ALERT_ID, is_enable=False)
        elif status == event_status.SCALEIN_ONLY:
            self._switch_alert_policy(policy_id=self.project_info.SCALE_IN_ALERT_ID, is_enable=True)
            self._switch_alert_policy(policy_id=self.project_info.SCALE_OUT_ALERT_ID, is_enable=False)
        elif status == event_status.SCALEOUT_ONLY:
            self._switch_alert_policy(policy_id=self.project_info.SCALE_IN_ALERT_ID, is_enable=False)
            self._switch_alert_policy(policy_id=self.project_info.SCALE_OUT_ALERT_ID, is_enable=True)

    def _switch_alert_policy(self, policy_id:str, is_enable:bool):
        policy_info = self.client.get_alert_info(policy_id)
        if policy_info.enabled == is_enable:
            print(f"Current policy '{policy_info.display_name}' enable_state is already {is_enable} So Don't Need to Switch")
        else:
            policy_info.enabled = is_enable
            response = self.client.update_alert_policy(policy_info)
            print(f"The Policy '{response.display_name}' enable value has been set to: {is_enable}")

    def _snooze_policy(self,name,target,interval:int):
        if target == SnoozeTarget.SCALE_IN or target == SnoozeTarget.ALL:
            self.client.create_alert_snooze(f"{name}",
                                            policy=self.project_info.SCALE_IN_ALERT_ID,
                                            interval_min=interval)
        if target == SnoozeTarget.SCALE_OUT or target == SnoozeTarget.ALL:
            self.client.create_alert_snooze(f"{name}",
                                            policy=self.project_info.SCALE_OUT_ALERT_ID,
                                            interval_min=interval)
    
    def _validate_parameters(self, is_provision=False):
        if not self.project_info.MIG_NAME:
            raise ValueError("Instance group name must be provided")
        if not self.project_info.MIG_ZONE:
            raise ValueError("Zone must be provided")
        if not isinstance(self.project_info.MIG_MIN, int) or self.project_info.MIG_MIN < 0:
            raise ValueError("Minimum number of instances must be a non-negative integer")
        if not isinstance(self.project_info.MIG_MAX, int) or self.project_info.MIG_MAX <= 0:
            raise ValueError("Maximum number of instances must be a greater than 0 integer")
        if not isinstance(is_provision, bool):
            raise ValueError("Provision mode must be a Boolean")
    
    def _find_max(self, *args):
        if not args:
            raise ValueError("No argument provided")
        return max(args)
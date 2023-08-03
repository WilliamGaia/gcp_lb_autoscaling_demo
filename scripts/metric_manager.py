import time
from google.cloud import monitoring_v3 as monitor
from project_info import ProjectInfo

class MetricManager():
    def __init__(self,project_info: ProjectInfo):
        self.client = monitor.MetricServiceClient()
        self.project = f"projects/{project_info.project}"

    def read_time_series(self,metric_path,ig_names,interval_secs=480,type="vm_cpu_avg") -> float:
        now = time.time()
        seconds = int(now)
        nanos = int((now - seconds) * 10**9)
        interval = monitor.TimeInterval(
            {
                "end_time": {"seconds": seconds, "nanos": nanos},
                "start_time": {"seconds": (seconds - interval_secs), "nanos": nanos},
            }
        )
        if type == "vm_cpu_avg":
            aggregation = monitor.Aggregation(
            {
                "alignment_period": {"seconds": 60},  # 1 minutes
                "per_series_aligner": monitor.Aggregation.Aligner.ALIGN_MEAN,
                "cross_series_reducer": monitor.Aggregation.Reducer.REDUCE_MEAN,
                "group_by_fields": ["metadata.system_labels.instance_group"],
            })
        elif type == "autoscaler":
            aggregation = monitor.Aggregation(
            {
                "alignment_period": {"seconds": 60},  # 1 minutes
                "per_series_aligner": monitor.Aggregation.Aligner.ALIGN_MEAN,
                "cross_series_reducer": monitor.Aggregation.Reducer.REDUCE_SUM,
                "group_by_fields": ["resource.instance_group_manager_name"],
            })
        else:
            print("No Metrics Type Match")
            return
        
        results = self.client.list_time_series(
            request={
                "name": self.project,
                "filter": f'metric.type = "{metric_path}"',
                "interval": interval,
                "view": monitor.ListTimeSeriesRequest.TimeSeriesView.FULL,
                "aggregation": aggregation,
            }
        )

        last_point_values = []
        if ig_names != "":
            ig_names = ig_names.split(",")
        # print(results.time_series[0].points[0])
        for result in results:
            # print(result.metadata.system_labels.fields["instance_group"].string_value)
            # print(result.points[0].value.double_value)
            # bk_name = result.resource.labels["backend_service_name"]
            # bk_value = result.points[0].value.double_value
            if type == "vm_cpu_avg":
                ig_name = result.metadata.system_labels.fields["instance_group"].string_value
            elif type == "autoscaler":
                ig_name = result.resource.labels["instance_group_manager_name"]

            ig_value = result.points[0].value.double_value

            if ig_names == "": #Append all igs
                print("ig name : ",ig_name)
                print("ig value : ",ig_value)
                last_point_values.append(ig_value)
            else:
                if ig_name in ig_names: #Append only selected igs
                    print("ig name : ",ig_name)
                    print("ig value : ",ig_value)
                    last_point_values.append(ig_value)

        avg_value = sum(last_point_values)/len(last_point_values)
        print("AVG VALUE= ",avg_value)
        return float(avg_value)

    def write_time_series(self,metric_path,value:float):
        series = monitor.TimeSeries()
        series.metric.type = f"custom.googleapis.com/{metric_path}"
        series.resource.type = "global"
        series.metric.labels["AvgOfCPUUtilization"] = "Avg_Util[CPU]"
        now = time.time()
        seconds = int(now)
        nanos = int((now - seconds) * 10**9)
        interval = monitor.TimeInterval(
            {"end_time": {"seconds": seconds, "nanos": nanos}}
        )
        point = monitor.Point({"interval": interval, "value": {"double_value": value}})
        series.points = [point]
        self.client.create_time_series(name=self.project, time_series=[series])
        print("Write VALUE= ",value," to Metric ",f"custom.googleapis.com/{metric_path}")


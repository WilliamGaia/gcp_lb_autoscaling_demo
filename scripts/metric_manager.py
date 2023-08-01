import time
from google.cloud import monitoring_v3 as monitor
from .project_info import ProjectInfo

class MetricManager():
    def __init__(self,project_info: ProjectInfo):
        self.client = monitor.MetricServiceClient()
        self.project = f"projects/{project_info.project}"

    def read_time_series(self,metric_path,backends,interval_secs=480) -> float:
        now = time.time()
        seconds = int(now)
        nanos = int((now - seconds) * 10**9)
        interval = monitor.TimeInterval(
            {
                "end_time": {"seconds": seconds, "nanos": nanos},
                "start_time": {"seconds": (seconds - interval_secs), "nanos": nanos},
            }
        )
        results = self.client.list_time_series(
            request={
                "name": self.project,
                "filter": f'metric.type = "{metric_path}"',
                "interval": interval,
                "view": monitor.ListTimeSeriesRequest.TimeSeriesView.FULL,
            }
        )

        last_point_values = []
        if backends != "":
            backends = backends.split(",")
        for result in results:
            bk_name = result.resource.labels["backend_service_name"]
            bk_value = result.points[0].value.double_value
            if backends == "": #Append all backends
                print("bk name : ",bk_name)
                print("bk value : ",bk_value)
                last_point_values.append(bk_value)
            else:
                if bk_name in backends: #Append only selected backends
                    print("bk name : ",bk_name)
                    print("bk value : ",bk_value)
                    last_point_values.append(bk_value)

        avg_value = sum(last_point_values)/len(last_point_values)
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


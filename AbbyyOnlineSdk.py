#!/usr/bin/python

import shutil
import xml.dom.minidom

try:
    import requests
except ImportError:
    print("Run 'pip install requests' to fix it.")
    exit()


class ProcessingSettings:
    Language = "English"
    OutputFormat = "txt"


class Task:
    Status = "Unknown"
    Id = None
    DownloadUrl = None

    def is_active(self):
        return self.Status in ("InProgress", "Queued")


class AbbyyOnlineSdk:
    ServerUrl = "https://cloud-eu.ocrsdk.com/"
    ApplicationId = ""
    Password = ""
    Proxies = {}

    def process_image(self, file_path, settings):
        url_params = {
            "language": settings.Language,
            "exportFormat": settings.OutputFormat
        }
        request_url = self.get_request_url("processImage")
        with open(file_path, 'rb') as f:
            image_data = f.read()
        response = requests.post(
            request_url, data=image_data, params=url_params,
            auth=(self.ApplicationId, self.Password), proxies=self.Proxies
        )
        response.raise_for_status()
        return self.decode_response(response.text)

    def get_task_status(self, task):
        url_params = {"taskId": task.Id}
        response = requests.get(
            self.get_request_url("getTaskStatus"), params=url_params,
            auth=(self.ApplicationId, self.Password), proxies=self.Proxies
        )
        return self.decode_response(response.text)

    def download_result(self, task, output_path):
        if not task.DownloadUrl:
            return
        r = requests.get(task.DownloadUrl, stream=True, proxies=self.Proxies)
        with open(output_path, 'wb') as f:
            shutil.copyfileobj(r.raw, f)

    def download_result_text(self, task):
        """Download hasil langsung sebagai string (untuk format txt)."""
        if not task.DownloadUrl:
            return ""
        r = requests.get(task.DownloadUrl, proxies=self.Proxies)
        r.encoding = r.apparent_encoding or 'utf-8'
        return r.text

    def decode_response(self, xml_response):
        dom = xml.dom.minidom.parseString(xml_response)
        task_node = dom.getElementsByTagName("task")[0]
        task = Task()
        task.Id = task_node.getAttribute("id")
        task.Status = task_node.getAttribute("status")
        if task.Status == "Completed":
            task.DownloadUrl = task_node.getAttribute("resultUrl")
        return task

    def get_request_url(self, url):
        return self.ServerUrl.rstrip('/') + '/' + url.strip('/')

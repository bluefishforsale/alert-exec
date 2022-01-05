import json
import requests

class Client:
    def __init__(self, address):
        if address == "":
            address = "http://127.0.0.1:9001"
        self.address = address

    def query_alerts(self):
        url = self.address + "/alerts"
        response = requests.get(url)
        if response.status_code != 200:
            raise ConnectionError("could not complete request got " + str(response.status_code))
        return response.json()

    def notify(self, alertname, message):
        url = self.address + "/notify"
        request = {
            "alertName": alertname,
            "message": message
        }
        response = requests.post(url, json.dumps(request))
        if response.status_code != 200:
            raise ConnectionError("could not complete request got " + str(response.status_code))

    def resolve(self, alertname):
        url = self.address + "/resolve"
        request = {
            "alertName": alertname
        }
        response = requests.post(url, json.dumps(request))
        if response.status_code != 200:
            raise ConnectionError("could not complete request got " + str(response.status_code))

    def query(self, target):
        url = self.address + "/query?target=" + target
        response = requests.get(url)
        if response.status_code != 200:
            raise ConnectionError("could not complete request got " + str(response.status_code))
        return response.json()["value"]

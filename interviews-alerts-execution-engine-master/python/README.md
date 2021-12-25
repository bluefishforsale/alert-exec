# Python Client

The Python client uses the `requests` library, which can be insalled using `pip3 install requests`. 

A sample client is available here along with a snippet showing usage of the client. Start the server using
```
docker run -p 9001:9001 quay.io/chronosphereiotest/interview-alerts-engine:latest
```

The following snippet shows the operation of the different methods available on the client.
```
from client import Client

def main():
    client = Client("")

    # Retrieving alerts.
    alerts = client.query_alerts()
    print(alerts)

    # Querying a metric.
    resp = client.query("target")
    print(resp)

    # Triggering an alert.
    client.notify("test-alert", "test-message")

    # Resolving an alert.
    client.resolve("test-alert")

if __name__ == "__main__":
    main()
```

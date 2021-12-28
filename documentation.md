# Aert-Exec Submission Documentation

#### Requirements
* Python3 installed and in shells $PATH
* `client.py` library
* Running alerts_server at `localhost:9001`

```
docker run --name alerts_server -p 9001:9001 quay.io/chronosphereiotest/interview-alerts-engine:v2
```

## Startup and running
Displaying the help banner:
```./main.py -h``` 

#### Supported runtime parameters:
```
usage: main.py [-h] [-c CONCURRENCY] [-i INTERVAL] [-l LOG]

optional arguments:
  -h, --help            show this help message and exit
  -c CONCURRENCY, --concurrency CONCURRENCY
                        alerting concurrency
  -i INTERVAL, --interval INTERVAL
                        poll interval
  -l LOG, --log LOG     logging level eg. [critical, error, warn, warning, info, debug]
```


## Architecture
This script is a run-till-die effort. 

The concept is that of three message queues (python Queues) where worker threads pull Alert objects from them then wait for the next cycle

## Runtime operation:

* On startup connect to the metrics server
* Retrieve the list of alerts once and only once
* Convert the list of alerts to Alert objects, adding some attributes to help mange lifecycle
* Create {N} groups of workers of types [poll, notify, and resolve]
* Create {N} collections of worker for worker types [poll, notify, and resolve] where {N} is the level of concurrency requested at runtime
* divy up the alert items collected at start evenly between the {N} poll queues
* start {N} goups of the worker thread types

### Thread and Queue interaction

This operation flow is repeated horizontally {N} times in parallel

  ### Polling
  1. Poller thread is forever running
  1. Poller thread knows about three queues all sharing a numeric ID
  1. Thread iterates over the poll queue once, then waits
  1. Gets an Alert from global queues dict, key poll{N:03}
  1. Calls the alert server for a value for the Alert.query
  1. Adds the Alert ojbect to the Notification queue then skips to the next Alert object
  1. Adds a copy of the Alert ojbect to the the Resolve queue
  1. Adds current Alert object back to the end of the queue for the next cycle
  1. Repeats this loop sequentially for all items in the pollQ
  1. Then sleeps for the remainder of the INTERVAL cycle

  ### Notification
  1. Notifier is forever running
  1. Notifer knows of two queues (notifyQ), identified by it's numeric ID
  1. Thread iterates over the notification queue once, then waits
  1. Logic determines if this thread sends a message or waits. Using unix seconds + repeatInterval
  1. If logic allows, we call the notifications backend with the message. We also set the notification_sec attribute.
  1. If logic forbids, we wait out the clock
  1. the Alert object is added back to the notificaiton Q since it was updated in this thread
  1. Repeats this loop sequentially for all items in the pollQ
  1. Then sleeps for the remainder of the INTERVAL cycle  

  ### Resolver
  1. Resolver is forever running
  1. Resolver knows of one queue (resolveQ), identified by it's numeric ID
  1. Thread iterates over the resolve queue once, then waits
  1. Calls the resolve backend with the message
  1. Repeats this loop sequentially for all items in the resolveQ
  1. Then sleeps for the remainder of the INTERVAL cycle  




# Trade-offs
Globals: the concurrency mechanism chosen uses a global dictionary to hold the queues for each worker type. This makes the code less atomic and more inter-dependant. Creates a frustrating case for unit tests as the "secret sauce" must be  hand-written. 

Alert Class as dict with no methods: Kind of a sloppt abuse of a class here, but the alternative trade-off was a global dict, or list of dicts. The attribute reference of classes was a slightly nicer syntax and allows for easier testing.

Gathering the metrics list once and only once: This was not ideal, and I would have preferred something more fault tolerant. However due to the limitations of time I opted to aspiure for the minimum requirements.

Module level Logging not implemented. TBH I just could not get it working right. I opted for verbose instead of nothing. ideally I'd use a log handler, and streams so I could silence the requests module, or have that on it's own argument. 
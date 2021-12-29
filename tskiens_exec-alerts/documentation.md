# Aert-Exec Submission Documentation

#### Requirements
* Python3 installed and in shells $PATH
* `client.py` library
* Running alerts_server at `localhost:9001`

#### How to run alerts_server
```
docker run --name alerts_server -p 9001:9001 quay.io/chronosphereiotest/interview-alerts-engine:v2
```
#### Alternately `./start_server_container.sh`

## Startup and running
Displaying the help banner:
```./main.py -h``` 

#### Supported runtime parameters:
```
usage: alert-exec [-h] [-c CONCURRENCY] [-i INTERVAL] [-l LOG]

optional arguments:
  -h, --help            show this help message and exit
  -c CONCURRENCY, --concurrency CONCURRENCY
                        worker concurrency (default: 2)
  -i INTERVAL, --interval INTERVAL
                        internal operation interval (default: 1)
  -l LOG, --log LOG     logging level eg. [critical, error, warn, warning, info, debug] (default: info)
```

### Options details
The script can be run in a paralell mode. This divides up the alerts into fair'ish buckets for polling and notifying. Will not allow settings below 1, and above the length of the alerts list.

The script supports scraping intervals. Default value of 1, and safety clamps of 1sec and 3600sec limit.

Common Logging levels are supported. Debug will show all queue operations. Default is info. 

## Architecture
This script is a run-till-die affair.

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
  1. Respect intervalSecs in the item, and only poll if it's time
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
  1. Respect repeatInterval to determine if thread sends a message or waits. Using unix seconds + repeatInterval
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



# Trade-offs and Quirks
Globals: the concurrency mechanism chosen uses a global dictionary to hold the queues for each worker type. This makes the code less atomic and more inter-dependant. Creates a frustrating case for unit tests as the "secret sauce" must be  hand-written. 

Alert Class as dict with no methods: Kind of a sloppy abuse of a class here, but the alternative trade-off was a global dict (locking would have been annoying), or list of dicts (O(N) and locking). The attribute reference of classes was a slightly nicer syntax and allows for easier testing later on.

Gathering the metrics list once and only once: This was not ideal, and I would have preferred something more fault tolerant. However due to the limitations of time I opted to aspiure for the minimum requirements.

Module level Logging not implemented. TBH I just could not get it working right. I opted for verbose instead of nothing. ideally I'd use a log handler, and streams so I could silence the requests module, or have that on it's own argument. 

Fragile / Unavailable backends. The implementation tries to be tolerant of backends which are sporatically unavailable through the use of try/except blocks around those calls and logging of the messages. Should the inital alerts gather at start fail, then the script waits until that endpoint is able to provide the needed data.

There is very little sanitization and key checking of data returned from the client. Should the format change, this will undoubtedly break the script.

The metrics backend does seem to have some rate-limits in place. I have been able to take it offline through too many concurrent queries. I have noticed that it will resume operation after some time. This leads me to think the rate limit is implemented as a sliding window bucket. I have made not accomodation for this

Seen in my logging as:
```
2021-12-28 15:49:54,429 (./main.py:54) [ERROR] Worker poll003 failed to query for alert-3: could not complete request got 500
```

I tried to implement a spreading flow, dividing the (interval / alert number+1). In hopes this would alow for a smoother calling of the backend. Even with concurrency of 1 and interval of 4s, I still saw 500's from the metrics backend.  The happiest interval / concurrency achieved was 15s / 1 worker
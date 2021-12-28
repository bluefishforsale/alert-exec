# Aert-Exec Submission Documentation

#### Requirements
* Python3 installed and in shells $PATH


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
  1. Poll thread gets an Alert from global queues dict, key poll{N:03}
  1. Poll thread calls the alert server for a value for the Alert.query
  1. Poll thread adds the Alert ojbect to the Notification queue, or the Resolve queue
  1. Poll thread repeats this loop sequentially for all items in the pollQ
  1. Poll thread then sleeps for the remainder of the INTERVAL cycle

  ### Notification
  1. Notify thread 
  1. Notify thread 





# Trade-offs
Globals: the concurrency mechanism chosen uses a global dictionary to hold the queues for each worker type. This makes the code less atomic and more inter-dependant. Creates a frustrating case for unit tests as the "secret sauce" must be  hand-written. 

Alert Class as dict with no methods: Kind of a sloppt abuse of a class here, but the alternative trade-off was a global dict, or list of dicts. The attribute reference of classes was a slightly nicer syntax and allows for easier testing.

Gathering the metrics list once and only once: This was not ideal, and I would have preferred something more fault tolerant. However due to the limitations of time I opted to aspiure for the minimum requirements.
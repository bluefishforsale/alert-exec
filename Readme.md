# Alert-Exec Submission Documentation
Author terracnosaur@gmail.com

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
❯ ./main.py -h
usage: alert-exec [-h] [-c CONCURRENCY] [-i INTERVAL] [-r RETRY] [-l LOG]

optional arguments:
  -h, --help            show this help message and exit
  -c CONCURRENCY, --concurrency CONCURRENCY
                        worker concurrency (default: 2)
  -i INTERVAL, --interval INTERVAL
                        internal operation interval. max 15 (default: 1)
  -r RETRY, --retry RETRY
                        Failure retry count (default: 3)
  -l LOG, --log LOG     logging level eg. [critical, error, warn, warning, info, debug] (default: info)
```

### Options details
The script can be run in configurable paralellism modes. The default concurrency is two worker groups. Thr parallelism divides the alerts into fair'ish buckets for polling and notifying. It will not allow settings below 1, or beyond the length of the alerts list. The maximum concurrency is the number of alerts.

The script supports configurable internal timing interval. Default value of 1, and safety clamps of 1sec and 15s limit. This is for the internal timer operation. The polling of metrics from the metrics backend happens during a scrape interval allowed per item.

Also present is the retry argument. This overrides the internal default of 3 with any number between 1 and 10. Mostly for testing backend tolerance. I left it in for others to try.

Common Logging levels are supported. Debug will show extremely verbose output. Default is info. 

## Architecture
This script is a run-till-die affair. Ctrl-C to exit.

The concept is three FIFO queues. Where worker threads get Alert objects from them, evalute or act, then then wait for the next cycle. Items are often put back to the end of the group respective poll queue.

## Runtime operation:

* On startup connect to the metrics server
* Retrieve the list of alerts once and only once
* Convert the list of alerts to Alert objects, adding some attributes to help manage lifecycle
* Create {N} groups of workers of types [poll, notify, and resolve]
* Create {N} collections of worker for worker types [poll, notify, and resolve] where {N} is the level of concurrency requested at runtime
* divy up the alert items collected at start evenly between the {N} poll queues
* start {N} groups of the worker thread types

### Thread and Queue interaction

This operation flow is repeated horizontally {N} times in parallel

  ### Polling
  1. Poller thread is forever running
  1. Each poller thread knows about all three queues. Each sharing a numeric ID.
  1. Thread iterates over the poll queue once, then waits
  1. Gets an Alert from global queues dict, key poll{N:03}
  1. Respect intervalSecs in the item, and only poll if it's time
  1. Retry logic here
  1. Calls the alert server for a value for the Alert.query
  1. Adds the Alert ojbect to the Notification queue then skips to the next Alert object
  1. Adds a copy of the Alert object to the the Resolve queue
  1. Adds current Alert object back to the end of the queue for the next cycle
  1. Repeat this loop sequentially for all items in the pollQ
  1. Then sleeps for the remainder of the INTERVAL cycle

  ### Notification
  1. Notifier thread is forever running
  1. Each notifier thread knows of two queues (pollQ, notifyQ). Identified by their numeric ID's
  1. Thread iterates over the notification queue once, then waits
  1. Retry logic here
  1. Respect repeatInterval to determine if thread sends a message or waits. Using unix seconds + repeatInterval
  1. If logic allows, we call the notifications backend with the message. We also set the notification_sec attribute.
  1. If logic forbids, we wait out the clock
  1. the Alert object is added back to the notification Q since it was updated in this thread
  1. Repeat this loop sequentially for all items in the pollQ
  1. Then sleeps for the remainder of the INTERVAL cycle  

  ### Resolver
  1. Resolver thread is forever running
  1. Each resolver thread knows of one queue (resolveQ), identified by it's numeric ID
  1. Thread iterates over the resolve queue once, then waits
  1. Retry logic here
  1. Calls the resolve backend with the message
  1. Repeat this loop sequentially for all items in the resolveQ
  1. Then sleeps for the remainder of the INTERVAL cycle  


# Trade-offs and Quirks
Globals: the concurrency mechanism chosen uses a global dictionary to hold the queues for each worker type. This makes the code less atomic and more inter-dependant. Creates a frustrating case for unit tests as the "secret sauce" must be  hand-written. 

Alert Class as dict with no methods: Kind of a sloppy abuse of a class here, but the alternative trade-off was a global dict (locking would have been annoying), or list of dicts (O(N) and locking). The attribute reference of classes was a slightly nicer syntax and allows for easier testing later on.

Gathering the metrics list once and only once: This was not ideal, and I would have preferred something more fault tolerant. However due to the limitations of time I opted for the minimum requirements here.

Module level Logging not implemented. TBH I just could not get it working right. I opted for verbose instead of nothing. ideally I'd use a log handler, and streams so I could silence the requests module, or have that on it's own argument. 

There is very little sanitization and key checking of data returned from the client. Should the format change, this will undoubtedly break the script.

Poll worker function is more complex than I'd like. I opted for this approach  as it's self-contained. I thought about helper functions each for a simple analysis and return, but had bigger problems to worry about. I got it working and moved on. It's durable and well documented, so it will be easy to fix later.

# Backend limitations


The provided metrics backend `quay.io/chronosphereiotest/interview-alerts-engine:v2` returns 500 ISE occasionally. Through loadtesting it shows up ~1.2% of the time.
I have noticed that it will resume operation on the next query through. Very rarely are there repeated 500s.

Seen in my logging as:
```
2021-12-28 15:49:54,429 (./main.py:54) [ERROR] Worker poll003 failed to query for alert-3: could not complete request got 500
```

Confirmed with fortio load-testing.s
1.8% failures at the rate my script calls it.
```
docker run --rm -p 8088:8088 fortio/fortio load -c 2 -t 300s  'http://192.168.1.220:9001/query?target=test-query-10'

Fortio 1.20.0 running at 20 queries per second, 6->6 procs, for 5m0s: http://192.168.1.220:9001/query?target=test-query-10
18:11:02 I httprunner.go:81> Starting http test for http://192.168.1.220:9001/query?target=test-query-10 with 2 threads at 20.0 qps
Starting at 20 qps with 2 thread(s) [gomax 6] for 5m0s : 3000 calls each (total 6000)

Ended after 5m0.0040056s : 6000 calls. qps=20
Sleep times : count 5998 avg 0.093999007 +/- 0.003372 min 0.019000967 max 0.098345044 sum 563.806043
Aggregated Function Time : count 6000 avg 0.003876179 +/- 0.002669 min 0.0015637 max 0.0746449 sum 23.2570739

Code 200 : 5930 (98.8 %)
Code 500 : 70 (1.2 %)

```

#### Dealing with those limitations
Should the initial HTTP call to gather alerts fail; then the script waits until that endpoint is able to provide the needed data.

The implementation tries to be tolerant of backends which are sporatically unavailable through the use of try/except blocks around HTTP calls which could fail. Logging was used to spot this initially. Also for the poll / notify / resolve HTTP calls, a retry was implemented to ensure durability. It was noticed that if the first call failed, the second would succeed. A static retry count was used, but it could be made into an argument.

Time-spread call for polling. Dividing the (interval / alert count+1) `i_sleep`. In hopes this would allow for a smoother calling of the backend. A later tweak added the inclusion of the elapsed time so far in the worker. This allowed for more even distribution of calls, more concurrent polling workers, and fewer backend 500's

Opinionated `intervalSecs`. I saw that the body returned from the metrics server had an intervalSec field. I chose a different method than `repeatIntervalSecs`. Instead of capturing a timestamp and doing evaluation, I chose for this to modulo the current time with the items intervalSec then floor it. Knowing it would be some value between 0 and intervalSec. If the value is less than or eqal to the internal action interval, then we can poll it. 

The `INTERVAL` option is an internal resolution timer that actions occur on. A clockwork of sorts. It's used for polling and sleeping. All actions start at the next tick of the timer, in all worker threads. I had a variant where each poller thread slept `N` and that `N` was also used to evaluate if polling would occur. This  It's also used to spread out polling using the `i_sleep` variable

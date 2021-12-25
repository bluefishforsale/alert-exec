# Design notes
* Alerts will be picked up from the API and stored in memory
* Alerts have a sustain seconds which should be honored
* Sustain seconds means we need to record and evaluate last threshold pass timestamp
* If sustain seconds has elapsed (count down timer) and alert below threshold then reset state
* STATES = PASS <-> WARN <-> CRITICAL -> PASS
* we need to be parallel so start a thread pool with command line args, or maybe accept a rest request to change
* each alert has a structure of value, message where message is the level
* this feels more like two state machines in parallel: one where alerts are fetched from the API and loaded into memory
* and another where the in-memory state is evaluated for notification processing
* polling globally on a 1sec interval, and checking alert exec on 1sec interval
* 1s is the lowest we'll support, still this means we should timeout calls to the API
* game-loop style: budget-elapsed = sleep(remainder)

# {
#   'name': 'alert-1',
#   'query': 'test-query-1',
#   'intervalSecs': 15, 'repeatIntervalSecs': 100,
#   'sustainSecs': 0,
#   'warn': {'value': 100, 'message': 'warning'}, 
#   'critical': {'value': 200, 'message': 'critical'},
#   'state': 0,
#   'triggered_sec': 0
# }

* data stucture to store alerts in
* make this a class? might be too tricky
primary-key: name
- lastPolled: epochSeconds
- lastNotified: epochSeconds
- lastState: string
- warn: int
- crit: int

# flow
call api and get all initial data
populate memory data structure

make threadpool with two long running threads:
1. game loop threadpool for collectors
- collect all alerts in parallel
- update global data in parallel (gotta check this)
- sleep(budget-elapsed)
2. game loop alert checker thread pool
- start n concurrent threads, one for each alert
- evaluate each alert
- change state if needed
- send notification if needed
- sleep(budget-elapsed)


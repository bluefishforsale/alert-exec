# Requirements 
Alert Engine Basics 
The exercise requires you to develop an alert execution engine that executes alerts at the specified interval checks. Some engine basics: 

1. One alert execution cycle involves: 
  a. Making an API call to query the value of the metric 
  b. Comparing the return value against thresholds

  c. Determining the state of the alert 
  d. Make a notify API call if the alert is transitioning to WARN / CRITICAL state e. Make a resolve API call if the alert is transitioning to PASS state 

2. Alert can be in different states based on the current value of the query and the thresholds. 
  a. It is considered PASS if value <= warn threshold 
  b. It is considered WARN if value > warn threshold and value <= critical threshold c. It is considered CRITICAL if value > critical threshold 


# Functionality 
Functionality of the alert execution engine are described below 

1. Build an alert execution engine 
  a. Queries for alerts using the above API and execute them at the specified interval b. Alerts will not change over time, so only need to be loaded once at start 
  c. The basic alert engine will send notifications whenever it sees a value that exceeds the critical threshold. 
  d. The engine should have the ability to execute alerts in parallel with the amount of parallelization being configurable 

2. Introduce alert state transitions and repeat intervals 
  a. Incorporate using the the warn threshold in the alerting engine - now an alert can go between states PASS <-> WARN <-> CRITICAL <-> PASS 
  b. Add support for repeat intervals, so that if an alert is continuously firing in the same state it will only re-fire after the repeat interval 

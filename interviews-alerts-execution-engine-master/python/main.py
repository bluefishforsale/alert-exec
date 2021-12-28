#!env python3

from client import Client
from queue import Queue
from threading import Thread
from time import time, sleep
import logging
import sys
import argparse


def update_state(item, value, resolveQ):
  """ Compare the numeric value with the alert set-points """
  state = None
  triggered_sec = item.triggered_sec
  # PASS (less than or equal to warn thresh)
  if value <= item.warn['value']:
    state = 'PASS'
    triggered_sec = 0
  # WARNING (greater than warn thresh, less than or equal to critical)
  if value > item.warn['value']:
    state = item.warn['message']
  # CRITICAL (greater than critital)
  if value > item.critical['value']:
    state = item.critical['message']
  # here we catch the change back from non-pass to pass
  if item.state != state:
    if state == "PASS":
      # here is the resolve
      resolveQ.put(item)
  return (state, triggered_sec)


def poll(N):
  """ Worker 1/3 : collect update and compare. Put alert in notifyQ"""
  pollQ = queues[f"poll{N:03}"]
  notifyQ = queues[f"notify{N:03}"]
  resolveQ = queues[f"resolve{N:03}"]
  while True:
    start_time = time()
    for i in range(pollQ.qsize()):
      item = pollQ.get()
      # get numeric value from API
      try:
        resp = client.query(item.query)
        # trasnslate numeric to string, and update triggered_sec
        item.state, item.triggered_sec = update_state(item, resp, resolveQ)
        # if not pass, stick in notify queue
        if item.state != 'PASS':
          # Add the alert item to the notification queue
          # don't worry about re-triggers, thats what triggered_sec is for
          logging.debug(f"Worker poll{N:03} added {item.name} to notify{N:03}")
          notifyQ.put(item, resolveQ)
          continue
      except:
        pass
      # Add alert back to the end of the line
      pollQ.put(item)
    sleep(INTERVAL - (time() - start_time))
 


def notify(N):
  """ worker 2/3 : Send notifications. Manage cool-down timer """
  pollQ = queues[f"poll{N:03}"]
  notifyQ = queues[f"notify{N:03}"]
  while True:
    start_time = time()
    logging.debug(f"There are {notifyQ.qsize()} items in notify{N:03}")
    for i in range(notifyQ.qsize()):
      item = notifyQ.get()
      # First time, or re-trigger
      try:
        # values of 0, or repeatIntervalSecs seconds elapsed
        if item.triggered_sec + item.repeatIntervalSecs <= time():
          item.triggered_sec = time()
          logging.info(f"Worker notify{N:03} triggered {item.name} {item.state}")
          client.notify(item.name, item.state)
        # check if within repeatIntervalSecs window
        elif item.triggered_sec + item.repeatIntervalSecs >= time():
          pass
        # put back on pollQ with new values
      except:
        pass
      # back to the end of the line
      pollQ.put(item)
    sleep(INTERVAL - (time() - start_time))


def resolve(N):
  """ worker 3/3 : send resolution signals """
  resolveQ = queues[f"resolve{N:03}"]
  while True:
    start_time = time()
    logging.debug(f"There are {resolveQ.qsize()} items in resolve{N:03}")
    for i in range(resolveQ.qsize()):
      item = resolveQ.get()
      logging.info(f"Worker resolve{N:03} resolving for {item.name}")
      try:
        client.resolve(item.name)
      except:
        pass
    # wait out the duration
    sleep(INTERVAL - (time() - start_time))


# The alert object, dynamically instantiate all class properties from creation dict
class Alert(object):
  def __init__(self, data):
    # new k,v
    self.state = 'PASS'
    self.triggered_sec = 0
    # all passed in k,v
    for key in data:
      setattr(self, key, data[key])


def main(CONCURRENCY):
  # The idea is to put messages into queue
  # And a worker pool calls the functions
  # producing messages in other queues

  all_alerts = list()
  while len(all_alerts) == 0:
    try:
      all_alerts = client.query_alerts()
    except:
      pass

  logging.info(f"There are {len(all_alerts)} total alerts being watched")
  # sanity check on the concurrency
  if CONCURRENCY <= 0:
    CONCURRENCY = 1
  workers = [ 'poll', 'notify', 'resolve' ]
  
  # make the concurrent isolated  queues
  for N in range(0, CONCURRENCY):
    for worker in workers:
      logging.debug(f"creating Queue {worker}{N:03}")
      queues[f"{worker}{N:03}"] = Queue()
    # [ queues[f"{worker}{N:03}"] = Queue() for worker in workers ]

  # add alerts to each poll queue fairly
  for i in range(len(all_alerts)):
    for N in range(0, CONCURRENCY):
      if len(all_alerts) > 0:
        a = all_alerts.pop()
        logging.debug(f"adding {a['name']} to PollQ{N:03}")
        queues[f"poll{N:03}"].put(Alert(a))

  # start all the threads and pass their concurrency queue number
  for N in range(0, CONCURRENCY):
    for worker in workers:
      logging.debug(f"starting {worker}{N:03}")
      Thread(target=eval(worker), name=f"{worker}{N:03}", args=[N]).start() 


if __name__ == '__main__':


  parser = argparse.ArgumentParser(
    prog='alert-exec',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
  )
  parser.add_argument("-c", "--concurrency", help="worker concurrency",
                    type=int, default=1)
  parser.add_argument("-i", "--interval", help="poll interval",
                    type=int, default=1)
  parser.add_argument("-l", "--log", help="logging level eg. [critical, error, warn, warning, info, debug]",
                    type=str, default="info")
  args = parser.parse_args()

  levels = {
    'critical': logging.CRITICAL,
    'error': logging.ERROR,
    'warn': logging.WARNING,
    'warning': logging.WARNING,
    'info': logging.INFO,
    'debug': logging.DEBUG
  }

  level = levels.get(args.log.lower())
  logging.basicConfig(format='%(asctime)s %(message)s', level=level)

  INTERVAL = args.interval
  CONCURRENCY = args.concurrency

  queues = {}
  client = Client('')

  # helpfun runtime banner
  logging.info(f"Running Alert-Exec with {CONCURRENCY} workers on a {INTERVAL}s Timer")
  logging.info("Press Ctrl-C to exit")

  try:
    exit(main(CONCURRENCY))
  except KeyboardInterrupt:
    sys.exit('Ctrl-C pressed ...')

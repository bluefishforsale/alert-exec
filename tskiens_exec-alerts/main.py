#!env python3

from client import Client
from queue import Queue
from threading import Thread
from time import time, sleep
from math import floor
import logging
import sys
import argparse


class Alert(object):
  """ The alert object, dynamically instantiate all class properties from creation dict """
  def __init__(self, data):
    # new k,v
    self.state = 'PASS'
    self.triggered_sec = 0
    # all passed in k,v
    for key in data:
      setattr(self, key, data[key])


def zero_or_val(val):
  if val < 0:
    return 0
  else:
    return val


def val2state(item, value):
  """ Compare the numeric value with the alert set-points """
  state = None
  # PASS (less than or equal to warn thresh)
  if value <= item.warn['value']:
    state = 'PASS'
  # WARNING (greater than warn thresh, less than or equal to critical)
  if value > item.warn['value']:
    state = item.warn['message']
  # CRITICAL (greater than critital)
  if value > item.critical['value']:
    state = item.critical['message']
  return state


def poll(N):
  """ Worker 1/3 : collect update and compare. Put alert in notifyQ"""
  pollQ = queues[f"poll{N:03}"]
  notifyQ = queues[f"notify{N:03}"]
  resolveQ = queues[f"resolve{N:03}"]

  # run forever
  while True:
    start_time = time()
    i_sleep = (INTERVAL / (pollQ.qsize()+1))
    for i in range(pollQ.qsize()):
      # get item from queue
      item = pollQ.get()
      logging.debug(f"Worker poll{N:03} got {item.name} from pollQ{N:03}")

      # Check for intervalSecs
      # catch 0 or 1
      if not floor(time() % item.intervalSecs) <= 1:
        # back on the stack
        pollQ.put(item)
        # skip to next item
        continue

      # catch unavailable backends
      try:
        # get numeric value from API
        val = client.query(item.query)

      except Exception as err :
        logger.warn(f"Worker poll{N:03} failed to query for {item.name}: {err}")
        # add to back of line
        pollQ.put(item)
        sleep(zero_or_val(i_sleep - (time() - start_time)))
        # we skip to next Alert
        continue

      # trasnslate numeric to string, and update triggered_sec
      new_state = val2state(item, val)

      # if not pass, stick in notify queue
      if new_state != 'PASS':
        logger.debug(f"Worker poll{N:03} added {item.name} to notifyQ{N:03}")
        # update item state, reset timer
        if item.state != new_state:
          item.state = new_state
          item.triggered_sec == 0
        # Add the alert item to the notification queue
        # don't worry about re-triggers, thats what triggered_sec is for
        notifyQ.put(item)
        # do not put item on pollQ and skip to next item
        continue

      # here we catch the change back from non-pass to pass
      elif new_state == 'PASS':
        if item.state != new_state:
          # reset triggered sec
          item.triggered_sec = 0
          # set state to new
          item.state = new_state
          logger.debug(f"Worker poll{N:03} added {item.name} to resolveQ{N:03}")
          # put alert on resolve queue
          resolveQ.put(item)

      # Add alert back to the end of the line
      logger.debug(f"Worker poll{N:03} putting {item.name} back on pollQ{N:03}")
      pollQ.put(item)
    sleep(zero_or_val(INTERVAL - (time() - start_time)))


def notify(N):
  """ worker 2/3 : Send notifications. Manage cool-down timer """
  pollQ = queues[f"poll{N:03}"]
  notifyQ = queues[f"notify{N:03}"]

  # run forever
  while True:
    start_time = time()
    logger.debug(f"There are {notifyQ.qsize()} items in notify{N:03}")

    for i in range(notifyQ.qsize()):
      item = notifyQ.get()
      # First time, or re-trigger

      try:
        # values of 0, or repeatIntervalSecs seconds elapsed
        if item.triggered_sec + item.repeatIntervalSecs <= time():
          item.triggered_sec = time()
          logger.info(f"Worker notify{N:03} triggered {item.name} {item.state}")
          client.notify(item.name, item.state)
        # check if within repeatIntervalSecs window
        elif item.triggered_sec + item.repeatIntervalSecs >= time():
          pass
        # put back on pollQ with new values
      except:
        logger.warn(f"Worker notify{N:03} failed to get response from the backend. Will try again later.")

      # back to the end of the line
      pollQ.put(item)
    sleep(zero_or_val(INTERVAL - (time() - start_time)))


def resolve(N):
  """ worker 3/3 : send resolution signals """
  resolveQ = queues[f"resolve{N:03}"]

  # run forever
  while True:
    start_time = time()
    logger.debug(f"There are {resolveQ.qsize()} items in resolve{N:03}")

    for i in range(resolveQ.qsize()):
      item = resolveQ.get()
      logger.info(f"Worker resolve{N:03} resolving for {item.name}")
      try:
        client.resolve(item.name)
      except:
        logger.warn(f"Worker resolve{N:03} failed to get response from the backend. Will try again later.")
        pass

    # wait out the duration
    sleep(zero_or_val(INTERVAL - (time() - start_time)))


def main(INTERVAL, CONCURRENCY):
  """ Main function: gets all alerts, creates concurrency queues, and starts workers"""

  all_alerts = list()
  while len(all_alerts) == 0:
    try:
      all_alerts = client.query_alerts()
    except:
      logging.error("Could not contact metrics source. Sleeping 30s")
      sleep(30)

  logger.info(f"There are {len(all_alerts)} total alerts being watched")

  # sanity check on the interval
  if INTERVAL <= 0:
    INTERVAL = 1
  elif INTERVAL > 3600:
    INTERVAL = 3600
  # sanity check on the concurrency
  if CONCURRENCY <= 0:
    CONCURRENCY = 1
  elif CONCURRENCY >= len(all_alerts):
    CONCURRENCY = len(all_alerts)

  # helpfun runtime banner
  logger.info(f"Running Alert-Exec with {CONCURRENCY} workers on a {INTERVAL}s Timer")
  logger.info("Press Ctrl-C to exit")

  # types of workers and queues
  workers = [ 'poll', 'notify', 'resolve' ]
  
  # make the concurrent isolated  queues
  for N in range(0, CONCURRENCY):
    for worker in workers:
      logger.debug(f"creating Queue {worker}{N:03}")
      queues[f"{worker}{N:03}"] = Queue()
    # [ queues[f"{worker}{N:03}"] = Queue() for worker in workers ]

  # add alerts to each poll queue fairly
  for i in range(len(all_alerts)):
    for N in range(0, CONCURRENCY):
      if len(all_alerts) > 0:
        a = all_alerts.pop()
        logger.debug(f"PollQ{N:03} adding {a}")
        queues[f"poll{N:03}"].put(Alert(a))

  # start all the threads and pass their concurrency queue number
  for N in range(0, CONCURRENCY):
    for worker in workers:
      logger.debug(f"starting {worker}{N:03}")
      Thread(target=eval(worker), name=f"{worker}{N:03}", args=[N]).start() 


if __name__ == '__main__':
  """ Called directly or imported? """
  parser = argparse.ArgumentParser(
    prog='alert-exec',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
  )
  parser.add_argument("-c", "--concurrency", help="worker concurrency",
                    type=int, default=1)
  parser.add_argument("-i", "--interval", help="internal operation interval",
                    type=int, default=2)
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
  
  # logging setup
  format = '%(asctime)-30s %(levelname)-8s %(pathname)s:%(lineno)-21d %(message)s'
  logger = logging.getLogger(__name__)
  logging.basicConfig(format=format, level=level)

  # interval limits
  INTERVAL = args.interval
  CONCURRENCY = args.concurrency

  # required globals
  queues = {}
  client = Client('')

  try:
    exit(main(INTERVAL, CONCURRENCY))
  except KeyboardInterrupt:
    sys.exit('Ctrl-C pressed ...')
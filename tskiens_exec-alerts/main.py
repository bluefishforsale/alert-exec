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
  """ Returns any positive value, or zero if negative """
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
  """ Worker 1/3 : collect update and compare. Put alert in notifyQ
      This is a long, complex function. Apologies in advance. 
      The reason for the lengh is many-fold. 
      First there is the nuance of the intervalSecs, we only poll if it's our time
      Next is the retry behavior of the poller, as the backend sometimes fails.
      Additionally, the complex logic of state transitions is here.
      An attempt was made.
  """
  pollQ = queues[f"poll{N:03}"]
  notifyQ = queues[f"notify{N:03}"]
  resolveQ = queues[f"resolve{N:03}"]

  # run forever
  while True:
    start_time = time()
    i_sleep = (INTERVAL / (pollQ.qsize()))
    for i in range(pollQ.qsize()):
      # get item from queue
      item = pollQ.get()

      # Check for intervalSecs, skip to next early if not our time
      if not floor(time() % item.intervalSecs) <= INTERVAL:
        # back on the stack
        pollQ.put(item)
        # skip to next item
        continue

      # catch unavailable backends
      # we give ourselves a few tries
      val = False
      for attempt in range(3):
        if not val:
          # get numeric value from API
          logger.debug(f"Worker poll{N:03} query attempt #{attempt} for {item.query}")
          # make the external call, this fails sometimes
          try:
            val = client.query(item.query)
          except Exception as err:
            logger.warning(f"Worker poll{N:03} failed query attempt #{attempt} for {item.name}: {err}")
            # slow down the retry just a little
            sleep(zero_or_val(i_sleep) / 3)

      # all attempts exhausted, skip to next 
      if not val:
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
        notifyQ.put(item)
        # do not put item on pollQ and skip to next item
        continue

      # catch the change back from non-pass to pass
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

    for i in range(notifyQ.qsize()):
      item = notifyQ.get()

      OK = False
      # First time, or re-trigger
      # values of 0, or repeatIntervalSecs seconds elapsed
      if item.triggered_sec + item.repeatIntervalSecs < floor(time()):
        item.triggered_sec = floor(time())
        for attempt in range(3):

          if not OK:
            try:
              logger.info(f"Worker notify{N:03} triggered {item.name} {item.state}")
              client.notify(item.name, item.state)
              OK = True

            # Problem, tell somebody
            except Exception as err:
              logger.warning(f"Worker notify{N:03} failed attempt #{attempt} for {item.name}: {err}")
              continue

      # within repeatIntervalSecs window, log if debug
      elif item.triggered_sec + item.repeatIntervalSecs >= floor(time()):
        logger.debug(f"Worker notify{N:03} waiting {item.name} {item.state}")

      # put back on pollQ with new values
      pollQ.put(item)
    sleep(zero_or_val(INTERVAL - (time() - start_time)))


def resolve(N):
  """ worker 3/3 : send resolution signals """
  resolveQ = queues[f"resolve{N:03}"]

  # run forever
  while True:
    start_time = time()

    for i in range(resolveQ.qsize()):
      item = resolveQ.get()
      OK = False
      # retry loop
      for attempt in range(3):
        # Skip if we've had a success
        if not OK:
          try:
            logger.info(f"Worker resolve{N:03} resolving attempt #{attempt} for {item.name}")
            client.resolve(item.name)
            OK = True
          except:
            logger.warning(f"Worker resolve{N:03} failed attempt #{attempt} for {item.name}: {err}")

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
  elif INTERVAL > 15:
    INTERVAL = 15
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
      # logger.debug(f"creating Queue {worker}{N:03}")
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
      # logger.debug(f"starting {worker}{N:03}")
      Thread(target=eval(worker), name=f"{worker}{N:03}", args=[N]).start() 


if __name__ == '__main__':
  """ Called directly or imported? """
  parser = argparse.ArgumentParser(
    prog='alert-exec',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
  )
  parser.add_argument("-c", "--concurrency", help="worker concurrency",
                    type=int, default=2)
  parser.add_argument("-i", "--interval", help="internal operation interval. max 15",
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

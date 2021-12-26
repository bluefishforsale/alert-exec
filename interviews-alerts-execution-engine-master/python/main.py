#!env python3

from client import Client
from math import floor
from queue import Queue
from threading import Thread
from time import time, sleep
import signal
import sys


def now():
  return time()


def update_state(item, value):
  state = None
  # PASS (less than or equal to warn thresh)
  if value <= item.warn['value']:
    state = 'PASS'
    item.triggered_sec = 0
  # WARNING (greater than warn thresh, less than or equal to critical)
  if value > item.warn['value']:
    state = item.warn['message']
  # CRITICAL (greater than critital)
  if value > item.critical['value']:
    state = item.critical['message']
  # here we catch the change back from non pass to pass
  if item.state != state:
    if state == "PASS":
      print('resolving {}'.format(item.name))
      resolveQ.put(item)
  item.state = state
  return item


def poll():
  """ Worker 1/3 : collect update and compare. Put alert in notifyQ"""
  while True:
    start_time = now()
    # print('there are {} items in {} queue'.format( pollQ.qsize(), 'poll' ))
    for i in range(pollQ.qsize()):
      item = pollQ.get()
      # get numeric value from API
      try:
        resp = client.query(item.query)
      except:
        break
      # trasnslate numeric to string, store in state
      item = update_state(item, resp)
      # if not pass, stick in notify queue
      if item.state != 'PASS':
        # print("Adding {} {} {}".format(item.name, item.state, resp) )
        notifyQ.put(item)
        continue
      # back to the end of the line
      pollQ.put(item)
    sleep(INTERVAL - (now() - start_time))
 


def notify():
  """ worker 2/3 : Send notifications. Manage cool-down timer """
  while True:
    start_time = now()
    # print('There are {} items in {} queue'.format( notifyQ.qsize(), 'notify' ))
    for i in range(notifyQ.qsize()):
      item = notifyQ.get()
      # First time, or re-trigger
      if item.triggered_sec <= 0:
        item.triggered_sec = item.repeatIntervalSecs
        print('triggered {} {} {}'.format(item.name, item.state, item.triggered_sec) )
        try:
          client.notify(item.name, item.state)
        except:
          pass
      # decrement trigger_sec untl we hit zero
      elif item.triggered_sec > 0:
        # print('waiting out {} {} {}'.format(item.name, item.state, item.triggered_sec) )
        item.triggered_sec -= INTERVAL
      # put back on pollQ with new values
      pollQ.put(item)
    sleep(INTERVAL - (now() - start_time))


def resolve():
  """ worker 3/3 : send resolution signals """
  while True:
    start_time = now()
    # print('there are {} items in {} queue'.format( resolveQ._qsize(), 'resolve' ))
    for i in range(resolveQ._qsize()):
      item = resolveQ.get()
      print('resolving {}'.format(item.name))
      try:
        client.resolve(item.name)
      except:
        pass
    # wait out the duration
    sleep(INTERVAL - (now() - start_time))


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
  while pollQ.empty():
    try:
      [ pollQ.put(Alert(a)) for a in client.query_alerts() ]
    except:
      pass
  # sanity check on the concurrency
  if CONCURRENCY >= pollQ.qsize():
    # upper clamp to queue size
    CONCURRENCY = pollQ.qize()
  elif CONCURRENCY <= 0:
    CONCURRENCY = 1
  for N in range(1, CONCURRENCY):
    for worker in [ 'poll', 'notify', 'resolve' ]:
      # start all the threads
      Thread(target=eval(worker), name="%s%03d".format(worker, N), kwargs={}).start() 


if __name__ == '__main__':

  INTERVAL = 1
  CONCURRENCY = 4

  client = Client('')
  pollQ = Queue()
  notifyQ = Queue()
  resolveQ = Queue()

  try:
    main(CONCURRENCY)
  except KeyboardInterrupt:
    sys.exit('Ctrl-C pressed ...')

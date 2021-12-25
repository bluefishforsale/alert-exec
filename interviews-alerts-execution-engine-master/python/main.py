from client import Client
from math import floor
from queue import Queue
from threading import Thread
from time import time, sleep
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
    state = item.warn['message'].upper()
  # CRITICAL (greater than critital)
  if value > item.critical['value']:
    state = item.critical['message'].upper()
  # here we catch the change back from non pass to pass
  if item.state != state:
    if state == "PASS":
      print('resolving {}'.format(item.name))
      resolveQ.put(item)
  item.state = state
  return item


#  worker 1/3 : collect and compare
def poll(interval):
  while True:
    start_time = now()
    # print('there are {} items in {} queue'.format( pollQ._qsize(), 'poll' ))
    for i in range(pollQ._qsize()):
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
        print("Adding {} in notifiation queue".format(item.name, item.state, resp) )
        notifyQ.put(item)
        continue
      # back to the end of the line
      pollQ.put(item)
    sleep(interval - (now() - start_time))
 


# worker 2/3 : raise notifications
def notify(interval):
  while True:
    start_time = now()
    print('There are {} items in {} queue'.format( notifyQ._qsize(), 'notify' ))
    for i in range(notifyQ._qsize()):
      item = notifyQ.get()
      # we can re-trigger alert
      if item.triggered_sec == 0:
        item.triggered_sec = item.repeatIntervalSecs
        print('triggered {} {} {}'.format(item.name, item.state, item.triggered_sec) )
        try:
          client.notify(item.name, item.state)
        except:
          pass
      # decrement trigger_sec untl we hit zero
      if item.triggered_sec > 0:
        print('waiting out {} {} {}'.format(item.name, item.state, item.triggered_sec) )
        item.triggered_sec -= interval
      # put back on pollQ with new values
      pollQ.put(item)
    sleep(interval - (now() - start_time))


# worker 3/3 : resolver
def resolve(interval):
  while True:
    start_time = now()
    print('there are {} items in {} queue'.format( resolveQ._qsize(), 'resolve' ))
    for i in range(resolveQ._qsize()):
      item = resolveQ.get()
      print('resolving {}'.format(item.name))
      try:
        client.resolve(item.name)
      except:
        pass
    # wait out the duration
    sleep(interval - (now() - start_time))


# The alert object, dynamically instantiate all class properties from creation dict
class Alert(object):
  def __init__(self, data):
    # new k,v
    self.state = 'PASS'
    self.triggered_sec = 0
    # all passed in k,v
    for key in data:
      setattr(self, key, data[key])


def main():
  # The idea is to put messages into queue
  # And a worker pool calls the functions
  # producing messages in other queues
  while pollQ.empty():
    try:
      [ pollQ.put(Alert(a)) for a in client.query_alerts() ]
    except:
      pass
  # start all the threads
  [ Thread(target=eval(worker), kwargs={'interval': INTERVAL}).start() for worker in [ 'poll', 'notify', 'resolve' ]]


if __name__ == '__main__':
  INTERVAL = 10
  client = Client('')
  pollQ = Queue()
  notifyQ = Queue()
  resolveQ = Queue()

  try:
    main()
  except KeyboardInterrupt:
    sys.exit('Exiting...')

from client import Client

class Alert(object):
  def __init__(self, data):
    # new k,v
    self.state = None
    self.triggered_time = None
    # all passed in k,v
    for key in data:
      setattr(self, key, data[key])


client = Client("")
alerts = [ Alert(A) for A in client.query_alerts() ]

for i in alerts:
  print(vars(i))
  i.state = False
  print(vars(i))
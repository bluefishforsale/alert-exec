# Java Client

This is a sample Java client to access the alerts API. To test the client start the server using
```
docker run -p 9001:9001 quay.io/chronosphereiotest/interview-alerts-engine:latest
```

The code in Example.java shows how to exercise the client. You can run the example using `make example`. Run `make clean` to remove build files.
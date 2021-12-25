# Go Client

This implements a simple Go client for the alert execution engine interview. You can test the client using the code
snippet below. First start up the alerts server using
```
docker run -p 9001:9001 quay.io/chronosphereiotest/interview-alerts-engine:latest
```

The following code snippet also available in `main.go` shows how you can use the client.
```
package main

import (
	"context"
	"fmt"

	"github.com/chronosphereio/interviews-alerts-execution-engine/golang/src/alerts"
)

func main() {
	client := alerts.NewClient("")

	alerts, err := client.QueryAlerts(context.Background())
	if err != nil {
		fmt.Printf("error querying alerts: %+v\n", err)
	} else {
		for _, alert := range alerts {
			fmt.Printf("%v\n", alert)
		}
	}

	value, err := client.Query(context.Background(), "target")
	if err != nil {
		fmt.Printf("error resolving: %v\n", err)
	} else {
		fmt.Printf("value queried: %v\n", value)
	}

	err = client.Notify(context.Background(), "test-alert", "test-message")
	if err != nil {
		fmt.Printf("error notifying: %v\n", err)
	}

	err = client.Resolve(context.Background(), "test-alert")
	if err != nil {
		fmt.Printf("error resolving: %v\n", err)
	}
}
```

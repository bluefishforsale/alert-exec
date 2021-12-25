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

	value, err := client.Query(context.Background(), "test-query-1")
	if err != nil {
		fmt.Printf("error resolving: %v\n", err)
	} else {
		fmt.Printf("value queried: %v\n", value)
	}

	err = client.Notify(context.Background(), "alert-1", "test-message")
	if err != nil {
		fmt.Printf("error notifying: %v\n", err)
	}

	err = client.Resolve(context.Background(), "alert-1")
	if err != nil {
		fmt.Printf("error resolving: %v\n", err)
	}
}

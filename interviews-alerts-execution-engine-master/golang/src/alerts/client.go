package alerts

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"net/url"
)

const (
	defaultAddress = "http://127.0.0.1:9001"

	alertsURI  = "/alerts"
	notifyURI  = "/notify"
	resolveURI = "/resolve"
	queryURI   = "/query"
)

type queryResponse struct {
	Value float32 `json:"value"`
}

type notifyRequest struct {
	AlertName string `json:"alertName"`
	Message   string `json:"message"`
}

type resolveRequest struct {
	AlertName string `json:"alertName"`
}

// Alert is the alert structure.
type Alert struct {
	Name               string    `json:"name"`
	Query              string    `json:"query"`
	IntervalSecs       int       `json:"intervalSecs"`
	RepeatIntervalSecs int       `json:"repeatIntervalSecs"`
	Warn               Threshold `json:"warn"`
	Critical           Threshold `json:"critical"`
}

// Threshold is the structure for a particular threshold.
type Threshold struct {
	Value   float32 `json:"value"`
	Message string  `json:"message"`
}

// Client is the alerts client interface.
type Client interface {
	QueryAlerts(ctx context.Context) ([]*Alert, error)
	Query(ctx context.Context, target string) (float32, error)
	Notify(ctx context.Context, alertname, message string) error
	Resolve(ctx context.Context, alertname string) error
}

type client struct {
	address string
	client  *http.Client
}

// NewClient returns a new alerts client.
func NewClient(address string) Client {
	if len(address) == 0 {
		address = defaultAddress
	}
	return &client{
		address: address,
		client:  http.DefaultClient,
	}
}

func (c *client) QueryAlerts(ctx context.Context) ([]*Alert, error) {
	url := c.address + alertsURI
	req, err := http.NewRequest("GET", url, nil)
	req = req.WithContext(ctx)

	resp, err := c.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("error querying alerts: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("error querying alerts: %s", resp.Status)
	}

	data, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("error reading alerts response: %w", err)
	}

	var alertsResponse []*Alert
	if err := json.Unmarshal(data, &alertsResponse); err != nil {
		return nil, fmt.Errorf("error unmarshalling alerts response: %w", err)
	}
	return alertsResponse, nil
}

func (c *client) Notify(ctx context.Context, alertname, message string) error {
	url := c.address + notifyURI
	return c.post(ctx, url, notifyRequest{
		AlertName: alertname,
		Message:   message,
	})
}

func (c *client) Resolve(ctx context.Context, alertname string) error {
	url := c.address + resolveURI
	return c.post(ctx, url, resolveRequest{
		AlertName: alertname,
	})
}

func (c *client) Query(ctx context.Context, target string) (float32, error) {
	url := c.address + queryURI + "?target=" + url.QueryEscape(target)
	req, err := http.NewRequest("GET", url, nil)
	req = req.WithContext(ctx)

	resp, err := c.client.Do(req)
	if err != nil {
		return 0, fmt.Errorf("target eval error: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return 0, fmt.Errorf("target eval status error: %s", resp.Status)
	}

	data, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return 0, fmt.Errorf("target eval read error: %w", err)
	}

	var response queryResponse
	if err := json.Unmarshal(data, &response); err != nil {
		return 0, fmt.Errorf("target eval parse error: %s: %w", string(data), err)
	}
	return response.Value, nil
}

func (c *client) post(ctx context.Context, url string, arg interface{}) error {
	body, err := json.Marshal(arg)
	if err != nil {
		return fmt.Errorf("error marshalling payload: %w", err)
	}

	req, err := http.NewRequest("POST", url, bytes.NewBuffer(body))
	if err != nil {
		return fmt.Errorf("error creating post request: %w", err)
	}
	req = req.WithContext(ctx)

	req.Header.Add("Content-Type", "application/json")
	resp, err := c.client.Do(req)
	if err != nil {
		return fmt.Errorf("error making post request: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("post status: %v", resp.Status)
	}
	return nil
}

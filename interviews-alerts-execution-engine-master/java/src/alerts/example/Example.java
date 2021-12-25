package alerts.example;

import alerts.clients.*;

import java.util.List;

public class Example {
    public static void main(String[] args) {
        Client client = new Client();

        try {
            double value = client.query("test-query-1");
            System.out.println("Value: " + value);

            List<Alert> alerts = client.getAlerts();
            System.out.println("List of alerts:");
            for (Alert alert: alerts) {
                System.out.println(alert.toString());
            }

            client.notify("alert-1", "warning message");

            client.resolve("alert-1");
        } catch (Exception e) {
            System.err.println("Exception: " + e.getMessage());
        }
    }
}

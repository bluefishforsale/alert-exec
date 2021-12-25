package alerts.clients;

import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import org.json.simple.*;
import org.json.simple.parser.*;

public class Client {
    public static String BASE_URL = "http://127.0.0.1:9001/";
    private static Integer HTTP_OK_STATUS_CODE = 200;

    public Client() {}

    public List<Alert> getAlerts() throws Exception {
        HttpURLConnection conn = null;
        try {
            StringBuilder result = new StringBuilder();
            URL url = new URL(BASE_URL + "alerts");
            conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(conn.getInputStream()))) {
                for (String line; (line = reader.readLine()) != null; ) {
                    result.append(line);
                }
            }
            JSONParser parser = new JSONParser();
            Object obj = parser.parse(result.toString());
            JSONArray array = (JSONArray) obj;
            List<Alert> alerts = new ArrayList<>();
            for (int i = 0; i < array.size(); i++) {
                JSONObject jsonObj = (JSONObject) array.get(i);
                String name = (String) jsonObj.get("name");
                String query = (String) jsonObj.get("query");
                long intervalSeconds = (Long) jsonObj.get("intervalSecs");
                long repeatIntervalSeconds = (Long) jsonObj.get("repeatIntervalSecs");
                long sustainIntervalSeconds = (Long) jsonObj.get("sustainSecs");
                JSONObject warn = (JSONObject) jsonObj.get("warn");
                JSONObject critical = (JSONObject) jsonObj.get("critical");
                Alert alert = new Alert(
                        name,
                        query,
                        intervalSeconds,
                        repeatIntervalSeconds,
                        sustainIntervalSeconds,
                        new Threshold(
                                (Long) warn.get("value"),
                                (String) warn.get("message")),
                        new Threshold(
                                (Long) critical.get("value"),
                                (String) critical.get("message")));
                alerts.add(alert);
            }
            return alerts;
        } finally {
            if (conn != null) {
                conn.disconnect();
            }
        }
    }

    public double query(String query) throws Exception {
        HttpURLConnection conn = null;
        try {
            StringBuilder result = new StringBuilder();
            URL url = new URL(BASE_URL + "query?target=" + query);
            conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(conn.getInputStream()))) {
                for (String line; (line = reader.readLine()) != null; ) {
                    result.append(line);
                }
            }
            JSONParser parser = new JSONParser();
            Object obj = parser.parse(result.toString());
            JSONObject jsonObj = (JSONObject) obj;
            return (Double)jsonObj.get("value");
        } finally {
            if (conn != null) {
                conn.disconnect();
            }
        }
    }

    public boolean notify(String alertName, String message) throws IOException {
        HttpURLConnection conn = null;
        try {
            JSONObject obj = new JSONObject();
            obj.put("alertName", alertName);
            obj.put("message", message);
            byte[] out = obj.toJSONString().getBytes(StandardCharsets.UTF_8);

            URL url = new URL(BASE_URL + "notify");
            conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");

            conn.setDoOutput(true);
            conn.getOutputStream().write(out);
            if (conn.getResponseCode() == HTTP_OK_STATUS_CODE) {
                return true;
            }
            System.err.println(conn.getResponseMessage());
            return false;
        } finally {
            if (conn != null) {
                conn.disconnect();
            }
        }
    }

    public boolean resolve(String alertName) throws IOException {
        HttpURLConnection conn = null;
        try {
            JSONObject obj = new JSONObject();
            obj.put("alertName", alertName);
            byte[] out = obj.toJSONString().getBytes(StandardCharsets.UTF_8);

            URL url = new URL(BASE_URL + "resolve");
            conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");

            conn.setDoOutput(true);
            conn.getOutputStream().write(out);
            if (conn.getResponseCode() == HTTP_OK_STATUS_CODE) {
                return true;
            }
            System.err.println(conn.getResponseMessage());
            return false;
        } finally {
            if (conn != null) {
                conn.disconnect();
            }
        }
    }
}

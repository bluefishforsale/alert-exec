package alerts.clients;

public class Alert {
    public final String name;
    public final String query;
    public final long intervalSeconds;
    public final long repeatIntervalSeconds;
    public final Threshold warnThreshold;
    public final Threshold criticalThreshold;

    public Alert(
            String name,
            String query,
            long intervalSeconds,
            long repeatIntervalSeconds,
            long sustainSeconds,
            Threshold warnThreshold,
            Threshold criticalThreshold) {
        this.name = name;
        this.query = query;
        this.intervalSeconds = intervalSeconds;
        this.repeatIntervalSeconds = repeatIntervalSeconds;
        this.warnThreshold = warnThreshold;
        this.criticalThreshold = criticalThreshold;
    }

    @Override
    public String toString() {
        return "{" +
                "name='" + name + '\'' +
                ", query='" + query + '\'' +
                ", intervalSeconds=" + intervalSeconds +
                ", repeatIntervalSeconds=" + repeatIntervalSeconds +
                ", warnThreshold=" + warnThreshold.toString() +
                ", criticalThreshold=" + criticalThreshold.toString() +
                '}';
    }
}


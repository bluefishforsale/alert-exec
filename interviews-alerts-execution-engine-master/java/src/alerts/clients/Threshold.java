package alerts.clients;

public class Threshold {
    public final double value;
    public final String message;

    public Threshold(double value, String message) {
        this.value = value;
        this.message = message;
    }

    @Override
    public String toString() {
        return "{" +
                "value=" + value +
                ", message='" + message + '\'' +
                '}';
    }
}

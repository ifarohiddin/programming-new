from flask import Flask, jsonify
from config import TASK_QUEUES

app = Flask(__name__)

@app.route("/metrics", methods=["GET"])
def get_metrics():
    # Dummy metrikalar (haqiqiy RabbitMQ API orqali olish kerak)
    metrics = {
        "queues": {q: {"length": 0} for q in TASK_QUEUES},
        "workers": 2,
        "processed_per_second": 0
    }
    return jsonify(metrics)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

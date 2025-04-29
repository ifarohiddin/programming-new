Distributed Task Processing System
Setup

Install Docker and Docker Compose.
Run docker-compose up to start RabbitMQ, producer, and workers.
Access RabbitMQ management UI at http://localhost:15672 (guest/guest).

Usage
from src.client import TaskClient
client = TaskClient()
task_id = client.submit_task("image_processing", "resize", {"image": "sample.jpg"}, priority=8)
metrics = client.get_metrics()

Tests
Run pytest tests/ to execute unit and stress tests.


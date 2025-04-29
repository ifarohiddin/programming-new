import pika
import json
import zlib
from config import (
    RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASS, 
    EXCHANGE_NAME, TASK_QUEUES, DEAD_LETTER_QUEUE
)

class TaskClient:
    def __init__(self):
        self.credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        self.connection_params = pika.ConnectionParameters(
            host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=self.credentials
        )
        self.connect()

    def connect(self):
        self.connection = pika.BlockingConnection(self.connection_params)
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="direct")
        self.channel.confirm_delivery()

    def submit_task(self, queue, task_type, payload, priority=5):
        if not self.connection or self.connection.is_closed:
            self.connect()
        task = {"task_id": str(uuid.uuid4()), "type": task_type, "payload": payload, "priority": priority, "retry_count": 0}
        message = json.dumps(task)
        compressed = zlib.compress(message.encode())
        self.channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=queue,
            body=compressed,
            properties=pika.BasicProperties(delivery_mode=2, priority=priority)
        )
        return task["task_id"]

    def start_worker(self, queue, callback):
        worker = Worker(queue, callback)
        worker.start()

    def retry_task(self, task_id):
        # O‘lik xabarlar navbatidan vazifani qayta ishlash
        # Bu misolda soddalashtirilgan
        print(f"Retrying task {task_id} (manual implementation required)")
        return True

    def get_metrics(self):
        # RabbitMQ boshqaruv API orqali metrikalarni olish mumkin
        return {
            "queues": {q: {"length": 0} for q in TASK_QUEUES},
            "workers": 2,  # Dinamik ishchilar soni
            "processed_per_second": 0  # Haqiqiy hisoblash kerak
        }

    def close(self):
        if self.connection and not self.connection.is_closed:
            self.connection.close()

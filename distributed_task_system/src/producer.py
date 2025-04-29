import pika
import json
import uuid
import zlib
from config import RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASS, EXCHANGE_NAME, TASK_QUEUES, DEAD_LETTER_EXCHANGE

class Producer:
    def __init__(self):
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials)
        )
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="direct")
        self.channel.exchange_declare(exchange=DEAD_LETTER_EXCHANGE, exchange_type="fanout")
        self.channel.confirm_delivery()  # Nashriyotchi tasdiqlari

        # Navbatlarni sozlash
        for queue, config in TASK_QUEUES.items():
            args = {
                "x-max-priority": config["max_priority"],
                "x-dead-letter-exchange": DEAD_LETTER_EXCHANGE  # O‘lik xabarlar almashuvi
            } if config["priority"] else {"x-dead-letter-exchange": DEAD_LETTER_EXCHANGE}
            try:
                self.channel.queue_declare(queue=queue, durable=True, arguments=args)
                self.channel.queue_bind(queue=queue, exchange=EXCHANGE_NAME, routing_key=queue)
            except pika.exceptions.ChannelClosedByBroker as e:
                print(f"Queue {queue} already exists with different args: {e}. Continuing...")
                self.channel = self.connection.channel()  # Kanalni qayta ochish
                self.channel.confirm_delivery()

    def submit_task(self, queue, task_type, payload, priority=5):
        task = {
            "task_id": str(uuid.uuid4()),
            "type": task_type,
            "payload": payload,
            "priority": priority,
            "retry_count": 0
        }
        message = json.dumps(task)
        compressed_message = zlib.compress(message.encode())  # Siqish
        try:
            self.channel.basic_publish(
                exchange=EXCHANGE_NAME,
                routing_key=queue,
                body=compressed_message,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Doimiy xabar
                    priority=priority
                )
            )
            print(f"Task {task['task_id']} sent to {queue}")
        except Exception as e:
            print(f"Failed to send task: {e}")
            raise

    def close(self):
        self.connection.close()

if __name__ == "__main__":
    producer = Producer()
    producer.submit_task("image_processing", "resize", {"image": "sample.jpg"}, priority=8)
    producer.close()
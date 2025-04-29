import pika
import json
import zlib
import time
from config import (
    RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASS, 
    EXCHANGE_NAME, TASK_QUEUES, DEAD_LETTER_EXCHANGE, DEAD_LETTER_QUEUE, 
    MAX_RETRIES, RETRY_BACKOFF, PREFETCH_COUNT
)

class Worker:
    def __init__(self, queue, callback):
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT, credentials=credentials)
        )
        self.channel = self.connection.channel()
        self.channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="direct")
        self.channel.exchange_declare(exchange=DEAD_LETTER_EXCHANGE, exchange_type="fanout")
        self.channel.queue_declare(queue=DEAD_LETTER_QUEUE, durable=True)
        self.channel.queue_bind(queue=DEAD_LETTER_QUEUE, exchange=DEAD_LETTER_EXCHANGE)

        # Navbat sozlamalari
        args = {
            "x-max-priority": TASK_QUEUES[queue]["max_priority"],
            "x-dead-letter-exchange": DEAD_LETTER_EXCHANGE
        }
        try:
            self.channel.queue_declare(queue=queue, durable=True, arguments=args)
            self.channel.queue_bind(queue=queue, exchange=EXCHANGE_NAME, routing_key=queue)
        except pika.exceptions.ChannelClosedByBroker as e:
            print(f"Queue {queue} already exists with different args: {e}. Continuing...")
            self.channel = self.connection.channel()
        self.channel.basic_qos(prefetch_count=PREFETCH_COUNT)
        self.callback = callback
        self.queue = queue

    def process_task(self, ch, method, properties, body):
        try:
            decompressed = zlib.decompress(body).decode()
            task = json.loads(decompressed)
            self.callback(task)  # Vazifani qayta ishlash
            ch.basic_ack(delivery_tag=method.delivery_tag)  # Muvaffaqiyatli tasdiqlash
        except Exception as e:
            print(f"Error processing task: {e}")
            task["retry_count"] = task.get("retry_count", 0) + 1
            if task["retry_count"] <= MAX_RETRIES:
                time.sleep(RETRY_BACKOFF[task["retry_count"] - 1])  # Eksponensial kechikish
                compressed = zlib.compress(json.dumps(task).encode())
                ch.basic_publish(
                    exchange=EXCHANGE_NAME,
                    routing_key=self.queue,
                    body=compressed,
                    properties=properties
                )
            else:
                ch.basic_publish(
                    exchange=DEAD_LETTER_EXCHANGE,
                    routing_key="",
                    body=body,
                    properties=properties
                )
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def start(self):
        self.channel.basic_consume(queue=self.queue, on_message_callback=self.process_task)
        print(f"Worker started for {self.queue}")
        self.channel.start_consuming()

    def close(self):
        self.connection.close()

def example_callback(task):
    print(f"Processing task {task['task_id']} of type {task['type']}")
    time.sleep(0.01)  # Simulyatsiya

if __name__ == "__main__":
    worker = Worker("image_processing", example_callback)
    try:
        worker.start()
    except KeyboardInterrupt:
        worker.close()
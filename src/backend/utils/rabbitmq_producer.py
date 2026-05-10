import json
from typing import Dict

import aio_pika
from aio_pika import Message
from loguru import logger


class AsyncRabbitMQProducer:
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        exchange_name: str = "documents_exchange",
        resume_queue: str = "resume_queue",
        resume_routing_key: str = "resume",
        jd_queue: str = "jd_queue",
        jd_routing_key: str = "job_description",
    ):

        self.host = host
        self.port = port
        self.username = username
        self.password = password

        self.exchange_name = exchange_name
        self.resume_queue = resume_queue
        self.resume_routing_key = resume_routing_key
        self.jd_queue = jd_queue
        self.jd_routing_key = jd_routing_key

        self.connection = None
        self.channel = None
        self.exchange = None

    async def connect(self):

        self.connection = await aio_pika.connect_robust(
            host=self.host,
            port=self.port,
            login=self.username,
            password=self.password,
        )

        self.channel = await self.connection.channel()
        logger.info("Connected to RabbitMQ")

        # Create exchange if it doesn't exist
        self.exchange = await self.channel.declare_exchange(
            self.exchange_name,
            aio_pika.ExchangeType.DIRECT,
            durable=True,
        )
        logger.info(f"Declared exchange: {self.exchange_name}")

        # Create resume queue if it doesn't exist
        resume_queue = await self.channel.declare_queue(
            self.resume_queue,
            durable=True,
        )
        logger.info(f"Declared queue: {self.resume_queue}")

        await resume_queue.bind(self.exchange, routing_key=self.resume_routing_key)
        logger.info(
            f"Bound queue {self.resume_queue} to exchange {self.exchange_name} with routing key {self.resume_routing_key}"
        )

        # Create job description queue if it doesn't exist
        jd_queue = await self.channel.declare_queue(
            self.jd_queue,
            durable=True,
        )
        logger.info(f"Declared queue: {self.jd_queue}")

        await jd_queue.bind(self.exchange, routing_key=self.jd_routing_key)
        logger.info(
            f"Bound queue {self.jd_queue} to exchange {self.exchange_name} with routing key {self.jd_routing_key}"
        )

    async def publish_message(self, routing_key: str, payload: Dict):

        if not self.exchange:
            raise RuntimeError("RabbitMQ exchange not initialized")

        body = json.dumps(payload).encode()

        await self.exchange.publish(
            Message(
                body=body,
                content_type="application/json",
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=routing_key,
        )

        logger.info(f"Published message with routing_key={routing_key}")

    async def close(self):

        if self.connection:
            await self.connection.close()

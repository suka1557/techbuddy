from loguru import logger

from src.backend.utils.rabbitmq_producer import AsyncRabbitMQProducer


async def push_notification_to_queue(
    producer: AsyncRabbitMQProducer, routing_key: str, payload: dict
):
    try:
        await producer.publish_message(routing_key=routing_key, payload=payload)
        logger.info(f"Message published to RabbitMQ | routing_key={routing_key}")
    except Exception as e:
        logger.error(f"Failed to publish message to RabbitMQ | error={str(e)}")

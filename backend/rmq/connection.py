import aio_pika
import asyncio
from logging_config import get_logger
from config import settings

logger = get_logger("rmq.connection")


class RabbitMQClient:
    _instance = None
    _init_lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RabbitMQClient, cls).__new__(cls)
            cls._instance.connection = None
        return cls._instance

    async def connect(self):
        if self.connection and not self.connection.is_closed:
            return self.connection

        async with self._init_lock:
            if self.connection and not self.connection.is_closed:
                return self.connection

            self.connection = await aio_pika.connect_robust(settings.rabbitmq_url)
            return self.connection

    async def get_channel(self, prefetch_count: int = None):
        if prefetch_count is None:
            prefetch_count = settings.prefetch_count
        
        connection = await self.connect()
        channel = await connection.channel()

        await channel.set_qos(prefetch_count=prefetch_count)

        return channel

    async def close(self):
        if self.connection and not self.connection.is_closed:
            await self.connection.close()


rabbitmq = RabbitMQClient()

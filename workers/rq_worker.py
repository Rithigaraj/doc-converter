import os

import redis
from rq import Worker, Queue, Connection

from app.config import settings

listen = [settings.rq_queue]
conn = redis.from_url(settings.redis_url)

if __name__ == "__main__":
    with Connection(conn):
        worker = Worker(list(map(Queue, listen)))
        worker.work()

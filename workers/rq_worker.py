import os
import sys
import redis
from rq import Worker, SimpleWorker, Queue, Connection

from app.config import settings

listen = [settings.rq_queue]
conn = redis.from_url(settings.redis_url)

if __name__ == "__main__":
    is_windows = (os.name == "nt" or sys.platform == "win32")
    WorkerClass = SimpleWorker if is_windows else Worker
    print(f"Starting {WorkerClass.__name__} for queue '{settings.rq_queue}' at {settings.redis_url}...")
    with Connection(conn):
        worker = WorkerClass(list(map(Queue, listen)))
        worker.work()

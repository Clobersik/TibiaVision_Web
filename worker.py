# worker.py
# Uruchamia proces workera RQ, który nasłuchuje na zadania w kolejce Redis.

import os
from redis import Redis
from rq import Worker, Queue, Connection

# Ustawienie nasłuchiwania na domyślnej kolejce
listen = ['default']

# Połączenie z serwerem Redis
# Nazwa hosta 'redis' jest zdefiniowana w docker-compose.yml
redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
conn = Redis.from_url(redis_url)

if __name__ == '__main__':
    with Connection(conn):
        worker = Worker(map(Queue, listen))
        worker.work()

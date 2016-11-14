import time
from datetime import datetime
import uuid

def now():
    return time.time()

def now_sec():
    return int(time.time()) 

def randstr(len=32):
    return uuid.uuid4().hex[:len]

def fmt_timestamp(time, fmt):
    return datetime.fromtimestamp(time).strftime(fmt)

def save_file(path, data):
    print(data)
    with open(path, 'w') as file:
        file.write(data)

import time
import uuid

def now():
    return time.time()

def now_sec():
    return int(time.time()) 

def randstr(len=32):
    return uuid.uuid4().hex[:len]

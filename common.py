import time
from datetime import date, datetime
import json
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
    with open(path, 'w') as file:
        file.write(data)

class ExternJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        return json.JSONEncoder.default(self, obj)
    
def json_dumps(obj):
    return json.dumps(obj, cls=ExternJsonEncoder)

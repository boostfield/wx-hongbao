import urllib
import ssl
from urllib import request

class HTTP:
    @classmethod
    def get(cls, url, **kws):
        rsp = cls.raw_get(url, **kws)
        return rsp.read().decode('utf-8')

    @classmethod
    def post(cls, url, data, **kws):
        rsp = cls.raw_post(url, data, **kws)
        return rsp.read().decode('utf-8')
    
    @classmethod
    def _query_str(cls, kw):
        querys = ["{}={}".format(key, kw[key]) for key in kw]
        return '&'.join(querys)

    @classmethod
    def raw_get(cls, url, **kws):
        return cls._req(url, kws)

    @classmethod
    def raw_post(cls, url, data, **kws):
        if type(data) is str:
            data = data.encode('utf-8')
        return cls._req(url, kws, data)
    
    @classmethod
    def _req(cls, url, args={}, data=None):
        url = cls.joinurl(url, **args)
        return urllib.request.urlopen(url, data)

    @classmethod
    def download(cls, url, path):
        return urllib.request.urlretrieve(url, path)
        
    @classmethod
    def joinurl(cls, url, **kws):
        query = cls._query_str(kws)
        if query:
            return url + '?' + query
        return url
    
    @classmethod
    def ssl_post(cls, cert_file, key_file, url, data):
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        context.load_cert_chain(cert_file, key_file)
        rsp = urllib.request.urlopen(url, data, context=context)
        return rsp.read().decode('utf-8')

    @classmethod
    def urlencode(cls, params):
        return urllib.parse.urlencode(params)

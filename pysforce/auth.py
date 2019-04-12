import time
from abc import ABC, abstractmethod
import jwt
import requests
import json


class SFAuthCommon(ABC):

    @abstractmethod
    def authenticate(self):
        pass


class SFAuthenticator(object):

    def __init__(self):
        self.access_token = None
        self.service_url = None
        self.client = None
        self._authenticated = False

    def is_authenticated(self):
        return self._authenticated

    def construct(self, payload):
        self.access_token = payload['access_token']
        self.service_url = payload['instance_url']
        self.client = requests.Session()
        self.client.headers.update({'Authorization': 'OAuth ' + self.access_token,
                                    'Content-Type': 'application/json; charset=UTF-8',
                                    'Accept-Encoding': 'gzip, compress, deflate', 'Accept-Charset': 'utf-8'})


class OAuthJWT(SFAuthenticator, SFAuthCommon):

    def __init__(self, username: str, consumer_key: str, cert_key: str, server_url='https://test.salesforce.com'):
        SFAuthenticator.__init__(self)
        self.username = username
        self.consumer_key = consumer_key
        self.cert_key = cert_key
        self.server_url = server_url

    def authenticate(self):
        payload = {'iss': self.consumer_key,
                   'sub': self.username,
                   'aud': self.server_url,
                   'exp': int(time.time()) + 60
                   }
        package = jwt.encode(payload, self.cert_key, algorithm='RS256')
        rsp = requests.post(self.server_url + '/services/oauth2/token',
                            data={'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                                  'assertion': package},
                            headers={'content-type': 'application/x-www-form-urlencoded'})
        payload = json.loads(rsp.text)
        if 'error' in payload:
            raise Exception(payload['error_description'])
        rsp.raise_for_status()
        self._authenticated = True
        SFAuthenticator.construct(self, payload)


class OAuthPassword(SFAuthenticator):
    _username = None
    _password = None
    _consumer_key = None
    _consumer_secret = None
    _server_url = None

    def __init__(self, username: str, password: str, consumer_key: str, consumer_secret: str,
                 server_url='https://test.salesforce.com'):
        SFAuthenticator.__init__(self)
        self._username = username
        self._password = password
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret
        self._server_url = server_url

    def authenticate(self):
        payload = {'grant_type': 'password',
                   'username': self._username,
                   'password': self._password,
                   'client_id': self._consumer_key,
                   'client_secret': self._consumer_secret
                   }
        rsp = requests.post(self._server_url + '/services/oauth2/token', data=payload,
                            headers={'content-type': 'application/x-www-form-urlencoded'})
        payload = json.loads(rsp.text)
        if 'error' in payload:
            raise Exception(payload['error_description'])
        rsp.raise_for_status()
        super._authenticated = True
        SFAuthenticator.construct(self, payload)

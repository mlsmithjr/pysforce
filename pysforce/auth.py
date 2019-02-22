import time
import jwt
import requests
import json


class Authenticator(object):

    access_token = None
    service_url = None
    client = None
    _authenticated = False

    def __init__(self):
        pass

    def authenticate(self):
        pass

    def is_authenticated(self):
        return self._authenticated

    def construct(self, payload):
        self.access_token = payload['access_token']
        self.service_url = payload['instance_url']
        self.client = requests.Session()
        self.client.headers.update({'Authorization': 'OAuth ' + self.access_token,
                                    'Content-Type': 'application/json; charset=UTF-8',
                                    'Accept-Encoding': 'gzip, compress, deflate', 'Accept-Charset': 'utf-8'})


class OAuthJWT(Authenticator):

    def __init__(self, username: str, consumer_key: str, cert_key: str, server_url='https://test.salesforce.com'):
        Authenticator.__init__(self)
        payload = {'iss': consumer_key,
                   'sub': username,
                   'aud': server_url,
                   'exp': int(time.time()) + 60
                   }
        package = jwt.encode(payload, cert_key, algorithm='RS256')
        rsp = requests.post(server_url + '/services/oauth2/token',
                            data={'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
                                  'assertion': package},
                            headers={'content-type': 'application/x-www-form-urlencoded'})
        payload = json.loads(rsp.text)
        if 'error' in payload:
            raise Exception(payload['error_description'])
        rsp.raise_for_status()
        self._authenticated = True
        Authenticator.construct(self, payload)


class OAuthPassword(Authenticator):
    _username = None
    _password = None
    _consumer_key = None
    _consumer_secret = None
    _server_url = None

    def __init__(self, username: str, password: str, consumer_key: str, consumer_secret: str,
                 server_url='https://test.salesforce.com'):
        Authenticator.__init__(self)
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
        Authenticator.construct(self, payload)

# Released into the Public Domain by tav@espians.com

import sys, logging, os
import urllib2
from service_util import ServiceUtil

from datetime import datetime, timedelta
from hashlib import sha1
from hmac import new as hmac
from os.path import dirname, join as join_path
from random import getrandbits
from time import time
from urllib import urlencode, quote as urlquote
from uuid import uuid4
from wsgiref.handlers import CGIHandler

#sys.path.insert(0, join_path(dirname(__file__), 'lib')) # extend sys.path
sys.path.append(os.path.join(os.path.dirname(__file__),'lib'))

from demjson import decode as decode_json

import thrift.protocol.TBinaryProtocol as TBinaryProtocol
import thrift.transport.THttpClient as THttpClient
import evernote.edam.userstore.UserStore as UserStore
import evernote.edam.userstore.constants as UserStoreConstants
import evernote.edam.error.ttypes as Errors

from google.appengine.api.urlfetch import fetch as urlfetch, GET, POST
from google.appengine.ext import db
from google.appengine.ext.webapp import RequestHandler, WSGIApplication

OAUTH_APP_SETTINGS = {

    'twitter': {

        'consumer_key': 'z3Yh5b0DoVZqrRfEekLehA',
        'consumer_secret': '1AGbtzFbPfZYmjoasi5VuNpKESZxJiOA51jryY8cjUk',

        'request_token_url': 'https://api.twitter.com/oauth/request_token',
        'access_token_url': 'https://api.twitter.com/oauth/access_token',
        'user_auth_url': 'https://api.twitter.com/oauth/authorize',

        'default_api_prefix': 'http://twitter.com',
        'default_api_suffix': '.json',
        'return_to': '/'

        },

    'google': {

        'consumer_key': '943960239515.apps.googleusercontent.com',
        'consumer_secret': 'dfST9jwUrx5NoiLs-fF2Ryvw',

        'request_token_url': 'https://www.google.com/accounts/OAuthGetRequestToken',
        'access_token_url': 'https://www.google.com/accounts/OAuthGetAccessToken',
        'user_auth_url': 'https://www.google.com/accounts/OAuthAuthorizeToken',
        'return_to': '/'

        },


    'evernote': {

	'consumer_key':'bojanbabic-9482',
	'consumer_secret':'3e4e861ac2c0b758',
	
	'request_token_url': 'https://www.evernote.com/oauth',
	'access_token_url': 'https://www.evernote.com/oauth',
	'user_auth_url':'https://www.evernote.com/OAuth.action',
        'oauth_callback': 'http://www.instaright.com/oauth/evernote/callback',
        'return_to': '/user/dashboard'

        },
    'flickr': {

	'consumer_key':'3cf3ac115819762cc381b9a62d4a79ac',
	'consumer_secret':'d9249d1ffa11fae0',
	
        'request_token_url': 'http://www.flickr.com/services/oauth/request_token',
        'access_token_url': 'http://www.flickr.com/services/oauth/access_token',
        'user_auth_url':'http://www.flickr.com/services/oauth/authorize',
        'oauth_callback': 'http://www.instaright.com/oauth/flickr/callback',
        'return_to': '/user/dashboard'

        },
    }


CLEANUP_BATCH_SIZE = 100
EXPIRATION_WINDOW = timedelta(seconds=60*60*1) # 1 hour

try:
    from config import OAUTH_APP_SETTINGS
except:
    pass

STATIC_OAUTH_TIMESTAMP = 12345 # a workaround for clock skew/network lag

def get_service_key(service, cache={}):
    if service in cache: return cache[service]
    return cache.setdefault(
        service, "%s&" % encode(OAUTH_APP_SETTINGS[service]['consumer_secret'])
        )

def create_uuid():
    return 'id-%s' % uuid4()

def encode(text):
    return urlquote(str(text), '')

def twitter_specifier_handler(client):
    return client.get('/account/verify_credentials')['screen_name']

def evernote_specifier_handler(client):
    sl=ServiceUtil()
    userStoreHttpClient = THttpClient.THttpClient(sl.userStoreUri)
    userStoreProtocol = TBinaryProtocol.TBinaryProtocol(userStoreHttpClient)
    userStore = UserStore.Client(userStoreProtocol)
    user= userStore.getUser(urllib2.unquote(client.token.oauth_token))
        
    return user.username

def flickr_specifier_handler(client):
        return client.get('')
OAUTH_APP_SETTINGS['twitter']['specifier_handler'] = twitter_specifier_handler
OAUTH_APP_SETTINGS['evernote']['specifier_handler'] = evernote_specifier_handler
OAUTH_APP_SETTINGS['flickr']['specifier_handler'] = flickr_specifier_handler

class OAuthRequestToken(db.Model):
    """OAuth Request Token."""

    service = db.StringProperty()
    oauth_token = db.StringProperty()
    oauth_token_secret = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add=True)

class OAuthAccessToken(db.Model):
    """OAuth Access Token."""

    service = db.StringProperty()
    specifier = db.StringProperty()
    oauth_token = db.StringProperty()
    oauth_token_secret = db.StringProperty()
    additional_info=db.StringProperty()
    created = db.DateTimeProperty(auto_now_add=True)

class OAuthClient(object):

    __public__ = ('callback', 'cleanup', 'login', 'logout')

    def __init__(self, service, handler, oauth_callback=None, **request_params):
        self.service = service
        self.service_info = OAUTH_APP_SETTINGS[service]
        self.service_key = None
        self.handler = handler
        self.request_params = request_params
        self.oauth_callback = oauth_callback
        self.token = None
        self.oauth_verifier = None

    # public methods

    def get(self, api_method, http_method='GET', expected_status=(200,), **extra_params):

        if not (api_method.startswith('http://') or api_method.startswith('https://')):
            api_method = '%s%s%s' % (
                self.service_info['default_api_prefix'], api_method,
                self.service_info['default_api_suffix']
                )

        if self.token is None:
            self.token = OAuthAccessToken.get_by_key_name(self.get_cookie())

        fetch = urlfetch(self.get_signed_url(
            api_method, self.token, http_method, **extra_params
            ))

        if fetch.status_code not in expected_status:
            raise ValueError(
                "Error calling... Got return status: %i [%r]" %
                (fetch.status_code, fetch.content)
                )

        return decode_json(fetch.content)
        #return fetch.content

    def post(self, api_method, http_method='POST', expected_status=(200,), **extra_params):

        if not (api_method.startswith('http://') or api_method.startswith('https://')):
            api_method = '%s%s%s' % (
                self.service_info['default_api_prefix'], api_method,
                self.service_info['default_api_suffix']
                )

        if self.token is None:
            self.token = OAuthAccessToken.get_by_key_name(self.get_cookie())

        fetch = urlfetch(url=api_method, payload=self.get_signed_body(
            api_method, self.token, http_method, **extra_params
            ), method=http_method)

        if fetch.status_code not in expected_status:
            raise ValueError(
                "Error calling... Got return status: %i [%r]" %
                (fetch.status_code, fetch.content)
                )

        return decode_json(fetch.content)
        #return fetch.content

    def login(self):

        proxy_id = self.get_cookie()

        if proxy_id:
	    if self.service == 'twitter':
	    	self.handler.redirect(self.handler.request.get("return_to", '/'))
	    if self.service == 'evernote':
                self.expire_cookie()
                #return_to=OAUTH_APP_SETTINGS[self.service]['return_to']
	    	#self.handler.redirect(self.handler.request.get("return_to", return_to))
            #else:
            #    return "FOO%rFF" % proxy_id
            self.expire_cookie()


        return self.get_request_token()

    def logout(self, return_to='/'):
        self.expire_cookie()
        self.handler.redirect(self.handler.request.get("return_to", return_to))

    # oauth workflow

    def get_request_token(self):

        token_info = self.get_data_from_signed_url(
            self.service_info['request_token_url'], **self.request_params
            )
        logging.info('token info %s' % token_info)

        token = OAuthRequestToken(
            service=self.service,
            **dict(token.split('=') for token in token_info.split('&'))
            )

        token.put()

        if self.oauth_callback:
            oauth_callback = {'oauth_callback': self.oauth_callback}
        else:
            oauth_callback = {}

        self.handler.redirect(self.get_signed_url(
            self.service_info['user_auth_url'], token, **oauth_callback
            ))

    def callback(self, return_to='/'):

        oauth_token = self.handler.request.get("oauth_token")
        oauth_verifier = self.handler.request.get("oauth_verifier")

        if not oauth_token:
            return self.get_request_token()
        if oauth_verifier is not None:
                self.oauth_verifier = oauth_verifier

        specifier = None
        oauth_token = OAuthRequestToken.all().filter(
            'oauth_token =', oauth_token).filter(
            'service =', self.service).fetch(1)[0]

        logging.info('callback')

        token_info = self.get_data_from_signed_url(
                self.service_info['access_token_url'], oauth_token
            )

        logging.info('callback token info: %s' % token_info)
        key_name = create_uuid()

        self.token = OAuthAccessToken(
            key_name=key_name, service=self.service,
            **dict(token.split('=') for token in token_info.split('&'))
            )

        if self.service == 'evernote':
                token_dict=dict(s.split('=') for s in token_info.split('&'))    
                edamShard = token_dict["edam_shard"]
                edamUserID = token_dict["edam_userId"]
                logging.info('edam user id %s' % edamUserID)
                logging.info('edam shard %s' % edamShard)
                self.token.additional_info='edam_userId=%s&edam_shard=%s' %(edamUserID, edamShard)
        if self.service == 'flickr':
                token_dict =dict(s.split('=') for s in token_info.split('&'))
                logging.info('flickr token info %s' % token_dict)
                specifier = self.token.specifier = urllib2.unquote(token_dict["username"])

        return_to=OAUTH_APP_SETTINGS[self.service]['return_to']

        if 'specifier_handler' in self.service_info and specifier is None:
            logging.info('specifier_handler %s for %s' %(self.service_info, self.service))
            specifier = self.token.specifier = self.service_info['specifier_handler'](self)
            old = OAuthAccessToken.all().filter(
                'specifier =', specifier).filter(
                'service =', self.service)
            db.delete(old)

        self.token.put()
        logging.info('setting cookie %s' % key_name)
        self.set_cookie(key_name)
        self.handler.redirect(return_to)

    def cleanup(self):
        query = OAuthRequestToken.all().filter(
            'created <', datetime.now() - EXPIRATION_WINDOW
            )
        count = query.count(CLEANUP_BATCH_SIZE)
        db.delete(query.fetch(CLEANUP_BATCH_SIZE))
        return "Cleaned %i entries" % count

    # request marshalling

    def get_data_from_signed_url(self, __url, __token=None, __meth='GET', **extra_params):
        return urlfetch(self.get_signed_url(
            __url, __token, __meth, **extra_params
            )).content

    def get_signed_url(self, __url, __token=None, __meth='GET',**extra_params):
        logging.info('%s?%s'%(__url, self.get_signed_body(__url, __token, __meth, **extra_params)))
        return '%s?%s'%(__url, self.get_signed_body(__url, __token, __meth, **extra_params))

    def get_signed_body(self, __url, __token=None, __meth='GET',**extra_params):

        service_info = self.service_info

        kwargs = {
            'oauth_consumer_key': service_info['consumer_key'],
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_version': '1.0',
            'oauth_timestamp': int(time()),
            'oauth_nonce': getrandbits(64),
            }

        kwargs.update(extra_params)
        if self.service == 'evernote' or self.service == 'flickr':
                kwargs.update({'oauth_callback': OAUTH_APP_SETTINGS[self.service]['oauth_callback']})
        if self.oauth_verifier is not None:
                kwargs.update({'oauth_verifier': self.oauth_verifier})

        if self.service_key is None:
            self.service_key = get_service_key(self.service)

        if __token is not None:
            kwargs['oauth_token'] = __token.oauth_token
            key = self.service_key + encode(__token.oauth_token_secret)
        else:
            key = self.service_key

        message = '&'.join(map(encode, [
            __meth.upper(), __url, '&'.join(
                '%s=%s' % (encode(k), encode(kwargs[k])) for k in sorted(kwargs)
                )
            ]))

        kwargs['oauth_signature'] = hmac(
            key, message, sha1
            ).digest().encode('base64')[:-1]

        logging.info('oauth url args: %s' % kwargs )
        return urlencode(kwargs)

    # who stole the cookie from the cookie jar?

    def get_cookie(self):
        return self.handler.request.cookies.get(
            'oauth.%s' % self.service, ''
            )

    def set_cookie(self, value, path='/'):
        self.handler.response.headers.add_header(
            'Set-Cookie', 
            '%s=%s; path=%s; expires="Fri, 31-Dec-2021 23:59:59 GMT"' %
            ('oauth.%s' % self.service, value, path)
            )

    def expire_cookie(self, path='/'):
        self.handler.response.headers.add_header(
            'Set-Cookie', 
            '%s=; path=%s; expires="Fri, 31-Dec-1999 23:59:59 GMT"' %
            ('oauth.%s' % self.service, path)
            )

class OAuthHandler(RequestHandler):

    def get(self, service, action=''):

        if service not in OAUTH_APP_SETTINGS:
            return self.response.out.write(
                "Unknown OAuth Service Provider: %r" % service
                )

        client = OAuthClient(service, self)

        logging.info('action %s ' % action)
        if action in client.__public__:
            self.response.out.write(getattr(client, action)())
        else:
            self.response.out.write(client.login())

def main():

    application = WSGIApplication([
       ('/oauth/(.*)/(.*)', OAuthHandler),
       ], debug=True)

    CGIHandler().run(application)

if __name__ == '__main__':
    main()

import datetime, time, urllib2, urllib, logging, simplejson, os, BeautifulSoup, sys, base64
from google.appengine.ext import webapp
from google.appengine.api import urlfetch
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api.labs import taskqueue
from google.appengine.ext.webapp import template
try:
        #python 2.6
        from urlparse import parse_qsl
except ImportError:
        #python 2.5
        from cgi import parse_qsl
from hashlib import sha1 
from hmac import new as hmac

from models import UserDetails, SessionModel, UserStats, DeliciousImporter

oauth_nonce='delicious_tool'
oauth_consumer_key='dj0yJmk9U0hEZmxKVTFlRjY0JmQ9WVdrOVVHTldjMWR2Tm1jbWNHbzlNVE01TlRVNE5UZzJNZy0tJnM9Y29uc3VtZXJzZWNyZXQmeD0wMA--'
oauth_signature_method='plaintext'
oauth_signature='231b69a7d7b85e0b6e9d345bdf999b7922a2dbbc'
oauth_version='1.0'
oauth_callback='http://instaright.appspot.com/tools/delicious/callback'
#oauth_callback='http://localhost:8080/tools/delicious/callback'

class DeliciousImportHandler(webapp.RequestHandler):
        def get(self):
		template_variables = []
                #get delicious auth tokens
                timestamp =  int(time.time())
                params='oauth_nonce='+oauth_nonce+'&oauth_timestamp='+str(timestamp)+'&oauth_consumer_key='+oauth_consumer_key+'&oauth_signature_method=plaintext&oauth_signature='+oauth_signature+'%26&oauth_version='+oauth_version+'&xoauth_lang_pref=en-us&oauth_callback='+oauth_callback
                token_url='https://api.login.yahoo.com/oauth/v2/get_request_token?'+params
                logging.info('sending data %s' %params)
                result = urlfetch.fetch(
                                        url=token_url,
                                        method=urlfetch.GET 
                                        )
                logging.info('status code %s' % result.status_code)
                if result.status_code == 200:
                        response=urllib.unquote(result.content)
                        logging.info('result %s' % response)
                        response_dict = dict(parse_qsl(response))
                        logging.info('result %s' % response_dict['xoauth_request_auth_url'])
                        xoauth_url=response_dict['xoauth_request_auth_url']
                        oauth_token=response_dict['oauth_token']
                        oauth_token_secret=response_dict['oauth_token_secret']
                        oauth_expires_in=response_dict['oauth_expires_in']
                        dimporter=DeliciousImporter()
                        dimporter.oauth_token=oauth_token
                        dimporter.oauth_token_secret=oauth_token_secret
                        dimporter.oauth_expires_in=datetime.datetime.now() + datetime.timedelta(seconds=int(oauth_expires_in))
                        dimporter.put()
                        login_url=xoauth_url+'&oauth_nonce='+oauth_nonce+'&oauth_timestamp='+str(int(time.time()))+'&oauth_consumer_key='+oauth_consumer_key+'&oauth_signature_method=plaintext&oauth_signature='+oauth_signature+'&oauth_version='+oauth_version+'xoauth_lang_pref=enus&oauth_callback='+oauth_callback
                        template_variables={'yahoo_login_url':login_url}
		path= os.path.join(os.path.dirname(__file__), '../templates/import_tool.html')
                self.response.headers["Content-Type"] = "text/html; charset=utf-8"
		self.response.out.write(template.render(path,template_variables))
                

class InstapaperImporter(webapp.RequestHandler):
        def post(self):
               token = self.request.get('token',None)
               oauth_token_secret = self.request.get('oauth_token_secret',None)
               iuser = self.request.get('iuser',None)
               ipass = self.request.get('ipass',None)
               logging.info('credentials instapaper %s %s' % (iuser, ipass))
               if token is None or iuser is None:
                        logging.info('bad request ')
                        self.response.out.write('Bad request!')
                        return
               logging.info('token %s ' %token)
               logging.info('oauth_token_secret %s ' %oauth_token_secret)
               auth_resp = 200
               try:
                        authen_url='https://www.instapaper.com/api/authenticate'
                        values = {'username':iuser, 'password':ipass}
                        data = urllib.urlencode(values)
                        result = urlfetch.fetch(
                                        url=authen_url,
                                        payload=data, 
                                        method=urlfetch.POST, 
                                        headers={'Content-Type': 'application/x-www-form-urlencoded'})
                        auth_resp = result.status_code
                        logging.info('response %s' % result.status_code)
               except:
                        logging.info('instapaper authenticate error %s %s' % (sys.exc_info()[0], sys.exc_info()[1]))
                        auth_resp = 404
               successImport = DeliciousImporter.gql('WHERE instapaper_account = :1 and success = True', iuser).get()
               if successImport is None:
                        logging.info('initializing new import instapaper:%s delicious:%s' %(iuser))
                        importStats=DeliciousImporter()
                        importStats.instapaper_account=iuser
                        importStats.instapaper_pass=ipass
                        importStats.oauth_token=token
                        importStats.put()
               else:
                        logging.info('repeating import delicious %s instapaper ' %(iuser))
                        
               if auth_resp == 200:
                        taskqueue.add(queue_name='instapaper-import', url='/tools/import/delicious/task', 
                                params={'token':token, 'oauth_token_secret': oauth_token_secret, 'iuser':iuser, 'ipass':ipass})
                        resp='Import has been initialized, it can take a while. Try <a href="http://bit.ly/instaright" title="Instapaper Firefox addon">Instapaper Firefox addon</a>.'
                        
               elif auth_resp == 403:
                        logging.info('instapaper validation did not pass %s' %auth_resp)
                        resp='Invalid Instapaper credentials.'
               else:
                        logging.info('something is wrong w/ service')
                        resp='Error encountered. Please try later!'
               self.response.out.write(resp)
                                
                         
class DeliciousImportTask(webapp.RequestHandler):
        def post(self):
               token = self.request.get('token',None)
               oauth_token_secret = self.request.get('oauth_token_secret',None)
               iuser = self.request.get('iuser',None)
               ipass = self.request.get('ipass',None)
               logging.info('token %s' % token)
               logging.info('oauth token secret %s' % oauth_token_secret)
               #d_link='http://feeds.delicious.com/v2/json/%s'  %duser
               d_link='https://api.del.icio.us/v2/posts/all'
               d_link_quote='https%3A%2F%2Fapi.del.icio.us%2Fv2%2Fposts%2Fall'
               oauth_consumer_key_esc=urllib.quote(oauth_consumer_key)
               oauth_nonce_esc=urllib.quote(oauth_nonce)
               token_esc=urllib.quote(token)
               oauth_version_esc=urllib.quote(oauth_version)

               request_params_esc=urllib.quote('oauth_consumer_key='+oauth_consumer_key_esc+'&oauth_nonce='+oauth_nonce_esc+'&oauth_signature_method=HMAC-SHA1'+'&oauth_timestamp='+str(int(time.time()))+'&oauth_token='+token_esc+'&oauth_version='+oauth_version_esc)

               #delicious_request_string='GET&'+d_link_quote+'&oauth_consumer_key%3D'+oauth_consumer_key+'%26oauth_nonce%3D'+oauth_nonce+'%26oauth_signature_method%3DHMAC-SHA1%26oauth_timestamp%3D'+str(int(time.time()))+'%26oauth_token%3D'+urllib.quote(urllib.quote(token))+'%26oauth_version%3D'+oauth_version
               dstring='GET&'+d_link_quote+'&'+request_params_esc

               logging.info('request string %s' % dstring)
               digest_string=hmac(str(oauth_signature+"&"+oauth_token_secret), dstring, sha1).digest().encode('base64')[:-1]
               logging.info('digest_string: %s'  %digest_string)
               
               #dpass = self.request.get('dpass',None)
               #auth_header="OAuth realm=\"yahooapis.com\",oauth_consumer_key=\""+oauth_consumer_key+"\",oauth_nonce=\""+oauth_nonce+"\",oauth_signature_method=\"HMAC-SHA1\",oauth_timestamp=\""+str(int(time.time()))+"\",oauth_token=\""+urllib.quote(token)+"\",oauth_version=\""+oauth_version+"\",ouath_signature=\""+urllib.quote(digest_string)+"\"" 
               auth_header="OAuth realm=\"yahooapis.com\",oauth_consumer_key=\""+oauth_consumer_key+"\",oauth_nonce=\""+oauth_nonce+"\",oauth_signature_method=\"HMAC-SHA1\",oauth_timestamp=\""+str(int(time.time()))+"\",oauth_token=\""+urllib.quote(token)+"\",oauth_version=\""+oauth_version+"\",ouath_signature=\""+urllib.quote(digest_string)+"\"" 
               header_string="OAuth realm=\"yahooapis.com\",oauth_consumer_key=\""+oauth_consumer_key+"\",oauth_nonce=\""+oauth_nonce+"\",oauth_signature_method=\"HMAC-SHA1\",oauth_timestamp=\""+str(int(time.time()))+"\",oauth_token=\""+urllib.quote(token)+"\",oauth_version=\""+urllib.quote(oauth_version)+"\",oauth_signature=\""+urllib.quote(digest_string).replace('\\','%5C').replace('/','%2F').replace(':','%3A')+"\""
               logging.info('auth header: %s' % auth_header)
               logging.info('header: %s' % header_string)
               result = urlfetch.fetch(
                                        url=d_link,
                                        method=urlfetch.GET,
                                        headers={"Authorization":header_string} 
                                        )
               logging.info('yahoo response: %s' % result.content)
               logging.info('yahoo response status code: %s' % result.status_code)
               logging.info('try with url')
               #d_url=d_link+"?oauth_consumer_key="+oauth_consumer_key+"&oauth_nonce="+oauth_nonce+"&oauth_signature_method=HMAC-SHA1&oauth_timestamp="+str(int(time.time()))+"&oauth_token="+urllib.quote(token)+"&oauth_version="+oauth_version+"&oauth_signature="+urllib.quote(digest_string)
               #logging.info('url %s' % d_url)
               #result = urlfetch.fetch(
               #                         url=d_url,
               #                         method=urlfetch.GET,
               #                         )
               #logging.info('yahoo response: %s' % result.content)
               #logging.info('yahoo response status code: %s' % result.status_code)
               
               return
               json = simplejson.load(dta)
               if json is not None:
                   for j in json:
                       logging.info('delicious link %s %s' %(j['d'], j['u']))
                       taskqueue.add(queue_name='instapaper-import', url='/tools/import/instapaper/task', 
                       params={'instauser': iuser, 'instapass':ipass,'url':j['u'], 'title':j['d']})
               existing=DeliciousImporter.gql('where instapaper_account = :1 ', iuser).get()
               existing.success=True
               existing.put()
               
                
class InstapaperImportTask(webapp.RequestHandler):
        def post(self):
               importer_prefix='{Instaright-Importer} '
               user = self.request.get('instauser', None)
               pasw = self.request.get('instapass', None)
               url = self.request.get('url', None)
               title = self.request.get('title', None)
               values = {'username': user, 'password':pasw, 'title': importer_prefix+title.encode('utf8'), 'url':url}
               data = urllib.urlencode(values)
               result = urlfetch.fetch(
                                        url='https://www.instapaper.com/api/add', 
                                        payload=data, 
                                        method=urlfetch.POST, 
                                        headers={'Content-Type': 'application/x-www-form-urlencoded'})
               logging.info('response %s' % result.status_code)

class DeliciousCallbackHandler(webapp.RequestHandler):
        def get(self):
		template_variables = []
                oauth_token=self.request.get('oauth_token', None)
                oauth_verifier=self.request.get('oauth_verifier', None)
                logging.info('Looking for delicious importer session: oauth_token %s ' % oauth_token)
                dimporter=DeliciousImporter.gql('WHERE oauth_token = :1 and oauth_expires_in > :2', oauth_token, datetime.datetime.now()).get()
                if dimporter is not None:
                        yahoo_url='https://api.login.yahoo.com/oauth/v2/get_token?oauth_consumer_key='+oauth_consumer_key+'&oauth_signature_method=plaintext&oauth_version='+oauth_version+'&oauth_verifier='+oauth_verifier+'&oauth_token='+oauth_token+'&oauth_nonce='+oauth_nonce+'&oauth_timestamp='+str(int(time.time()))+'&oauth_signature='+oauth_signature+'%26'+dimporter.oauth_token_secret
                        logging.info('yahoo url %s' % yahoo_url)
                        result = urlfetch.fetch(
                                        url=yahoo_url,
                                        method=urlfetch.GET 
                                        )
                        logging.info('recieved response %s' %result.content)
                        response=urllib.unquote(result.content)
                        logging.info('result %s' % response)
                        response_dict = dict(parse_qsl(response))
                        try:
                                logging.info('result %s' % response_dict['oauth_token'])
                                token=response_dict['oauth_token']
                                oauth_token_secret=response_dict['oauth_token_secret']
                                oauth_expires_in=response_dict['oauth_expires_in']
                                oauth_session_handle=response_dict['oauth_session_handle']
                                oauth_authorization_expires_in=response_dict['oauth_authorization_expires_in']
                                xoauth_yahoo_guid=response_dict['xoauth_yahoo_guid']
                                logging.info('token %s' %token)
		                template_variables = {'token':token, 'oauth_token_secret':oauth_token_secret }
                        except:
                                logging.info('key error %s  %s' %(sys.exc_info()[0], sys.exc_info()[1]))
		path= os.path.join(os.path.dirname(__file__), '../templates/import_tool.html')
                self.response.headers["Content-Type"] = "text/html; charset=utf-8"
		self.response.out.write(template.render(path,template_variables))
                
app = webapp.WSGIApplication([
                                ('/tools/delicious', DeliciousImportHandler),
                                ('/tools/delicious/callback', DeliciousCallbackHandler),
                                ('/tools/import/instapaper/task', InstapaperImportTask),
                                ('/tools/import/delicious/task', DeliciousImportTask),
                                ('/tools/import/delicious', InstapaperImporter),
                                        ], debug =True)
def main():
        run_wsgi_app(app)

if __name__ == "__main__":
        main()


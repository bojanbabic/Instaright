import datetime, time, urllib2, urllib, logging, os, sys
from google.appengine.ext import webapp
from google.appengine.api import urlfetch
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api.labs import taskqueue
from google.appengine.ext.webapp import template

from models import UserDetails, SessionModel, UserStats, DeliciousImporter
from generic_handler import GenericWebHandler

sys.path.append(os.path.join(os.path.dirname(__file__),'lib'))
import simplejson

class DeliciousImportHandler(GenericWebHandler):
        def get(self):
                self.redirect_perm()
		template_variables = []
		path= os.path.join(os.path.dirname(__file__), '../templates/import_tool.html')
                self.response.headers["Content-Type"] = "text/html; charset=utf-8"
		self.response.out.write(template.render(path,template_variables))
                

class InstapaperImporter(webapp.RequestHandler):
        def post(self):
               duser = self.request.get('duser',None)
               iuser = self.request.get('iuser',None)
               ipass = self.request.get('ipass',None)
               dpass = self.request.get('dpass',None)
               logging.info('credentials delicious %s %s instapaper %s %s' % (duser, dpass, iuser, ipass))
               if duser is None or iuser is None:
                        logging.info('bad request ')
                        self.response.out.write('Bad request!')
                        return
               if '@yahoo' in duser:
                        duser = duser[:duser.index('@')]
                        logging.info('proposed screen name %s'  %duser)
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
               successImport = DeliciousImporter.gql('WHERE instapaper_account = :1 and delicious_account = :2 and success = True', iuser, duser).get()
               if successImport is None:
                        logging.info('initializing new import instapaper:%s delicious:%s' %(iuser, duser))
                        importStats=DeliciousImporter()
                        importStats.instapaper_account=iuser
                        importStats.instapaper_pass=ipass
                        importStats.delicious_account=duser
                        importStats.put()
               else:
                        logging.info('repeating import delicious %s instapaper %s' %(iuser, duser))
                        
               if auth_resp == 200:
                        taskqueue.add(queue_name='instapaper-import', url='/tools/import/delicious/task', 
                                params={'duser':duser, 'iuser':iuser, 'ipass':ipass})
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
               duser = self.request.get('duser',None)
               iuser = self.request.get('iuser',None)
               ipass = self.request.get('ipass',None)
               d_link='http://feeds.delicious.com/v2/json/%s'  %duser
               logging.info('fetching felicious feed %s' %d_link)
               #dpass = self.request.get('dpass',None)
               json = None
               try:
                       dta = urllib2.urlopen(d_link)
                       json = simplejson.load(dta)
               except:
                       logging.info('can\'t fetch url %s' % d_link)
               if json is not None:
                   for j in json:
                       logging.info('delicious link %s %s' %(j['d'], j['u']))
                       taskqueue.add(queue_name='instapaper-import', url='/tools/import/instapaper/task', 
                       params={'instauser': iuser, 'instapass':ipass,'url':j['u'], 'title':j['d']})
               existing=DeliciousImporter.gql('where instapaper_account = :1 and delicious_account = :2', iuser, duser).get()
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
                
                
app = webapp.WSGIApplication([
                                ('/tools/delicious', DeliciousImportHandler),
                                ('/tools/import/instapaper/task', InstapaperImportTask),
                                ('/tools/import/delicious/task', DeliciousImportTask),
                                ('/tools/import/delicious', InstapaperImporter),
                                        ], debug =True)
def main():
        run_wsgi_app(app)

if __name__ == "__main__":
        main()


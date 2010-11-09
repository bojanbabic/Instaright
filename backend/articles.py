import logging, datetime, os, sys
from google.appengine.ext import webapp
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from models import UserDetails, SessionModel
from utils import UserUtil
import simplejson

from feedformatter import Feed

DOMAIN = 'http://instaright.appspot.com'

class FeedGenerator(webapp.RequestHandler):
	def get(self):
                memcache_key='feed_json_cache'
                cached_feed= memcache.get(memcache_key)
		format = self.request.get('format', None);
                userUtil = UserUtil()
                if format == 'json' and cached_feed:
			logging.info('getting json from cache')
			self.response.headers['Content-Type'] = "application/json"
#			messageAsJSON = [{'u':{'id':update.id, 't':update.title,'l':update.link,'d':update.domain,'u':update.updated}}]
                        self.response.out.write(simplejson.dumps(cached_feed, default=lambda o: {'u':{'id':str(o.key()), 't':unicode(o.title), 'l': 'http://instaright.appspot.com/article/'+str(o.key()), 'd':o.domain, 'u': o.date.strftime("%Y-%m-%dT%I:%M:%SZ"), 'a':userUtil.getAvatar(o.instaright_account)}}))
                        return
		entries = SessionModel.gql('ORDER by date DESC').fetch(10)
		memcache.set(memcache_key, entries)
		if not entries:
			self.response.out.write('Nothing here')
		now = datetime.datetime.now().strftime("%Y-%m-%dT%H\:%i\:%sZ")
		if format is None or format == 'xml':
                        template_variables = { 'entries' : entries, 'dateupdated' : datetime.datetime.today()}
			path= os.path.join(os.path.dirname(__file__), 'templates/feed.html')
			self.response.headers['Content-Type'] = "application/atom+xml"
			self.response.out.write(template.render(path,template_variables))
			return
		if format == 'json':
			self.response.headers['Content-Type'] = "application/json"
                        self.response.out.write(simplejson.dumps(entries, default=lambda o: {'u':{'id':str(o.key()), 't':unicode(o.title), 'l': 'http://instaright.appspot.com/article/'+str(o.key()), 'd':o.domain, 'u': o.date.strftime("%Y-%m-%dT%I:%M:%SZ"), 'a':userUtil.getAvatar(o.instaright_account)}}))
			return

			
class ArticleHandler(webapp.RequestHandler):
	def get(self, location):
                try:
		        logging.info('fetching: %s' % location)
		        keyS=location
		        key = db.Key(keyS)
		        if not key:
		        	logging.info('not provided proper key entry : %s' % keyS)
		        	self.response.out.write('not provided  proper key entry %s' % keyS)
		        article = SessionModel.gql( 'WHERE __key__ = :1', key).get()
		        if not article:
		        	self.response.out.write('For key %s no article has been found' % keyS)
		        logging.info('redirecting to %s' % article.url)
		        template_variables={ 'url' : article.url }
		        path = os.path.join(os.path.dirname(__file__), 'templates/article.html')
		        self.response.out.write(template.render(path, template_variables))
                except:
                        e,e0 = sys.exc_info()[0], sys.exc_info()[1]
                        logging.error('handled error : %s, %s ' %( e, e0 ))
		        self.redirect('/')

class BlogLoader(webapp.RequestHandler):
	def get(self):
		template_variables=[]
		path = os.path.join(os.path.dirname(__file__), 'templates/blog.html')
		self.response.out.write(template.render(path, template_variables))

		
application = webapp.WSGIApplication(
                                     [
                                     	('/article/(.*)', ArticleHandler),
                                     	#('/feed', AtomGenerator)
                                     	('/feed', FeedGenerator),
                                     	('/blog', BlogLoader)
                                     	#('/feed', FeedHandler)
				     ],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()

import logging
import datetime
import os
import sys
import time
import urllib

from google.appengine.ext import webapp
from google.appengine.api import memcache
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from models import SessionModel, Links
from users import UserUtil
from generic_handler import GenericWebHandler
from utils import LinkUtil
from link_utils import EncodeUtils, LinkUtils

sys.path.append(os.path.join(os.path.dirname(__file__),'lib'))
import simplejson

class FeedGenerator(webapp.RequestHandler):
	def get(self):
                memcache_key='feed_json_cache'
                cached_feed= memcache.get(memcache_key)
		format = self.request.get('format', None);
                cache_exp = datetime.datetime.now() + datetime.timedelta(minutes=5)
                cache_exp_ts = time.mktime(cache_exp.timetuple())
                userUtil = UserUtil()
                if format == 'json' and cached_feed:
			logging.info('getting json from cache')
			self.response.headers['Content-Type'] = "application/json"
#			messageAsJSON = [{'u':{'id':update.id, 't':update.title,'l':update.link,'d':update.domain,'u':update.updated}}]
                        self.response.out.write(simplejson.dumps(cached_feed, default=lambda o: {'u':{'id':str(o.key()), 't':unicode(o.title), 'l': 'http://www.instaright.com/article/'+str(o.key()), 'd':o.domain, 'u': int(time.mktime(o.date.timetuple())), 'a':userUtil.getAvatar(o.instaright_account),'ol':o.url, 'e': o.embeded, 'n': int(time.mktime(datetime.datetime.now().timetuple()))}}))
                        return
		entries = SessionModel.gql('ORDER by date DESC').fetch(10)
		memcache.set(memcache_key, entries, time = cache_exp_ts)
		if not entries:
			self.response.out.write('Nothing here')
		#now = datetime.datetime.now().strftime("%Y-%m-%dT%H\:%i\:%sZ")
		if format is None or format == 'xml':
                        template_variables = { 'entries' : entries, 'dateupdated' : datetime.datetime.today()}
			path= os.path.join(os.path.dirname(__file__), 'templates/feed.html')
			self.response.headers['Content-Type'] = "application/atom+xml"
			self.response.out.write(template.render(path,template_variables))
			return
		if format == 'json':
			self.response.headers['Content-Type'] = "application/json"
                        self.response.out.write(simplejson.dumps(entries, default=lambda o: {'u':{'id':str(o.key()), 't':unicode(o.title), 'l': 'http://www.instaright.com/article/'+str(o.key()), 'd':o.domain, 'u': int(time.mktime(o.date.timetuple())), 'a':userUtil.getAvatar(o.instaright_account),'ol':o.url, 'e': o.embeded, 'n': int(time.mktime(datetime.datetime.now().timetuple()))}}))
			return

			
class ArticleHandler(GenericWebHandler):
	def get(self, url_hash, title):
                try:
                        self.redirect_perm()
                        self.get_user()
                        url_hash = urllib.unquote(url_hash)
		        logging.info('url hash: %s' % url_hash)
                        logging.info('category screen_name %s' %self.screen_name)
			category=None
                        if self.avatar is None:
                                self.avatar='/static/images/noavatar.png'

                        sessionModel = SessionModel.gql('where url_encode26 = :1', url_hash).get()
                        if sessionModel is None:
                                logging.info('not article with hash %s ... redirecting' % url_hash)
                                self.redirect('/')
                                return
                        generated_title =  LinkUtils.make_title(sessionModel.title)
                        if title != generated_title:
                                self.redirect('/article/'+url_hash+'/'+generated_title)
                                return
                        instaright_link =  LinkUtils.generate_instaright_link(url_hash, generated_title)
                        links = Links.gql('where url_hash = :1', url_hash).get()
			userUtil = UserUtil()
                        if links is not None:
                                category = links.categories
                        sessionTitle = LinkUtil.generateUrlTitle(sessionModel.title)
                        template_variables = {'user':self.screen_name, 'logout_url':'/account/logout', 'avatar':self.avatar,'story_avatar': userUtil.getAvatar(sessionModel.instaright_account), 'story_user': sessionModel.instaright_account, 'domain': sessionModel.domain, 'category':category,'title':sessionModel.title, 'link': sessionModel.url, 'updated':sessionModel.date, 'id': str(sessionModel.key()), 'instaright_link': instaright_link}
		        path = os.path.join(os.path.dirname(__file__), 'templates/article.html')
                        self.response.headers["Content-Type"] = "text/html; charset=utf-8"
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

class SitemapHandler(webapp.RequestHandler):
        def get(self):
		template_variables=[]
                self.response.headers["Content-Type"] = "text/xml; charset=utf-8"
		path = os.path.join(os.path.dirname(__file__), 'templates/sitemap.xml')
		self.response.out.write(template.render(path, template_variables))

		
class ArticleEncodeCorrectHandler(webapp.RequestHandler):
	def get(self):
                e = EncodeUtils()
                query = SessionModel.all()
		query.filter("url_counter_id <= " ,6000)
		query.order("-url_counter_id")
		results=query.fetch(1000)
                logging.info("fetch %s " %query.count())
                for s in results:
                        cnt = s.url_counter_id
			encoded = e.encode(cnt)
                        enbased26 = e.enbase(encoded)
                        logging.info("cnt: %s => encoded: %s enbased %s (before %s)" % (str(s.url_counter_id), str(encoded), enbased26, s.url_encode26 ))
                        s.url_encode26 = enbased26
                        s.put()
		
application = webapp.WSGIApplication(
                                     [
                                     	('/article/(.*)/(.*)', ArticleHandler),
                                     	#('/feed', AtomGenerator)
                                     	('/feed', FeedGenerator),
                                     	('/blog', BlogLoader),
                                     	('/sitemap.xml', SitemapHandler)
                                     	#('/feed', FeedHandler)
				     ],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()

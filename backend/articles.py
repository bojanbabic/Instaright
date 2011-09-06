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
                        self.response.out.write(simplejson.dumps(cached_feed, default=lambda o: {'u':{'id':str(o.key()), 't':unicode(o.title), 'dd': LinkUtils.generate_domain_link(o.domain), 'd':o.domain, 'user': urllib.unquote(o.instaright_account), 'source': o.client, 'u': int(time.mktime(o.date.timetuple())), 'l':LinkUtils.generate_instaright_link(o.url_encode26,LinkUtils.make_title(o.title)),'a':userUtil.getAvatar(o.instaright_account),'ol':o.url, 'lc':LinkUtils.getLinkCategory(o), 'html_lc':LinkUtils.getLinkCategoryHTML(o), 'e': o.embeded, 'n': int(time.mktime(datetime.datetime.now().timetuple()))}}))
                        return
		entries = SessionModel.gql('ORDER by date DESC').fetch(10)
		memcache.set(memcache_key, entries, time = cache_exp_ts)
		if not entries:
			self.response.out.write('Nothing here')
		#now = datetime.datetime.now().strftime("%Y-%m-%dT%H\:%i\:%sZ")
		if format is None or format == 'xml':
                        updated_entries = [ (str(o.key()), unicode(o.title), LinkUtils.generate_domain_link(o.domain), LinkUtils.generate_instaright_link(o.url_encode26,LinkUtils.make_title(o.title)),userUtil.getAvatar(o.instaright_account), o.date ) for o in entries ]
                        template_variables = { 'entries' : updated_entries, 'dateupdated' : datetime.datetime.today()}
			path= os.path.join(os.path.dirname(__file__), 'templates/feed.html')
			self.response.headers['Content-Type'] = "application/atom+xml"
			self.response.out.write(template.render(path,template_variables))
			return
		if format == 'json':
			self.response.headers['Content-Type'] = "application/json"
                        self.response.out.write(simplejson.dumps(entries, default=lambda o: {'u':{'id':str(o.key()), 't':unicode(o.title), 'dd': LinkUtils.generate_domain_link(o.domain), 'd':o.domain, 'user': o.instaright_account, 'u': int(time.mktime(o.date.timetuple())), 'l':LinkUtils.generate_instaright_link(o.url_encode26,LinkUtils.make_title(o.title)), 'a':userUtil.getAvatar(o.instaright_account),'ol':o.url, 'source': o.client, 'e': o.embeded, 'lc':LinkUtils.getLinkCategory(o), 'html_lc':LinkUtils.getLinkCategoryHTML(o), 'n': int(time.mktime(datetime.datetime.now().timetuple()))}}))
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
                        template_variables = {'user':self.screen_name, 'logout_url':'/account/logout', 'avatar':self.avatar,'story_avatar': userUtil.getAvatar(sessionModel.instaright_account), 'story_user': sessionModel.instaright_account, 'domain': sessionModel.domain, 'title':sessionModel.title, 'link': sessionModel.url, 'updated':sessionModel.date, 'id': str(sessionModel.key()), 'instaright_link': instaright_link, 'category': LinkUtils.getLinkCategoryHTML(sessionModel), 'dd': LinkUtils.generate_domain_link(sessionModel.domain)}
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
                json = LinkUtil.getJsonFromApi('http://www.instaright.com/feed?format=json')
                if json is None:
                        logging.info('default view')
                        self.response.headers["Content-Type"] = "text/xml; charset=utf-8"
		        path = os.path.join(os.path.dirname(__file__), 'templates/sitemap.xml')
		        self.response.out.write(template.render(path, template_variables))
                else:
                        logging.info('dynamic view')
                        links = []
                        for j in json:
                                logging.info('json entry: %s' % j)
                                dd = j['u']['dd']
                                if dd is not None:
                                        links.append(dd)
                                l = j['u']['l']
                                if l is not None:
                                        links.append(l)
                                lc = j['u']['lc']
                                if lc is not None:
                                        llc = lc.split(',')
                                        for ll in llc:
                                                links.append('http://www.instaright.com/%s' % ll)
                        logging.info('list of links: %s ' % len(links))
                        template_variables = { 'links': links }
		        path = os.path.join(os.path.dirname(__file__), 'templates/sitemap_dyn.xml')
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

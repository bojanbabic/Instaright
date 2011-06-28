import os, urllib2, logging, sys, ConfigParser, urllib, simplejson
from google.appengine.ext import webapp, db
from google.appengine.api import memcache
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template
from google.appengine.api.labs import taskqueue

from models import Links, SessionModel, CategoryDomains
from utils import StatsUtil, LinkUtil, CategoriesUtil
from simplejson import JSONDecodeError

sys.path.append(os.path.join(os.path.dirname(__file__),'social'))
sys.path.append(os.path.join(os.path.dirname(__file__),'fetch'))
from link_info import LinkHandler
from google.appengine.api import urlfetch 
from google.appengine.api.urlfetch import DownloadError 

class LinkSortHandler(webapp.RequestHandler):
        def get(self):
                order = self.request.get('order',None)
                l = Links()
                self.response.headers["Content-Type"]='text/plain'
                logging.info('get links')
                if order and hasattr(l,order): 
                        if order == 'diggs':
                                links = Links.gql('ORDER by diggs desc' ).fetch(100)
                        elif order == 'redditups':
                                links = Links.gql('ORDER by redditups desc' ).fetch(100)
                        elif order == 'all_score':
                                links = Links.gql('ORDER by all_score desc' ).fetch(100)
                        elif order == 'influence_score':
                                links = Links.gql('ORDER by influence_score desc' ).fetch(100)
                        elif order == 'facebook_like':
                                links = Links.gql('ORDER by facebook_like desc' ).fetch(100)
                        elif order == 'instaright_count':
                                links = Links.gql('ORDER by instaright_count desc' ).fetch(100)
                        elif order == 'overall_score':
                                links = Links.gql('ORDER by overall_score desc' ).fetch(100)
                        elif order == 'redditdowns':
                                links = Links.gql('ORDER by redditdowns desc' ).fetch(100)
                        elif order == 'tweets':
                                links = Links.gql('ORDER by tweets desc' ).fetch(100)
                        elif order == 'delicious_count':
                                links = Links.gql('ORDER by delicious_count desc' ).fetch(100)
                        else:
                                links = Links.gql('ORDER by overall_score desc').fetch(100)
                else:
                        links = Links.gql('ORDER by date_added desc, overall_score desc').fetch(100)
                        logging.info('pre link count: %s' %len(links))
                        order = 'overall_score'
                urls = [ (l.url, str(getattr(l,order)), str(l.date_updated)) for l in links  if l.url != StatsUtil.getDomain(l.url)]
                logging.info('link count: %s' %len(urls))
                if order and hasattr(l,order): 
                        template_variables = {'links' : urls }
        	        path= os.path.join(os.path.dirname(__file__), 'templates/top_links.html')
                        self.response.headers["Content-type"] = "text/html"
        	        self.response.out.write(template.render(path,template_variables))

class LinkTransformHandler(webapp.RequestHandler):
        def post(self):
                k=self.request.get('key',None)
                if k is None:
                        logging.info('error key has not been specified')
                        return
                key=db.Key(k)
                if key is None:
                        logging.info('error not valid key')
                        return
                s = SessionModel.gql('WHERE __key__ = :1', key).get()
                logging.info('feedproxt url %s' % unicode(s.url))
                util = LinkUtil()
                url = util.getFeedOriginalUrl(s.url)
                if url is None:
                        logging.info('could not fetch original url. skipping.')
                        return
                logging.info('original url %s' % url)
                domain = StatsUtil.getDomain(url)
                s.domain = domain
                s.feed_url=s.url
                s.url=url
                s.put()
                util.updateStats(s)
                

class ShortLinkHandler(webapp.RequestHandler):
        def post(self):
                k = self.request.get('key')
                key = db.Key(k)
                s = SessionModel.gql('WHERE __key__ = :1', key).get()
                util = LinkUtil()
                long_url=util.getShortOriginalUrl(s.url)
                if long_url is None:
                        logging.info('could not retrieve long link.skipping')
                        return
                logging.info('expanded url: %s' % long_url)
                if long_url.startswith('itms://'):
                        logging.info('Skipping itunes item: %s' % long_url)
                        return
                domain = StatsUtil.getDomain(long_url)
                s.short_url = s.url
                s.url = long_url
                s.domain = domain
                s.put()
                util.updateStats(s)

class LinkDomainCategoriesBatch(webapp.RequestHandler):
	def post(self):
		domain = self.request.get('domain',None)
		if domain is None:
			logging.info('no domain in request')
		logging.info('fetching categories for domain %s' % domain)
		memcache_key='domain_lookup_%s' % domain
                logging.info('checking cache for key %s' %memcache_key)
		if memcache.get(memcache_key) is None:
			logging.info('domain already processed skipping. key %s expires %s' % (memcache_key, memcache.get(memcache_key)))
			return
		else:
                        next_week=datetime.datetime.now().date() + datetime.timedelta(days=2)
                        next_week_ts=time.mktime(next_week.timetuple())
			memcache.set(memcache_key,1,time=next_week_ts)
		sessions = SessionModel.gql('WHERE  domain = :1', domain).fetch(1000)
		for s in sessions:
			logging.info('task: determine categories for url %s ( domain: %s)' % (s.url, domain))
			taskqueue.add(queue_name='category-queue', url='/link/category/task', params={'url':s.url, 'domain':domain})

class LinkDomainCategoriesTask(webapp.RequestHandler):
	def post(self):
		url = self.request.get('url', None)
		domain = self.request.get('domain', None)
		if url is None:
			logging.info('no url giving up')
			return
                if domain is None:
                        logging.info('no domain provided. giving up')
                        return
		link = None
		try:
			link = Links.gql('WHERE url = :1' , url).get()
		except:
			logging.info('error while fetching url from db')
		if link is None:
			link= Links()
		if link.categories is None:
			lh = LinkHandler()
			link=lh.delicious_data(url)	
			if link is None or link.categories is None:
				logging.info('no categories for link %s' % url)
				return
                CategoriesUtil.processDomainCategories(link.categories, domain)
                
class ProcessCategoriesHandler(webapp.RequestHandler):
        def post(self):
                categories = self.request.get('categories',None)
                domain = self.request.get('domain',None)
                if categories is None:
                        logging.info('no categories in request. skipping..')

                if domain is None:
                        logging.info('no domain is request. skipping...')
                CategoriesUtil.processDomainCategories(categories, domain)
class LinkRecommendationTask(webapp.RequestHandler):
        def __init__(self):
                conf = ConfigParser.ConfigParser()
		conf.read(os.path.split(os.path.realpath(__file__))[0]+'/properties/general.ini')
                self.z_key=conf.get('zemanta', 'key')
        def post(self):
                url=self.request.get('url',None)
                if url is None:
                        logging.info('no url no recommendations')
                        return
                url_hash = Utils.getUrlHash(url)
                l = Links.gql('WHERE url = :1' , url).get()
                if l is None:
                        logging.info('no link saved with url %s' % url)
                        l = Links()
                        l.url  = url
                        l.put()
                api_call= 'http://api.zemanta.com/services/rest/0.0/'
                args ={'method': 'zemanta.suggest',
                               'api_key': self.z_key,
                               'text': url,
                               'return_categories': 'dmoz',
                               'format': 'json'}
                args_enc = urllib.urlencode(args)
                json= None
                try:
                        result = urlfetch.fetch(url=api_call, payload=args_enc,method = urlfetch.POST, headers={'Content-Type': 'application/x-www-form-urlencoded'})
                        json = simplejson.loads(result.content)
                except JSONDecodeError,DownloadError:
                        logging.info('bad json data from zemanta: %s' % data)

                if json is None or json['status'] != 'ok':
                        logging.info('error while fetching recommendations')
                        return
                articles = json['articles']
                categories = json['categories']
                #relevant_articles = [ (c["title"], c["url"]) for c in articles if c["confidence"] > 0.01 ]
                relevant_articles = [ (c["title"], c["url"]) for c in articles ]
                l.recommendation=str(simplejson.dumps(relevant_articles[0:4]))
                l.put()
                logging.info('link updated: %s' % l.to_xml())

class LinkRecommendationHandler(webapp.RequestHandler):
        def get(self):
                url=self.request.get('url', None)
                if url is None:
                        logging.info('no url cant provide rcmds')
                        return
                link=Links.gql('WHERE url = :1' , url).get()
                self.response.headers['Content-Type']="application/json"
                if link is None:
                        logging.info('unexisting link , no recommendations')
                        self.response.out.write("{}")
                        return
                if link.recommendation is None:
                        logging.info('no recommendations started new job')
                        taskqueue.add(url='/link/recommendation/task', queue_name='link-rcmd-queue', params={'url':url })
                        self.response.out.write("{}")
                else:
                        logging.info(' transforming %s to json output ' % link.recommendation)
                        self.response.out.write("{}")
                        #self.response.out.write(simplejson.dumps(link.recommendation, default = lambda l: {'title': l.0, 'url': l.1}))

def main():
        run_wsgi_app(application)

application=webapp.WSGIApplication(
                [
                        ('/link/stats',LinkSortHandler),
                        ('/link/category/task',LinkDomainCategoriesTask),
                        ('/link/recommendation/task',LinkRecommendationTask),
                        ('/link/recommendation',LinkRecommendationHandler),
                        ('/link/category/task/batch',LinkDomainCategoriesBatch),
                        ('/link/transform/feed',LinkTransformHandler),
                        ('/link/transform/short',ShortLinkHandler),
                        ('/domain/categories',ProcessCategoriesHandler),
                        ],debug=True
                )

if __name__ == "__main__":
        main()

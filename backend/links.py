import os
import time
import datetime
import logging
import sys
import ConfigParser
import urllib
import simplejson
import itertools
from google.appengine.ext import webapp, db
from google.appengine.api import memcache
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template
from google.appengine.api.labs import taskqueue
from google.appengine.api import datastore_errors
from google.appengine.runtime import apiproxy_errors

from models import Links, SessionModel, UserSessionFE

from utils.general import Cast
from utils.category import CategoryUtil
from utils.link import LinkUtils
from utils.handler import RequestUtils
from utils.user import UserUtils

sys.path.append(os.path.join(os.path.dirname(__file__),'social'))
sys.path.append(os.path.join(os.path.dirname(__file__),'fetch'))
from link_info import LinkHandler
from google.appengine.api import urlfetch 

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
                urls = [ (l.url, str(getattr(l,order)), str(l.date_updated)) for l in links  if l.url != RequestUtils.getDomain(l.url)]
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
                util = LinkUtils()
                url = util.getFeedOriginalUrl(s.url)
                if url is None:
                        logging.info('could not fetch original url. skipping.')
                        return
                logging.info('original url %s' % url)
                domain = RequestUtils.getDomain(url)
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
                util = LinkUtils()
                long_url=util.getShortOriginalUrl(s.url)
                if long_url is None:
                        logging.info('could not retrieve long link.skipping')
                        return
                logging.info('expanded url: %s' % long_url)
                if long_url.startswith('itms://'):
                        logging.info('Skipping itunes item: %s' % long_url)
                        return
                domain = RequestUtils.getDomain(long_url)
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
                CategoryUtil.processDomainCategories(link.categories, domain)
                
class ProcessCategoriesHandler(webapp.RequestHandler):
        def post(self):
                categories = self.request.get('categories',None)
                domain = self.request.get('domain',None)
                if categories is None:
                        logging.info('no categories in request. skipping..')

                if domain is None:
                        logging.info('no domain is request. skipping...')
                CategoryUtil.processDomainCategories(categories, domain)
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
		url = url.encode('utf-8')
                logging.info('getting url hash %s' %url)
                url_hash = LinkUtils.getUrlHash(url)
                if url_hash is None:
                        logging.error("can't determing url hash %s" % url)
                        return
                try:
                        l = Links.gql('WHERE url_hash = :1' , url_hash).get()
                        if l is None:
                                l = Links.gql('WHERE url = :1' , url).get()
                except:
                        l = None
                if l is None:
                        logging.info('no link saved with url %s' % url)
                        l = Links()
                        l.url  = url
                        l.url_hash = url_hash
                        l.put()
                api_call= 'http://api.zemanta.com/services/rest/0.0/'
                args ={'method': 'zemanta.suggest',
                               'api_key': self.z_key,
                               'text': url,
                               'return_categories': 'dmoz',
                               'format': 'json'}
                args_enc = urllib.urlencode(args)
                json= None
                result=None
                try:
                        result = urlfetch.fetch(url=api_call, payload=args_enc,method = urlfetch.POST, headers={'Content-Type': 'application/x-www-form-urlencoded'})
                        json = simplejson.loads(result.content)
                except:
                        logging.info('bad json data from zemanta: %s' % result)

                if json is None or json['status'] != 'ok':
                        logging.info('error while fetching recommendations')
                        return
                articles = json['articles']
                #TODO apply DMOZ categories
                categories = json['categories']
                #relevant_articles = [ (c["title"], c["url"]) for c in articles if c["confidence"] > 0.01 ]
                relevant_articles = [ (c["title"], c["url"]) for c in articles ]
                l.recommendation=str(simplejson.dumps(relevant_articles[0:4]))
                if l.url_hash is None:
                        l.url_hash = url_hash
                l.put()

class LinkRecommendationHandler(webapp.RequestHandler):
        def get(self):
                url_hash=self.request.get('url_hash', None)
                if url_hash is None:
                        logging.info('no url cant provide rcmds')
                        return
                link=Links.gql('WHERE url_hash = :1' , url_hash).get()
                self.response.headers['Content-Type']="application/json"
                if link is None:
                        logging.info('unexisting link_hash %s, no recommendations' % url_hash)
                        self.response.out.write("{}")
                        return
                if link.recommendation is None:
                        logging.info('no recommendations started new job')
                        taskqueue.add(url='/link/recommendation/task', queue_name='default', params={'url_hash':url_hash })
                        self.response.out.write("{}")
                else:
                        logging.info(' transforming %s to json output ' % link.recommendation)
                        #self.response.out.write(link.recommendation)
                        self.response.out.write(simplejson.dumps(link.recommendation, default = lambda l: {'title': l[0], 'url': l[1]}))

class LinkUserHandler(webapp.RequestHandler):
        def __init__(self):
                conf = ConfigParser.ConfigParser()
		conf.read(os.path.split(os.path.realpath(__file__))[0]+'/properties/users.ini')
                self.link_batch=int(conf.get('dashboard', 'show_links'))
        def get(self):
                logging.info('fetching more user links ...')
                cookie = self.request.get('cookie', None)
                offset = Cast.toInt(self.request.get('offset', None), 0)
                logging.info('row offset %s' % offset)
                offset = offset * self.link_batch
                ud = UserUtils.getUserDetailsFromCookie(cookie)
                sessions = SessionModel.gql('WHERE instaright_account =  :1 ORDER by date desc ', ud.instaright_account ).fetch(20,offset)
                if sessions is None or len(sessions) == 0:
                        self.response.headers["Content-type"] = "application/json"
                        self.response.out.write('{}')
                        return
                d = {}
                for d_te, j in itertools.groupby(sessions, key= lambda s: s.date.date()):
                        ss = [ {'t':ss.title,'l':ss.url,'d':ss.domain,'h':ss.url_hash} for ss in list(j) ]
                        d[str(d_te)] = ss
                logging.info('giving more links %s' % str(d))
                self.response.headers["Content-type"] = "application/json"
                self.response.out.write(simplejson.dumps(d))




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
                        ('/link/user',LinkUserHandler),
                        ('/domain/categories',ProcessCategoriesHandler),
                        ],debug=True
                )


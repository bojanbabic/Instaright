import os, urllib2, logging, ConfigParser, sys, datetime
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template

from models import Links, SessionModel, LinkCategory
from utils import StatsUtil, LinkUtil, Cast, CategoriesUtil
from generic_handler import GenericWebHandler
from main import UserMessager

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
                logging.info('feedproxt url %s' % str(s.url))
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

                
class LinkCategoryHandler(webapp.RequestHandler):
        def __init__(self):
		config=ConfigParser.ConfigParser()
		config.read(os.path.split(os.path.realpath(__file__))[0]+'/properties/general.ini')
		self.alchemy_key=config.get('social', 'alchemy_api_key')
        def post(self):
                url=self.request.get('url',None)
                if url is None:
                        logging.info('no link in request. skipping')

                category_api='http://access.alchemyapi.com/calls/url/URLGetCategory?apikey=%s&url=%s&outputMode=json' %(self.alchemy_key, urllib2.quote(url.encode('utf-8')))
                logging.info('trying to fetch shared count info %s' %category_api)
                link=None
                languge=None
                category=None

		try:
                	link = Links.gql('WHERE url = :1', url).get()
		except BadValueError:
			logging.info('url property too long')
                if link is None:
                        link = Links()
                else:
                        link.date_updated = datetime.datetime.now().date()
                json = LinkUtil.getJsonFromApi(category_api)
                if json is None:
                        logging.info('alchemy api returned no category.skipping')
                        return
                try:
                    language=json['language']
                    category=json['category']
                    score=Cast.toFloat(json['score'],0)
                    if score is not None and score > 0.5 and category is not None:
                            logging.info('category %s score %s' %(category, score))
                            cats=category.split("_")
                            if cats is None:
                                    logging.info('no categories. exit')
                                    return
                            for c in cats:
                                existingLinkCat = LinkCategory.gql('WHERE url = :1 and category = :2', url, c).get()
                                if existingLinkCat is not None:
                                        existingLinkCat.updated=datetime.datetime.now()
                                        existingLinkCat.put()
                                        logging.info('updated exisitng url(%s) category(%s) update time %s' % (url, c, existingLinkCat.updated))
                                else:
                                        logging.info('new pair: url%s) category(%s) ' % (url, c))
                                        linkCategory=LinkCategory()
                                        linkCategory.url=url
                                        linkCategory.category=c
                                        linkCategory.put()
                    if language is not None:
                            link.language = language
                            link.url=url
                            link.put()
                except KeyError:
                    e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                    logging.info('key error [[%s, %s]] in %s' %(e0, e1, json))

class LinkCategoryDeliciousHandler(webapp.RequestHandler):
        def post(self):
                category=self.request.get('category',None)
                url=self.request.get('url',None)
                if category is None:
                        logging.info('no category skipping')
                        return
                if url is None:
                        logging.info('no url skipping')
                        return
                logging.info('processing categories %s for url %s' %(category, url))
                CategoriesUtil.processLinkCategoriesFromJson(category, url)

class CategoryHandler(GenericWebHandler):
        def get(self,category):
                self.redirect_perm()
                self.get_user()
                logging.info('category screen_name %s' %self.screen_name)
                if self.avatar is None:
                        self.avatar='/static/images/noavatar.png'

		userMessager = UserMessager(str(self.user_uuid))
		channel_id = userMessager.create_channel()

		template_variables = []
                template_variables = {'user':self.screen_name, 'logout_url':'/account/logout', 'avatar':self.avatar,'channel_id':channel_id,'category':category}
		path= os.path.join(os.path.dirname(__file__), 'templates/category.html')
                self.response.headers["Content-Type"] = "text/html; charset=utf-8"
		self.response.out.write(template.render(path,template_variables))


def main():
        run_wsgi_app(application)

application=webapp.WSGIApplication(
                [
                        ('/link/stats',LinkSortHandler),
                        ('/link/transform/feed',LinkTransformHandler),
                        ('/link/transform/short',ShortLinkHandler),
                        ('/link/category',LinkCategoryHandler),
                        ('/link/category/delicious',LinkCategoryDeliciousHandler),
                        ('/category/(.*)',CategoryHandler),
                        ],debug=True
                )

if __name__ == "__main__":
        main()

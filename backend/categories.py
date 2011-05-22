import os, urllib2, logging, ConfigParser, sys, os, datetime
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template
from google.appengine.api.labs import taskqueue

from models import Links, SessionModel, LinkCategory
from main import BroadcastMessage
from utils import StatsUtil, LinkUtil, Cast, CategoriesUtil
from users import UserUtil
from generic_handler import GenericWebHandler
from main import UserMessager
from google.appengine.ext.db import BadValueError

sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
import simplejson

class CategoryDetailsUpdate(webapp.RequestHandler):
        def get(self):
                allData=LinkCategory.getAll()
                all_categories= [ c.category for c in allData if c is not None ]
                uniq_categories = set(all_categories)
                for c in uniq_categories:
                        logging.info('updates for category %s' % c)
                        lc=LinkCategory.gql('WHERE category = :1 order by updated desc', c).fetch(50)
                        for l in lc:
                                if hasattr(l,'model_details') and l.model_details is not None:
                                        #logging.info('url %s already has details, skipping update' %l.url)
                                        continue
                                logging.info('updating url details %s ' %l.url)
                                s=SessionModel.gql('WHERE url = :1', l.url).get()
                                if s is None:
                                        logging.info('no session model for url %s trying feed url' %l.url)
                                s=SessionModel.gql('WHERE feed_url = :1', l.url).get()
                                if s is None:
                                        logging.info('no session model for url %s trying shprt url' %l.url)
                                s=SessionModel.gql('WHERE feed_url = :1', l.url).get()
                                if s is None:
                                        logging.info('ERROR: no session model url for %s' % l.url)
                                        continue
                                l.model_details=s.key()
                                l.put()


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
                key=self.request.get('session_key', None)
                if url is None:
                        logging.info('no link in request. skipping')
                        return
                if id is None:
                        logging.info('link inconsistency detected. skipping.')
                        return
                modelKey = db.Key(key)
                model = SessionModel.gql('WHERE __key__ = :1', modelKey).get()
                if model is None:
                        logging.error('no session model for key %s ' %str(modelKey))
                        return

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
                                taskqueue.add(queue_name='category-stream-queue', url='/category/stream', params={'model_key': str(model.key()), 'category':c, 'url': url})
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
                                        linkCategory.model_details=model.key()
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

class CategoryFeedHandler(webapp.RequestHandler):
        def get(self, category):
                format=self.request.get('out',None)
                if category is None or category == 0:
                        logging.info('not category in request. return empty')
                        return
                if format == 'json':
                        logging.info('catefory %s json feed' % category)
                        userUtil = UserUtil()
                        allentries = LinkCategory.gql('WHERE category = :1 order by updated desc', category).fetch(10)
                        entries= [ e for e in allentries if hasattr(e,'model_details') and e.model_details is not None]
			self.response.headers['Content-Type'] = "application/json"
                        self.response.out.write(simplejson.dumps(entries, default=lambda o: {'u':{'id':str(o.model_details.key()), 't':unicode(o.model_details.title), 'l': 'http://instaright.appspot.com/article/'+str(o.model_details.key()), 'd':o.model_details.domain, 'u': o.updated.strftime("%Y-%m-%dT%I:%M:%SZ"), 'a':userUtil.getAvatar(o.model_details.instaright_account),'ol':o.url}}))
			return
                self.reponse.headers['Content-Type'] = "application/json"
                self.response.out.write("[{}]")

class CategoryHandler(GenericWebHandler):
        def get(self,category):
                logging.info('category handler ')
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

class CategoryStreamHandler(webapp.RequestHandler):
        def post(self):
                category=self.request.get('category', None)
                model_key=self.request.get('model_key', None)
                url=self.request.get('url', None)
                userUtil=UserUtil()
                if category is None or len(category) == 0:
                        logging.info('no category in request. skipping ...')
                        return
                if url is None:
                        logging.info('no url in request. skipping ...')
                        return
                key=db.Key(model_key)
                model=SessionModel.gql('WHERE __key__ = :1' , key).get()
                category_path='/category/%s' %category
		broadcaster = BroadcastMessage()
                        
                messageAsJSON = [{'u':{'id':str(model.key()), 't':unicode(model.title),'l':model.url,'d':model.domain,'u': model.date.strftime("%Y-%m-%dT%I:%M:%SZ"), 'a':userUtil.getAvatar(model.instaright_account),'ol':model.url,'c':category}}]
                logging.info('sending message %s for users on path %s' % (messageAsJSON, category_path))
                broadcaster.send_message(messageAsJSON,category_path)

def main():
        run_wsgi_app(application)

application=webapp.WSGIApplication(
                [
                        ('/link/stats',LinkSortHandler),
                        ('/link/transform/feed',LinkTransformHandler),
                        ('/link/transform/short',ShortLinkHandler),
                        ('/link/category',LinkCategoryHandler),
                        ('/link/category/delicious',LinkCategoryDeliciousHandler),
                        ('/category/stream',CategoryStreamHandler),
                        ('/category/(.*)/feed',CategoryFeedHandler),
                        ('/category/model/update',CategoryDetailsUpdate),
                        ('/category/(.*)',CategoryHandler),
                        ],debug=True
                )

if __name__ == "__main__":
        main()

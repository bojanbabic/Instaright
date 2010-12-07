import os, urllib2, logging
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template

from models import Links, SessionModel
from utils import StatsUtil, LinkUtil

class LinkSortHandler(webapp.RequestHandler):
        def get(self):
                order = self.request.get('order',None)
                l = Links()
                self.response.headers["Content-Type"]='text/plain'
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
                        links = Links.gql('ORDER by overall_score desc').fetch(100)
                        order = 'overall_score'
                urls = [ (l.url, str(getattr(l,order)), str(l.date_updated)) for l in links  if l.url != StatsUtil.getDomain(l.url)]
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
                domain = StatsUtil.getDomain(long_url)
                s.short_url = s.url
                s.url = long_url
                s.domain = domain
                s.put()
                util.updateStats(s)
def main():
        run_wsgi_app(application)

application=webapp.WSGIApplication(
                [
                        ('/link/stats',LinkSortHandler),
                        ('/link/transform/feed',LinkTransformHandler),
                        ('/link/transform/short',ShortLinkHandler),
                        ],debug=True
                )

if __name__ == "__main__":
        main()

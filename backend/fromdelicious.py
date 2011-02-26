import datetime, time, urllib, logging, simplejson, os, BeautifulSoup, sys
from google.appengine.ext import webapp
from google.appengine.api import urlfetch
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api.labs import taskqueue
from google.appengine.ext.webapp import template
from pydelicious import DeliciousAPI


from models import UserDetails, SessionModel, UserStats

class DeliciousImportHandler(webapp.RequestHandler):
        def get(self):
                a = DeliciousAPI('ybabun', 'ybab00n')
                posts = a.posts_all()
                for p in posts:
                        logging.info('post: %s' %p)
                
                

app = webapp.WSGIApplication([
                                ('/tools/delicious', DeliciousImportHandler),
                                        ], debug =True)
def main():
        run_wsgi_app(app)

if __name__ == "__main__":
        main()


import datetime, time, urllib, logging, simplejson, os, BeautifulSoup, sys
from google.appengine.ext import webapp
from google.appengine.api import urlfetch
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api.labs import taskqueue
from google.appengine.ext.webapp import template

from models import UserDetails, SessionModel, UserStats, UserBadge
from utils import BadgeUtil

class TopUserHandler(webapp.RequestHandler):
        def get(self, stat_range):
                        format=self.request.get('format',None)
class BadgeStatsHandler(webapp.RequestHandler):
        def get(self):
                date_ = self.request.get('date', None)
                if date_:
                        date = datetime.datetime.strptime(date_, '%Y-%m-%d')
                else:   
                        date = datetime.datetime.now() - datetime.timedelta(days=1)
                stats = UserBadges.gql('WHERE date = :1 ', date).fetch(1000)
                if not stats:
                        self.response.out.write('no badges found for date %s Retreived no data' % date_)
                        return
                self.response.headers["Content-type"] = "application/json"
                self.response.out.write(simplejson.dumps(stats, default=lambda s: {'u':{'account':s.user, 'cout': s.badge}}))

app = webapp.WSGIApplication([
                                ('/badges/stats/top/(.*)', TopBadgeHandler),
                                ('/badges/stats/(.*)', BadgeStatsHandler),
                                        ], debug =True)
def main():
        run_wsgi_app(app)

if __name__ == "__main__":
        main()


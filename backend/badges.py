import datetime, time, urllib, logging, simplejson, os, sys
from google.appengine.ext import webapp
from google.appengine.api import urlfetch
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api.labs import taskqueue
from google.appengine.ext.webapp import template

from models import UserDetails, SessionModel, UserStats, UserBadge
from utils import BadgeUtil

class TopBadgeHandler(webapp.RequestHandler):
        def get(self, stat_range):
                        format=self.request.get('format',None)
class BadgeStatsHandler(webapp.RequestHandler):
        def get(self, _date):
                dt = datetime.datetime.strptime(_date, '%Y-%m-%d').date()
                if dt is None:
                        dt = dateime.datetime.now().date() 
                logging.info('checking badges for date: %s' % str(dt) )
                stats = UserBadge.gql('WHERE date = :1 ', dt).fetch(1000)
                if not stats:
                        self.response.out.write('no badges found for date %s Retreived no data' % _date)
                        return
                badges = [ (s.user, s.badge) for s in stats ]

                template_variables = {'badges' : badges }
        	path= os.path.join(os.path.dirname(__file__), 'templates/badges.html')
                self.response.headers["Content-type"] = "text/html"
        	self.response.out.write(template.render(path,template_variables))

app = webapp.WSGIApplication([
                                ('/badges/stats/top/(.*)', TopBadgeHandler),
                                ('/badges/stats/(.*)', BadgeStatsHandler),
                                        ], debug =True)
def main():
        run_wsgi_app(app)

if __name__ == "__main__":
        main()


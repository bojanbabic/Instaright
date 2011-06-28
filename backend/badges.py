import datetime
import logging
import os
from google.appengine.ext import webapp
from google.appengine.api import memcache
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template

from models import UserBadge, Badges, UserDetails


class BadgeStatsHandler(webapp.RequestHandler):
        def get(self, _date):
                dt = datetime.datetime.strptime(_date, '%Y-%m-%d').date()
                if dt is None:
                        dt = datetime.datetime.now().date()
                logging.info('checking badges for date: %s' % str(dt))
                stats = UserBadge.gql('WHERE date = :1 ', dt).fetch(1000)
                if not stats:
                        self.response.out.write('no badges found for date %s Retreived no data' % _date)
                        return
                badges = [(s.user, s.badge) for s in stats]

                template_variables = {'badges': badges}
        	path= os.path.join(os.path.dirname(__file__), 'templates/badges.html')
                self.response.headers["Content-type"] = "text/html"
        	self.response.out.write(template.render(path,template_variables))


class UpdateBadgeHandler(webapp.RequestHandler):
        def get(self):
                memcache_key = 'update_user_badges'
                cached_badges = memcache.get(memcache_key)
                #if cached_badges is not None:
                #        logging.info('badge from cache')
                ##        u_badges = cached_badges
                #else:
                user_badges = UserBadge.all()
                u_badges = [ u for u in user_badges if u.badge_property is None ]
                memcache.set(memcache_key, u_badges)

                logging.info('total badges %s' % len(u_badges))
                for ub in u_badges:
                        if ub.badge_property is not None:
                                logging.info('skipping already defined badge_p')
                                continue
                        b = Badges.gql('WHERE badge_label = :1 ', ub.badge).get()
                        if b is None:
                                b = Badges()
                                b.badge_label = ub.badge
                                b.badge_icon = ub.badge
                                b.put()
                        ud = UserDetails.gql('WHERE instaright_account = :1' , ub.user).get()
                        if ud is None:
                                ud = UserDetails()
                                ud.instaright_account = ub.user
                                ud.put()
                        ub.badge_property=b.key()
                        ub.user_property = ud.key()
                        ub.put()


app = webapp.WSGIApplication([
                                ('/badges/stats/(.*)', BadgeStatsHandler),
                                ('/badges/update', UpdateBadgeHandler),
                                        ], debug =True)
def main():
        run_wsgi_app(app)

if __name__ == "__main__":
        main()

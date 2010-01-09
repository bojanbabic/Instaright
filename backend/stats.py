import sys, os, time, datetime, cgi, logging, gviz_api
#import multiprocessing

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import mail
from google.appengine.runtime import DeadlineExceededError
from urlparse import urlparse
from main import SessionModel
from cron import StatsModel, DailyDomainStats, WeeklyDomainStats, YearDomainStats
from google.appengine.ext.webapp import template

class VisualStats(webapp.RequestHandler):
	def get(self):
		template_variables=''
		logging.info('generating visual stats')
		path= os.path.join(os.path.dirname(__file__), 'templates/stats.html')
		self.response.out.write(template.render(path,template_variables))

application = webapp.WSGIApplication(
                                     [('/stats', VisualStats)],
					debug=True)
                                     

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()


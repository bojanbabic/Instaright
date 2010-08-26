import sys, os, time, datetime, cgi, logging, gviz_api
#import multiprocessing

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.runtime import DeadlineExceededError
from urlparse import urlparse
from main import SessionModel
from cron import StatsModel, DailyDomainStats, WeeklyDomainStats, YearDomainStats
from google.appengine.ext.webapp import template

class VisualStats(webapp.RequestHandler):
	def get(self):
		#dailyStats = [ '2010-01-14', '2010-01-13','2010-01-12' ]
		#weeklyStats = [ '2010-02-16','2010-02-02','2010-01-26', '2010-01-19', '2010-01-12', '2010-01-05','2009-12-29' ]
		dailyStats = self.latestDailyStats()
		weeklyStats = self.latestWeeklyStats()
		template_variables={'dailyStats':dailyStats, 'weeklyStats':weeklyStats}
		logging.info('generating visual stats')
		path= os.path.join(os.path.dirname(__file__), 'templates/stats.html')
		self.response.out.write(template.render(path,template_variables))
	def latestDailyStats(self):
		memcache_key = "daily_stats_dates"+str(datetime.date.today())
		logging.info('looking up for memcache key: %s' % memcache_key)
		if memcache.get(memcache_key):
			logging.info('key found in cache')
			return memcache.get(memcache_key)
		topDailyStat = DailyDomainStats.gql(' ORDER by date desc ').get()
		if topDailyStat:
			dateInStats = topDailyStat.date
		if not dateInStats:
			logging.info('can\'t figure out last succesful daily stats execution')
			return None
		numberOfStats = 5
		dayOffset = 1
		datesForDailyStats = []
		while numberOfStats > 0:
			logging.info('daily stats date : %s ' % dateInStats)
			datesForDailyStats.append(dateInStats)
			dateInStats = dateInStats - datetime.timedelta(days = 1)
			numberOfStats = numberOfStats - 1
		logging.info("daily stats dates %s" % datesForDailyStats)
		memcache.set(memcache_key, datesForDailyStats)
		return datesForDailyStats
	def latestWeeklyStats(self):
		memcache_key = "weekly_stats_dates"+str(datetime.date.today())
		logging.info('looking up for memcache key: %s' % memcache_key)
		if memcache.get(memcache_key):
			logging.info('key found in cache')
			return memcache.get(memcache_key)
		topWeeklyStat = WeeklyDomainStats.gql(' ORDER by date desc ').get()
		if topWeeklyStat:
			dateInStats = topWeeklyStat.date
		if not dateInStats:
			logging.info('can\'t figure out last succesful weekly stats execution')
			return None
		numberOfStats = 5
		dayOffset = 7
		datesForWeeklyStats = []
		while numberOfStats > 0:
			logging.info('weekly stats date : %s ' % dateInStats)
			datesForWeeklyStats.append(dateInStats)
			dateInStats = dateInStats - datetime.timedelta(days = 7)
			numberOfStats = numberOfStats - 1
		logging.info("weekly stats dates %s" % datesForWeeklyStats)
		memcache.set(memcache_key, datesForWeeklyStats)
		return datesForWeeklyStats

application = webapp.WSGIApplication(
                                     [('/stats', VisualStats)],
					debug=True)
                                     

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()


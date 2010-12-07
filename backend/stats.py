import sys, os, time, datetime, cgi, logging, gviz_api
#import multiprocessing

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.api.labs import taskqueue
from google.appengine.runtime import DeadlineExceededError
from urlparse import urlparse
from google.appengine.ext.webapp import template

from models import SessionModel, CityStats, CountryStats
from cron import StatsModel, DailyDomainStats, WeeklyDomainStats, YearDomainStats

class VisualStats(webapp.RequestHandler):
	def get(self):
		#dailyStats = [ '2010-01-14', '2010-01-13','2010-01-12' ]
		#weeklyStats = [ '2010-02-16','2010-02-02','2010-01-26', '2010-01-19', '2010-01-12', '2010-01-05','2009-12-29' ]
		dailyStats = self.latestDailyStats()
		weeklyStats = self.latestWeeklyStats()
		template_variables={'dailyStats':dailyStats, 'weeklyStats':weeklyStats, 'userStats':dailyStats}
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

class CityRedundantStats(webapp.RequestHandler):
        def get(self):
                allCities = CityStats.gql('order by count desc').fetch(5000)
                for c in allCities:
                        memcache_key='city_queue'+c.city+'_'+c.countryCode+str(datetime.datetime.now().date())
                        if memcache.get(memcache_key):
                                logging.info('processed city %s %s skipping' %( c.city, c.countryCode))
                                continue
                        logging.info('adding to queue %s %s' % (c.countryCode, c.city))
                        taskqueue.add(queue_name='redundant',url='/stats/city/redundant/task', params={'city':c.city, 'country':c.countryCode})
                        memcache.set(memcache_key, 1)
class CityRedundantTask(webapp.RequestHandler):
        def post(self):
                city=self.request.get('city',None)
                countryCode=self.request.get('country',None)
                memcache_key='reduncant_city'+city+'_'+countryCode+'_'+str(datetime.datetime.now().date())
                if memcache.get(memcache_key):
                        logging.info('already processed %s %s' %(city, countryCode))
                        return
                redundant=CityStats.gql('WHERE city = :1 and countryCode = :2', city, countryCode).fetch(1000)
                if len(redundant) == 1:
                        logging.info('no duplicates for %s %s' % (city, countryCode))
                        return
                logging.info('city: %s country: %s has duplidates: %s' %(city, countryCode, len(redundant)))
                pivot = max(redundant, key=redundant.count)	
                logging.info('max stats:%s' % pivot.count)
                redundant.remove(pivot)
                for cc in redundant:
                        pivot.count += cc.count
                        if cc.dateUpdated is not None and (pivot.dateUpdated is None or cc.dateUpdated > pivot.dateUpdated):
                                pivot.dateUpdated = cc.dateUpdated
                        cc.delete()
                pivot.put()
                memcache.set(memcache_key, '1')
                logging.info('new count %s' % pivot.count)
                
class CountryRedundantStats(webapp.RequestHandler):
        def get(self):
                allCountries = CountryStats.gql('order by count desc').fetch(5000)
                for c in allCountries:
                        memcache_key='city_queue'+'_'+c.countryCode+str(datetime.datetime.now().date())
                        if memcache.get(memcache_key):
                                logging.info('processed country %s skipping' % c.countryCode)
                                continue
                        logging.info('adding to queue %s' % c.countryCode)
                        taskqueue.add(queue_name='redundant',url='/stats/country/redundant/task', params={'country':c.countryCode})
                        memcache.set(memcache_key, 1)
class CountryRedundantTask(webapp.RequestHandler):
        def post(self):
                countryCode=self.request.get('country',None)
                memcache_key='reduncant_country'+'_'+countryCode+'_'+str(datetime.datetime.now().date())
                if memcache.get(memcache_key):
                        logging.info('already processed %s %s' %countryCode)
                        return
                redundant=CountryStats.gql('WHERE countryCode = :1', countryCode).fetch(1000)
                if len(redundant) == 1:
                        logging.info('no duplicates for %s ' % countryCode)
                        return
                logging.info('country: %s has duplidates: %s' %(countryCode, len(redundant)))
                pivot = max(redundant, key=redundant.count)	
                logging.info('max stats:%s' % pivot.count)
                redundant.remove(pivot)
                for c in redundant:
                        pivot.count += c.count
                        if c.dateUpdated is not None and (pivot.dateUpdated is None or c.dateUpdated > pivot.dateUpdated):
                                pivot.dateUpdated = c.dateUpdated
                        c.delete()
                pivot.put()
                memcache.set(memcache_key, '1')
                logging.info('new count %s' % pivot.count)
                

application = webapp.WSGIApplication(
                                     [
                                        ('/stats', VisualStats),
                                        ('/stats/city/redundant', CityRedundantStats),
                                        ('/stats/city/redundant/task', CityRedundantTask),
                                        ('/stats/country/redundant', CountryRedundantStats),
                                        ('/stats/country/redundant/task', CountryRedundantTask),
                                     ],
					debug=True)
                                     

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()


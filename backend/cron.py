import sys, os, time, datetime, cgi, logging
#import multiprocessing

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache
from google.appengine.runtime import DeadlineExceededError
from main import SessionModel
from google.appengine.ext.webapp import template
from utils import StatsUtil

class StatsModel(db.Model):
	totalNumber=db.IntegerProperty(default=0)
	totalDailyNumber=db.IntegerProperty(default=0)
	date=db.DateProperty(auto_now_add=True)

class DailyDomainStats(db.Model):
	domain=db.StringProperty()
	count=db.IntegerProperty()
	date=db.DateProperty(auto_now_add=True)
	def toxml(self):
		return "<domain>%s</domain><count>%s</count>" %(self.domain , self.count)

class WeeklyDomainStats(db.Model):
	domain=db.StringProperty()
	count=db.IntegerProperty()
	date=db.DateProperty(auto_now_add=True)
	def toxml(self):
		return "<domain>%s</domain><count>%s</count>" %(self.domain , self.count)

class YearDomainStats(db.Model):
	domain=db.StringProperty()
	count=db.IntegerProperty()
	date=db.DateProperty(auto_now_add=True)


class CronTask(webapp.RequestHandler):
	def get(self):
		logging.info('Cron task stats')
		statstype=self.request.get('type', None)
		targetDate=self.request.get('date', None)
		if statstype == "daily":
			self.dailyStats(targetDate)
		elif statstype == "weekly":
			self.weeklyStats(targetDate)
		elif statstype == "year":
			self.yearStats(targetDate)
		elif statstype == "count":
			self.countDailySessions(targetDate)
		else:
			self.response.out.write('Not yet implemented!')
	def post(self):
		logging.info('cron post call')
		statstype = self.request.get('type', None)
		targetDate = self.request.get('date', None)
		logging.info(' for parameters: %s %s' % (statstype, targetDate))
		if statstype == "daily":
			self.dailyStats(targetDate)
		elif statstype == "weekly":
			self.weeklyStats(targetDate)
		elif statstype == "year":
			self.yearStats(targetDate)
		else:
			self.response.out.write('Not yet implemented!')
	def countDailySessions(self, tDate):
		try:
			if tDate is None or tDate == 'None':
				today = datetime.date.today()
				logging.info('Started session count for %s' % today)
				targetDate=datetime.date.today() - datetime.timedelta(days=1)
			else:
				targetDate = datetime.datetime.strptime(tDate, "%Y-%m-%d").date()
			logging.info('targetDate: %s', targetDate)
			dailyData=SessionModel.getDailyStats(targetDate)
			#totalCount=SessionModel.countAll()
			stats=StatsModel()
			if dailyData:
				stats.totalDailyNumber=len(dailyData)
			stats.date=targetDate
			stats.put()
			logging.info('Link volume for %s : %s' % (tDate , stats.totalDailyNumber ))
		except:
			e = sys.exc_info()[1]
			logging.error('Error while running stats cron task. %s' % e)
			
	def dailyStats(self, tDate):
		try:
			if tDate is None or tDate == "None":
				targetDate = None
			else:
				targetDate = datetime.datetime.strptime(tDate, "%Y-%m-%d").date()
			allStats = SessionModel.getDailyStats(targetDate)
			logging.info('daily stats for %s ' % targetDate )
			if allStats:
				logging.info('retieved %s ' % len(allStats))
				self.calculateStatsPerDomain(allStats,'daily', targetDate)
			
		except:
			e = sys.exc_info()[1]
			logging.error('Error while running daily cron task. %s' % e)

	def weeklyStats(self, tDate):
		try:
			if tDate is None or tDate == "None":
				targetDate = None
			else:
				targetDate = datetime.datetime.strptime(tDate, "%Y-%m-%d").date()
			allWeeklyStats = SessionModel.getWeeklyStats(targetDate)
			logging.info('weekly stats for %s ' % targetDate )
			if allWeeklyStats:
				logging.info('retieved %s ' % len(allWeeklyStats))
				self.calculateStatsPerDomain(allWeeklyStats, 'weekly', targetDate)
		except:
			e0 = sys.exc_info()[0]
			e = sys.exc_info()[1]
			logging.error('Error while running weekly cron task. %s. More info %s' % (e, e0))

	def yearStats(self, tDate):
		try:
			if tDate is None or tDate == "None":
				targetDate = None
			else:
				targetDate = datetime.datetime.strptime(tDate, "%Y-%m-%d").date()
			allYearStats = SessionModel.getYearStats(targetDate)
			logging.info('yearly stats for %s ' % targetDate )
			if allYearStats:
				logging.info('retieved %s ' % len(allYearStats))
				self.calculateStatsPerDomain(allYearStats,'year', targetDate)
			
		except:
			e = sys.exc_info()[1]
			logging.error('Error while running weekly cron task. %s' % e)
	
	def calculateStatsPerDomain(self, data, period, target):
		if not data:
			return
		# take domain if exists
		if target:
			for_date = str(target)
		else:
			for_date = str(datetime.date.today())
		memcache_domains_key = "domains_"+period + for_date
		if memcache.get(memcache_domains_key):
			logging.info('getting domain list from cache')
			domains = memcache.get(memcache_domains_key)
		else:
			domains=[ record.domain for record in data if record.domain ]
			memcache.set(memcache_domains_key, domains)
		uniqdomains = set(domains)
		logging.info("total domains retrieved: %d", len(uniqdomains))
		for domain in uniqdomains:
			memcache_key = period+str(datetime.date.today())+domain
			try:
				if period == "daily":
					domainStat = DailyDomainStats()
				elif period == "weekly":
					domainStat = WeeklyDomainStats()
				elif period == "year":
					domainStat = YearDomainStats()
				if memcache.get(memcache_key):
					logging.info('found entry in cache. skipping %s' % domain)
					continue
				countfordomain=domains.count(domain)
				domainStat.domain=domain
				domainStat.count=countfordomain
				if target:
					domainStat.date=target
				domainStat.put()
				logging.info("stats for domain %s: %s" % (domain, countfordomain) )
				memcache.set(memcache_key, 'done')
			except DeadlineExceededError:
				logging.error("deadline error while proceeding stats for domain %s", domain)
			except:
				e= sys.exc_info()[1]
				logging.error('error calculating stats for domain %s . Error: %s' %(domain, e))
		logging.info('finished %s stats calculating for %s ' % ( period, target))
		
application = webapp.WSGIApplication(
                                     [('/cron', CronTask)],debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
	main()

import sys, os, time, datetime, cgi, logging
#import multiprocessing

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache
from google.appengine.runtime import DeadlineExceededError
from models import SessionModel
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
				users = [ d.instaright_account for d in dailyData if d.instaright_account is not None ]
				user_set = set(users)
				stats.totalUserNumber = len(user_set)
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
				targetDate = datetime.datetime.strptime(tDate, "%Y-%m-%d")
			allStats = SessionModel.getDailyStats(targetDate)
			logging.info('daily stats for %s ' % targetDate )
			if allStats:
				logging.info('retieved %s ' % len(allStats))
				self.calculateStatsPerDomain(allStats,'daily', targetDate)
			
		except:
			e0, e1 = sys.exc_info()[0], sys.exc_info()[1]
			logging.error('Error while running daily cron task. %s. More info %s' % (e0, e1))

	def weeklyStats(self, tDate):
		try:
			if tDate is None or tDate == "None":
				targetDate = None
			else:
				targetDate = datetime.datetime.strptime(tDate, "%Y-%m-%d")
			logging.info('target date %s' % targetDate)
			allWeeklyStats = SessionModel.getWeeklyStats(targetDate)
			logging.info('weekly stats for %s ' % targetDate )
			if allWeeklyStats:
				logging.info('retieved %s ' % len(allWeeklyStats))
				self.calculateStatsPerDomain(allWeeklyStats, 'weekly', targetDate)
		except:
			e0, e1 = sys.exc_info()[0], sys.exc_info()[1]
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
		                memcache_domains_key = "domains_year" + str(datetime.datetime.now().date())
        		        if memcache.get(memcache_domains_key):
                                        logging.info('year stats::geting domain list from cache')
        		        	allStats = memcache.get(memcache_domains_key)
        		        else:
			                allStats = [ (stat.domain, sum([ x.count for x in allYearStats if x.domain == stat.domain])) for stat in allYearStats if stat.domain ]
        		        	memcache.set(memcache_domains_key, allStats)
                                for s in allStats:
                                        domain = s[0]
                                        count = s[1]
			                memcache_year_key = 'year'+str(datetime.datetime.now().date())+domain
			        	if memcache.get(memcache_year_key):
			        		logging.info('found entry in cache. skipping %s' % domain)
			        		continue
                                        logging.info(' %s %s ' %(domain , count))
                                        ys = YearDomainStats()
                                        ys.domain = domain
                                        ys.count = count
                                        ys.put()
                                        memcache.set(memcache_year_key,count)
		except:
			e0, e1 = sys.exc_info()[0], sys.exc_info()[1]
			logging.error('Error while running weekly cron task. %s \n %s' %( e0, e1))
	
	def calculateStatsPerDomain(self, data, period, target):
		if not data:
			self.updateCacheEntries(period,target)
			return
		# take domain if exists
		if target:
			for_date = target.strftime("%Y-%m-%d")
		else:
			for_date = str(datetime.date.today())
		logging.info('calculating stats for date: %s' % for_date)
		memcache_domains_key = "domains_"+period + for_date
		if memcache.get(memcache_domains_key):
			logging.info('geting domain list from cache')
			domains = memcache.get(memcache_domains_key)
		else:
			domains=[ record.domain for record in data if record.domain ]
			memcache.set(memcache_domains_key, domains)
		uniqdomains = set(domains)
		logging.info("total domains retrieved: %d", len(uniqdomains))
		for domain in uniqdomains:
			memcache_key = period+str(datetime.date.today())+domain+'_'+for_date
			try:
				if period == "daily":
					domainStat = DailyDomainStats()
				elif period == "weekly":
					domainStat = WeeklyDomainStats()
				if memcache.get(memcache_key):
					logging.info('found entry in cache. skipping %s' % domain)
					continue
				countfordomain=domains.count(domain)
				domainStat.domain=domain
				domainStat.count=countfordomain
				if target:
					domainStat.date=target.date()
				domainStat.put()
				logging.info("stats for domain %s: %s" % (domain, countfordomain) )
				memcache.set(memcache_key, 'done')
			except DeadlineExceededError:
				logging.error("deadline error while proceeding stats for domain %s", domain)
			except:
				e= sys.exc_info()[1]
				logging.error('error calculating stats for domain %s . Error: %s' %(domain, e))
		logging.info('finished %s stats calculating for %s ' % ( period, target))
		# delete memcache keys that have been generated for stats during running of stats 
		daily_memcache_key = "daily_stats_dates"+str(datetime.date.today())
		if memcache.get(daily_memcache_key):
			logging.info('removing existing memcache entry: %s ' % daily_memcache_key)
			memcache.delete(daily_memcache_key)
		weekly_memcache_key = "weekly_stats_dates"+str(datetime.date.today())
		if memcache.get(weekly_memcache_key):
			logging.info('removing existing memcache entry: %s ' % weekly_memcache_key)
			memcache.delete(weekly_memcache_key)
	# 
application = webapp.WSGIApplication(
                                     [('/cron', CronTask)],
				     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
	main()

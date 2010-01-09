import sys, os, time, datetime, cgi, logging
#import multiprocessing

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import mail
from google.appengine.runtime import DeadlineExceededError
from urlparse import urlparse
from main import SessionModel

class StatsModel(db.Model):
	totalNumber=db.IntegerProperty()
	totalDailyNumber=db.IntegerProperty()
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
		statstype=cgi.escape(self.request.get('type'))
		if statstype == "daily":
			self.dailyStats()
		elif statstype == "weekly":
			self.weeklyStats()
		elif statstype == "year":
			self.yearStats()
	def dailyStats(self):
		try:
			today = datetime.date.today()
			logging.info('Started crontask for %s' % today)
			yesterday=datetime.date.today() - datetime.timedelta(days=1)
			logging.info('yesterday: %s',yesterday)
			todayData=SessionModel.gql('WHERE date = :1', yesterday)
			#todayData=SessionModel.gql('WHERE date = :1', datetime.date.today())
			totalCount=SessionModel.countAll()
			logging.info('total count: %d' % totalCount)
			logging.info('Gathered yesterday data : %d' % todayData.count())
			stats=StatsModel()
			stats.totalNumber=totalCount
			stats.totalDailyNumber=todayData.count()
			#stats.date=datetime.date.today()
			stats.put()
			# daily count stats
			# this will work for close to 500 domains - for success i'm not ready
			allStats = SessionModel.getDailyStats()
			if allStats:
				self.calculateStatsPerDomain(allStats,'daily')
			
		except:
			e = sys.exc_info()[1]
			logging.error('Error while running daily cron task. %s' % e)

	def weeklyStats(self):
		try:
			logging.info('Started weekly stats %s ' % datetime.date.today())
			allWeeklyStats = SessionModel.getWeeklyStats()
			self.calculateStatsPerDomain(allWeeklyStats, 'weekly')
			
		except:
			e = sys.exc_info()[1]
			logging.error('Error while running weekly cron task. %s' % e)

	def yearStats(self):
		try:
			logging.info('Started year stats %s ' % datetime.date.today())
			allYearStats = SessionModel.getYearStats()
			self.calculateStatsPerDomain(allYearStats,'year')
			
		except:
			e = sys.exc_info()[1]
			logging.error('Error while running weekly cron task. %s' % e)
	
	def calculateStatsPerDomain(self, data, period):
		
		if not data:
			return
		domains=[ StatsUtil.getDomain(record.url) for record in data ]
		uniqdomains = set(domains)
		logging.info("total domains retrieved: %d", len(uniqdomains))
		for domain in uniqdomains:
			try:
				logging.info("calculating stats for domain %s:", domain )
				if period == "daily":
					domainStat = DailyDomainStats()
				elif period == "weekly":
					domainStat = WeeklyDomainStats()
				elif period == "year":
					domainStat = YearDomainStats()
				countfordomain=domains.count(domain)
				domainStat.domain=domain
				domainStat.count=countfordomain
				domainStat.put()
			except DeadlineExceededError:
				logging.error("deadline error while proceeding stats for domain %s", domain)
				
			except:
				e= sys.exc_info()[1]
				logging.error('error calculating stats for domain %s', domain)
		

class StatsUtil(object):
	@staticmethod
	def getDomain(url):
		urlobject=urlparse(url)
		return urlobject.netloc
	
	def callResolverAPI(self, ip):
		apiCall="http://api.hostip.info/get_xml.php?ip="+ip
		req = urllib2.Request(apiCall)
		response = req.read()
		# TODO  parse xml 
		
		
			
		
application = webapp.WSGIApplication(
                                     [('/cron', CronTask)],debug=True)
                                     

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()


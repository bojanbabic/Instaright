import sys, os, time, datetime
import logging 
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

class DomainStats(db.Model):
	domain=db.StringProperty()
	count=db.IntegerProperty()
	date=db.DateProperty(auto_now_add=True)


class CronTask(webapp.RequestHandler):
	def get(self):
		try:
			logging.info('Started crontask for %s' % datetime.date.today())
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
			allStats = SessionModel.getAll()
			self.calculateStatsPerDomain(allStats)
			
		except:
			e = sys.exc_info()[1]
			logging.error('Error while running crontask.Error: %s' % e)
	def getAll(self):
		try:
			allData=SessionModel.all()
			stats=StatsModel()
			stats.totalNumber=allData.count()
			stats.totalDailyNumber=allData.count()
			stats.put()
		except:
			e = sys.exc_info()[1]
			logging.error('Error while running getALl %s' %e)
	def calculateStatsPerDomain(self, data):
		
		if not data:
			return
		domains=[ StatsUtil.getDomain(record.url) for record in data ]
		uniqdomains = set(domains)
		logging.info("total domains retrieved: %d", len(uniqdomains))
		for domain in uniqdomains:
			try:
				logging.info("calculating stats for domain %s:", domain)
				countfordomain=domains.count(domain)
				domainStat = DomainStats()
				domainStat.domain=domain
				domainStat.count=countfordomain
				domainStat.put()
			except DeadlineExceededError:
				logging.error("deadline error while proceeding stats for domain %s", domain)
				#sleep for 30 sec until system recovers
				time.sleep(30)
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


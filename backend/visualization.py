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

class VisualStats(webapp.RequestHandler):
	def get(self):
#		template_variables=''
#		logging.info('generating visual stats')
#		path= os.path.join(os.path.dirname(__file__), 'templates/stats.html')
#		self.response.out.write(template.render(path,template_variables))
		self.response.out.write("check 1 2 ")

class Visualization(webapp.RequestHandler):
	def get(self):
		statstype=cgi.escape(self.request.get('type'))
		if statstype == "dailyfeed":
			targetdate=cgi.escape(self.request.get('date'))
			self.dailyFeed(targetdate)
		elif statstype == "weeklyfeed":
			targetdate=cgi.escape(self.request.get('date'))
			self.weeklyFeed(targetdate)
	def dailyFeed(self,targetdate):
		try:
			if not targetdate:
				today = datetime.date.today()
				yesterday=datetime.date.today() - datetime.timedelta(days=1)
				targetdate=yesterday
			else:
				try:
					year=targetdate[:4]
					month=targetdate[5:7]
					day=targetdate[8:10]
					logging.info('year %s month %s day %s' %(year, month, day))
					#targetdate=datetime.date(year,month, day)
					targetdate=datetime.date(int(year),int(month), int(day))
				except:
					e = sys.exc_info()[1]
					logging.error('error formating date %s =>  %s' %(targetdate, e))
					targetdate=datetime.date.today() - datetime.timedelta(days=1)
					
			logging.info('Fetching stats for %s' % targetdate)
			dailyStats=DailyDomainStats.gql('WHERE date = :1 ORDER BY count DESC ', targetdate)
			datastore = []
			datastore = self.prepareforvisualize(dailyStats)
			
			# prepare for output 
			description ={"domain": ("string", "Domain"),
					"count":("number", "Total Links")}
			columnnames = [ "domain", "count" ]
			data_table = gviz_api.DataTable(description)
			data_table.LoadData(datastore)
			
			self.response.headers['Content-Type'] = 'text/plain'
			self.response.out.write(data_table.ToJSonResponse(columns_order=(columnnames)))
			
			
		except:
			e = sys.exc_info()[1]
			logging.error('Error while fetching daily feed %s' % e)

	def prepareforvisualize(self, stats):
		try:
			datastore = []
			for stat in stats:
				if stat.count > 10 :
					entry = {"domain": stat.domain, "count":stat.count}
					datastore.append(entry)
			return datastore
			
		except:
			e = sys.exc_info()[1]
			logging.error('Error visualizing stats %s' %e )
	def weeklyFeed(self,targetdate):
		try:
			if not targetdate:
				s="<?xml version=\"1.0\" encoding=\"UTF-8\"?><daily_stats>"
				s+="</daily_stats>"
				self.response.out.write(s)
				return
			else:
				try:
					year=targetdate[:4]
					month=targetdate[5:7]
					day=targetdate[8:10]
					logging.info('year %s month %s day %s' %(year, month, day))
					#targetdate=datetime.date(year,month, day)
					targetdate=datetime.date(int(year),int(month), int(day))
				except:
					e = sys.exc_info()[1]
					logging.error('error formating date %s =>  %s' %(targetdate, e))
					targetdate=datetime.date.today() - datetime.timedelta(days=1)
					
			logging.info('Fetching stats for %s' % targetdate)
			weeklyStats=WeeklyDomainStats.gql('WHERE date = :1 ORDER BY count DESC ', targetdate)
			datastore = []
			datastore = self.prepareforvisualize(weeklyStats)
			
			# prepare for output 
			description ={"domain": ("string", "Domain"),
					"count":("number", "Total Links")}
			columnnames = [ "domain", "count" ]
			data_table = gviz_api.DataTable(description)
			data_table.LoadData(datastore)
			
			self.response.headers['Content-Type'] = 'text/plain'
			self.response.out.write(data_table.ToJSonResponse(columns_order=(columnnames)))
			
		except:
			e = sys.exc_info()[1]
			logging.error('Error while fetching weekly feed %s' % e)

application = webapp.WSGIApplication(
                                     [('/visual', Visualization), 
					('/stats', VisualStats)],
					debug=True)
                                     

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()


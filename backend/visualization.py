import sys, os, time, datetime, cgi, logging, gviz_api, re, math
#import multiprocessing

from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import mail
from google.appengine.runtime import DeadlineExceededError
from urlparse import urlparse
from cron import StatsModel, DailyDomainStats, WeeklyDomainStats, YearDomainStats
from models import CountryStats, CityStats, SessionModel, UserStats
from xmpp_handler import XMPPHandler

class Visualization(webapp.RequestHandler):
	def get(self):
		txId = self.request.get('tqx')
		logging.info('txId: %s' % txId)
		params=dict([ p.split(':') for p in txId.split(';')])
		reqId = params['reqId']
		for p in params.iterkeys():
			logging.info(" request params %s: %s " %(p , params[p]))
		statstype=cgi.escape(self.request.get('type'))
		if statstype == "dailyfeed":
			targetdate=cgi.escape(self.request.get('date'))
			self.dailyFeed(targetdate, reqId)
		elif statstype == "weeklyfeed":
			targetdate=cgi.escape(self.request.get('date'))
			self.weeklyFeed(targetdate, reqId)
		elif statstype == "linkvolume":
			self.linkVolume(reqId)
		elif statstype == "countryFeed":
			self.countryFeed(reqId)
		elif statstype == "cityFeed":
			self.cityFeed(reqId)
		elif statstype == "weekLinks":
			self.weekLinks(reqId)
		elif statstype == "overAllLinks":
			self.overAllLinks(reqId)
                elif statstype == "userfeed":
			targetdate=cgi.escape(self.request.get('date'))
                        user = cgi.escape(self.request.get('user'))
                        self.userFeed(targetdate, user, reqId)
		else:
			self.response.out.write('Not yet implementd')
	def dailyFeed(self,tdate,reqId):
		try:
			if not tdate:
				today = datetime.date.today()
				yesterday=datetime.date.today() - datetime.timedelta(days=1)
				targetdate=yesterday
			else:
				try:
					targetdate=datetime.datetime.strptime(tdate, '%Y-%m-%d').date()
				except:
					e = sys.exc_info()[1]
					logging.error('error formating date %s =>  %s' %(tdate, e))
					targetdate=datetime.date.today() - datetime.timedelta(days=1)
					
			logging.info('Fetching stats for %s' % targetdate)
			dailyStats=DailyDomainStats.gql('WHERE date = :1 ORDER BY count DESC ', targetdate)
			if dailyStats is None or dailyStats.count() == 0 :
				logging.info('Not enough data for graph')
				self.response.out.write('Not enough data for graph')
				return
			logging.info('about to prepare %s query results for visualisation.' % dailyStats.count())
			datastore = self.prepareforvisualize(dailyStats)
			
			# prepare for output 
			description ={"domain": ("string", "Domain"),
					"count":("number", "Total Links")}
			columnnames = [ "domain", "count" ]
			data_table = gviz_api.DataTable(description)
			data_table.LoadData(datastore)
			
			self.response.headers['Content-Type'] = 'text/plain'
			self.response.out.write(data_table.ToJSonResponse(columns_order=(columnnames), req_id=reqId))
			
			
		except:
			e = sys.exc_info()[1]
			logging.error('Error while fetching daily feed %s' % e)

	def prepareforvisualize(self, stats):
		try:
			datastore = []
			# try to remember domains processed in order to avoid domain repeat
			tmp_list_processed_domains = []
			lowerMargin = 10
			result_margine = 10
			for stat in stats:
				if (stat.count > lowerMargin or len(datastore) < 5) and ( stat.domain not in tmp_list_processed_domains):
					entry = {"domain": stat.domain, "count":stat.count}
					datastore.append(entry)
					tmp_list_processed_domains.append(stat.domain)
					result_margine-=1
				if result_margine == 0:
					return datastore
			return datastore
			
		except:
			e0 = sys.exc_info()[0]
			e = sys.exc_info()[1]
			logging.error('Error visualizing stats %s %s' % (e0 , e) )
	def weeklyFeed(self,tdate, reqId):
		try:
			if not tdate:
				s="<?xml version=\"1.0\" encoding=\"UTF-8\"?><daily_stats>"
				s+="</daily_stats>"
				self.response.out.write(s)
				return
			else:
				try:
					targetdate=datetime.datetime.strptime(tdate, '%Y-%m-%d').date()
				except:
					e = sys.exc_info()[1]
					logging.error('error formating date %s =>  %s' %(tdate, e))
					targetdate=datetime.date.today() - datetime.timedelta(days=1)
					
			logging.info('Fetching stats for %s' % targetdate)
			weeklyStats=WeeklyDomainStats.gql('WHERE date = :1 ORDER BY count DESC ', targetdate)
			if weeklyStats is None or weeklyStats.count() == 0 :
				logging.info('Not enough data for graph')
				self.response.out.write('Not enough data for graph')
				return
			logging.info('about to prepare %s query results for visualisation.' % weeklyStats.count())
			xmpp_handler = XMPPHandler()
			xmpp_handler.cacheTopWeeklyDomains(weeklyStats)
			datastore = self.prepareforvisualize(weeklyStats)
			
			# prepare for output 
			description ={"domain": ("string", "Domain"),
					"count":("number", "Total Links")}
			columnnames = [ "domain", "count" ]
			data_table = gviz_api.DataTable(description)
			data_table.LoadData(datastore)
			
			self.response.headers['Content-Type'] = 'text/plain'
			self.response.out.write(data_table.ToJSonResponse(columns_order=(columnnames), req_id=reqId))
			
		except:
			e = sys.exc_info()[1]
			logging.error('Error while fetching weekly feed %s' % e)

	def linkVolume(self, reqId):
		logging.info('Link volume for last 2 weeks')
		linkCount = StatsModel.gql('ORDER by date desc').fetch(15)
		if linkCount is None: 
			logging.info('Not enough data for graph')
			self.repsonse.out.write('Not enough data for graph')
			return
		logging.info('retrieved %s stats' % len(linkCount))
		description = {"date": ("string", "Date"),
				"link_volume":("number", "Link volume"),
				"user_volume":("number", "Active Users")
                                }
		columnnames = [ "date", "link_volume" , "user_volume" ]
		data_table = gviz_api.DataTable(description)
		lnkCnt = []
		for linkCnt in linkCount:
			entry = {"date": linkCnt.date, "link_volume":linkCnt.totalDailyNumber, "user_volume":linkCnt.totalUserNumber}
			lnkCnt.append(entry)
		data_table.LoadData(lnkCnt)
		
		self.response.headers['Content-Type'] = 'text/plain'
		self.response.out.write(data_table.ToJSonResponse(columns_order=(columnnames) , req_id=reqId))
					
	def countryFeed(self, reqId):
		logging.info('Country stats feed')
		countryStats= CountryStats.gql('WHERE count > 10 ORDER BY count desc ').fetch(40)
		if countryStats is None: 
			logging.info('Not enough data for graph')
			self.repsonse.out.write('Not enough data for graph')
			return
		countryStats = [ x for x in countryStats if x.countryCode != 'XX' and x.countryCode != 'EU'  ]
		logging.info('retrieved %s stats' % len(countryStats))
		description = {"countryCode": ("string", "Country Code"),
				"count":("number", "Count")}
		columnnames = [ "countryCode", "count" ]
		data_table = gviz_api.DataTable(description)
		cntrCnt = []
		for countryCnt in countryStats:
			entry = {"countryCode": countryCnt.countryCode, "count":math.log(countryCnt.count)}
			cntrCnt.append(entry)
		data_table.LoadData(cntrCnt)
		
		self.response.headers['Content-Type'] = 'text/plain'
		self.response.out.write(data_table.ToJSonResponse(columns_order=(columnnames) , req_id=reqId))
		
	def cityFeed(self, reqId):
		logging.info('City stats feed')
		cityStatsQ= CityStats.gql('WHERE count > 100 ORDER BY count desc ').fetch(80)
		if cityStatsQ is None: 
			logging.info('Not enough data for graph')
			self.repsonse.out.write('Not enough data for graph')
			return
		cityStats = [ x for x in cityStatsQ if not "unknown" in x.city.lower() and x.countryCode != 'US' and x.countryCode != 'XX' ]
		logging.info('retrieved %s stats' % len(cityStats))
		description = {"city_countryCode": ("string", "City Code"),
				"count":("number", "Count")}
		columnnames = [ "city_countryCode", "count" ]
		data_table = gviz_api.DataTable(description)
		cityCnt = []
		for ctCnt in cityStats:
			entry = {"city_countryCode": ctCnt.city + ', ' + ctCnt.countryCode, "count":ctCnt.count}
			cityCnt.append(entry)
		data_table.LoadData(cityCnt)
		
		self.response.headers['Content-Type'] = 'text/plain'
		self.response.out.write(data_table.ToJSonResponse(columns_order=(columnnames) , req_id=reqId))

	def linkOverAllLinks(self, reqId):
		logging.info('overAll link popularity')
        def userFeed(self, targetdate, user, reqId):
                if user:
                        logging.info('getting stats for user: %s' %user)
                        stats = UserStats.gql('WHERE instapaper_account = :1 order by date desc', user).fetch(14)
                        if stats is None:
		        	logging.info('Not enough data for graph')
		        	self.repsonse.out.write('Not enough data for graph')
		        	return
		        stats = [ x for x in stats if x is not None ]
		        logging.info('retrieved %s stats' % len(stats))
		        description = {"date": ("string", "Date"),
		        		"count":("number", "Count")}
		        columnnames = [ "date", "count" ]
		        data_table = gviz_api.DataTable(description)
		        userCnt = []
		        for uCnt in stats:
                                logging.info('account:%s' % uCnt.to_xml())
			        entry = {"date": uCnt.date, "count":uCnt.count}
			        userCnt.append(entry)
		        data_table.LoadData(userCnt)
		
		        self.response.headers['Content-Type'] = 'text/plain'
		        self.response.out.write(data_table.ToJSonResponse(columns_order=(columnnames) , req_id=reqId))
                        return

	        if not targetdate:
	                today = datetime.date.today()
			yesterday=datetime.date.today() - datetime.timedelta(days=1)
			targetdate=yesterday
		else:
		        try:
			        targetdate=datetime.datetime.strptime(targetdate, '%Y-%m-%d').date()
			except:
			        e = sys.exc_info()[1]
			        logging.error('error formating date %s =>  %s' %(targetdate, e))
			        targetdate=datetime.date.today() - datetime.timedelta(days=1)
					
                logging.info('User stats feed')
                stats = UserStats.gql('WHERE date = :1 and count > 10 order by count desc', targetdate).fetch(50)
                if stats is None:
			logging.info('Not enough data for graph')
			self.repsonse.out.write('Not enough data for graph')
			return
		stats = [ x for x in stats if x is not None ]
		logging.info('retrieved %s stats' % len(stats))
		description = {"account": ("string", "User"),
				"count":("number", "Count")}
		columnnames = [ "account", "count" ]
		data_table = gviz_api.DataTable(description)
		userCnt = []
		for uCnt in stats:
                        logging.info('account:%s' % uCnt.to_xml())
			entry = {"account": uCnt.instapaper_account, "count":uCnt.count}
			userCnt.append(entry)
		data_table.LoadData(userCnt)
		
		self.response.headers['Content-Type'] = 'text/plain'
		self.response.out.write(data_table.ToJSonResponse(columns_order=(columnnames) , req_id=reqId))



		
	def linkWeekly(self,reqId):
		logging.info('weekly link popularity')
		
		

application = webapp.WSGIApplication(
                                     [('/visual', Visualization)],
					debug=True)
                                     

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()


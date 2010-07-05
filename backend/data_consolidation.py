import datetime, logging, os, urllib2
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache
from google.appengine.runtime import DeadlineExceededError
from google.appengine.ext.webapp import template
from utils import StatsUtil
from main import SessionModel
from models import UserLocationModel, CityStats, CountryStats, LinkStats
class GeneralConsolidation(webapp.RequestHandler):
	def get(self):
		memcache_key = 'domain_update_key'
		message = []
		#lower_limit_date = datetime.datetime.strptime('2009-11-15', '%Y-%m-%d').date()
		upper_limit_date = datetime.datetime.today().date()
		dateStr = self.request.get('date',None)
		processType = self.request.get('process_type',None)
		if dateStr is None and processType is None: 
			logging.info('no date specified')
			return
		date = datetime.datetime.strptime(dateStr, "%Y-%m-%d").date()
		if  upper_limit_date - date < datetime.timedelta(1):
			logging.info('invalid date specified: %s' %dateStr)
			self.response.out.write('invalid date specified: %s' %dateStr)
			memcache.delete(memcache_key)
			return
		#keyS = self.request.get('key', None);
		#if keyS:
		#	logging.info('got from request %s' % keyS )
		#  	key = db.Key(keyS)
		if memcache.get(memcache_key):
			logging.info('getting from memcache %s ' % memcache.get('domain_update_key'))
		  	key = memcache.get(memcache_key)
			if processType == 'all':
				sessions = SessionModel.gql('WHERE __key__ > :1 ORDER by  __key__ asc ', key).fetch(limit=2)
			else:
				sessions = SessionModel.gql('WHERE date = :1 and __key__ > :2 ORDER by  __key__ asc ', date, key).fetch(limit=2)
		else:
			if processType == 'all':
				sessions = SessionModel.gql('ORDER by __key__ asc ').fetch(limit=2)
				logging.info('getting from query: ORDER by __key__ asc')
			else:	
				sessions = SessionModel.gql('where date = :1 ORDER by __key__ asc ', date).fetch(limit=2)
				logging.info('getting from query: where date = :1 ORDER by __key__ asc')
		if len(sessions) < 2:
			logging.info('one session caught')
			# update last session domain
			corrected_domain = ''
			if len(sessions) == 1:
				currentSession = sessions[0]
				self.agregateData(currentSession, message, processType)
			# reset __key__ from cache
			memcache.delete(memcache_key)
			date = date + datetime.timedelta(days=1)
			logging.info('list out of range next date: %s' % str(date))
			#self.response.out.write('list out of range next date: %s' % str(date))
			message = 'next date'
			context = { 
				'message': message,
				'prev_url': '',
				'prev_domain' : corrected_domain, 
				'next_url' : '/data_consolidation?date=%s&process_type=%s' % ( dateStr, processType)
			}
			path= os.path.join(os.path.dirname(__file__), 'templates/update_date.html')
			self.response.out.write(template.render(path, context))
			return
		currentSession = sessions[0]
		self.agregateData(currentSession, message, processType)

		next_key = sessions[1].key()
		memcache.set(memcache_key, next_key)
		context = { 
			'message': message,
			'prev_url': currentSession.url,
			'prev_domain' : currentSession.domain, 
			'next_url' : '/data_consolidation?date=%s&process_type=%s' % ( dateStr, processType)
		}
		path= os.path.join(os.path.dirname(__file__), 'templates/update_date.html')
		self.response.out.write(template.render(path, context))
			
	def agregateData(self, currentSession, message, processType):
		logging.info('agregate data for %s' % currentSession.date)
		if processType == 'all':
			locationData = None
		else:
			locationData =StatsUtil.ipResolverAPI(currentSession.ip)
		message.append(currentSession.date)
		if locationData and len(locationData) == 2:
			logging.info('updating location data')
			city= locationData[0]
			countryCode = locationData[1]

			#self.response.out.write('location api response:<BR> city : %s; country: %s ' % (locationData[1], locationData[3]))
			logging.info('location api response:  %s ' % locationData)
			userLocation = UserLocationModel()
			userLocation.user = currentSession.instaright_account
			userLocation.city = city
			userLocation.countryCode = countryCode
			userLocation.date = currentSession.date
			message.append(currentSession.ip)
			message.append(city)
			message.append(countryCode)
			userLocation.put()
			# update country stats and city stats
			logging.info('country update')
			message.append(countryCode)
			existingCountryStat = CountryStats.gql('WHERE countryCode = :1' , countryCode).get()
			if existingCountryStat:
				existingCountryStat.count = existingCountryStat.count + 1
				existingCountryStat.put()
			else:
				countryStat = CountryStats()
				countryStat.countryCode = countryCode
				countryStat.count = 1
				countryStat.put()
				message.append(countryCode)
			logging.info('city update')
			existingCityStat = CityStats.gql('WHERE city = :1 and countryCode = :2', city, countryCode).get()
			if existingCityStat:
				existingCityStat.count = existingCityStat.count + 1
				existingCityStat.put()
			else:
				cityStat = CityStats()
				cityStat.countryCode = countryCode
				cityStat.city = city
				cityStat.count = 1
				cityStat.put()
				
			
		existingLinkStat = LinkStats.gql('WHERE link = :1', currentSession.url).get()
		if existingLinkStat:
			existingLinkStat.count = existingLinkStat.count + 1
			existingLinkStat.countUpdated = currentSession.date
			existingLinkStat.lastUpdatedBy = currentSession.instaright_account
			existingLinkStat.put()
		else:
			linkStat = LinkStats()
			linkStat.link=currentSession.url
			linkStat.count = 1
			linkStat.countUpdated = currentSession.date
			linkStat.lastUpdatedBy = currentSession.instaright_account
			linkStat.put()
		# domain update
		shouldUpdateSession = 0
		mode = ''
		if currentSession.domain is None or currentSession.domain == '':
			currentSession.domain = StatsUtil.getDomain(currentSession.url)
			shouldUpdateSession = 1
			mode='domain change: %s' % currentSession.domain
		if currentSession.date is None or currentSession.date == '':
			date = datetime.datetime.strptime('2009-11-15', '%Y-%m-%d').date() 
			currentSession.date = date
			shouldUpdateSession = 2
			mode='date change: %s' % date
		if shouldUpdateSession > 0:
			message = 'updating session mode: %s' % mode
			logging.info('updating session mode: %s' % mode)
			currentSession.put()
		else:
			logging.info('unchanged session' )
			message = 'unchanged session' 
		logging.info('done data aggregation')
		
		
application = webapp.WSGIApplication(
                                     [('/data_consolidation',GeneralConsolidation)],debug=True)

def main():
	run_wsgi_app(application)
if __name__ == '__main__':
	main()

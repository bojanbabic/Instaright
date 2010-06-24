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
class DomainConsolidation(webapp.RequestHandler):
	def get(self):
		memcache_key = 'domain_update_key'
		message = []
		generalConsolidation = GeneralConsolidation()
		#lower_limit_date = datetime.datetime.strptime('2009-11-15', '%Y-%m-%d').date()
		upper_limit_date = datetime.datetime.today().date()
		dateStr = self.request.get('date',None)
		if dateStr is None: 
			logging.info('no date specified')
			return
		date = datetime.datetime.strptime(dateStr, "%Y-%m-%d").date()
		if  upper_limit_date - date < datetime.timedelta(1):
			logging.info('invalid date specified: %s' %dateStr)
			self.response.out.write('invalid date specified: %s' %dateStr)
			return
		#keyS = self.request.get('key', None);
		#if keyS:
		#	logging.info('got from request %s' % keyS )
		#  	key = db.Key(keyS)
		if memcache.get(memcache_key):
			logging.info('getting from memcache %s ' % memcache.get('domain_update_key'))
		  	key = memcache.get(memcache_key)
			sessions = SessionModel.gql('WHERE date = :1 and __key__ > :2 ORDER by  __key__ asc ', date, key).fetch(limit=2)
		else:
			logging.info('getting from query')
			sessions = SessionModel.gql('where date = :1 ORDER by __key__ asc ', date).fetch(limit=2)
		if len(sessions) < 2:
			# update last session domain
			corrected_domain = ''
			if len(sessions) == 1:
				currentSession = sessions[0]
				generalConsolidation.agregateData(currentSession, message)
			# reset __key__ from cache
			memcache.delete(memcache_key)
			date = date + datetime.timedelta(days=1)
			self.response.out.write('list out of range next date: %s' % str(date))
			message = 'next date'
			context = { 
				'message': message,
				'prev_url': '',
				'prev_domain' : corrected_domain, 
				'next_url' : '/correct_domains?date=%s' % str(date)
			}
			path= os.path.join(os.path.dirname(__file__), 'templates/update_date.html')
			self.response.out.write(template.render(path, context))
			return
		currentSession = sessions[0]
		self.response.out.write('for date %s <br>' % currentSession.date)
		generalConsolidation.agregateData(currentSession, message)

		next_key = sessions[1].key()
		memcache.set(memcache_key, next_key)
		context = { 
			'message': message,
			'prev_url': currentSession.url,
			'prev_domain' : currentSession.domain, 
			'next_url' : '/correct_domains?date=%s' % dateStr
		}
		path= os.path.join(os.path.dirname(__file__), 'templates/update_date.html')
		self.response.out.write(template.render(path, context))
		
			
class GeneralConsolidation(webapp.RequestHandler):
	def agregateData(self, currentSession, message):
		logging.info('session date: %s ' % currentSession.date)
		locationData =StatsUtil.ipResolverAPI(currentSession.ip)
		message.append(currentSession.date)
		if locationData and len(locationData) == 2:
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
				
			
		logging.info('link update')
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
		if currentSession.domain is None or currentSession.domain == '':
			currentSession.domain = StatsUtil.getDomain(currentSession.url)
			logging.info('updating session %s ' % currentSession.domain)
			message = 'updating session %s ' % currentSession.domain 
			currentSession.put()
		else:
			logging.info('existing domain: %s' % currentSession.domain)
			message = 'existing domain: %s' % currentSession.domain
		
		
application = webapp.WSGIApplication(
                                     [('/data_consolidation', GeneralConsolidation ), ('/correct_domains',DomainConsolidation)],debug=True)

def main():
	run_wsgi_app(application)
if __name__ == '__main__':
	main()

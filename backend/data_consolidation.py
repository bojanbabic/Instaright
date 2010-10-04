import datetime, logging, os, urllib2
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache
from google.appengine.runtime import DeadlineExceededError
from google.appengine.ext.webapp import template
from google.appengine.api.labs import taskqueue

from utils import StatsUtil
from main import SessionModel
from models import UserLocationModel, CityStats, CountryStats, LinkStats, UserDetails
class GeneralConsolidation(webapp.RequestHandler):
	memcache_key = 'domain_update_key'
	def get(self):
		message = []
		#lower_limit_date = datetime.datetime.strptime('2009-11-15', '%Y-%m-%d').date()
		upper_limit_date = datetime.datetime.today().date()
		dateStr = self.request.get('date',None)
		processType = self.request.get('process_type',None)
		if processType is None or processType == 'None': 
			if dateStr is None :
				logging.info('no date specified')
				memcache.delete(memcache_key)
				return
			else:
				date = datetime.datetime.strptime(dateStr, "%Y-%m-%d").date()
				logging.info('parsing date %s' % date)
				if  upper_limit_date - date < datetime.timedelta(1):
					logging.info('invalid date specified: %s' %dateStr)
					self.response.out.write('invalid date specified: %s' %dateStr)
					memcache.delete(memcache_key)
					return
		sessions = self.fetchSessions(date)
		while (len(sessions) == 2):
			currentSession = sessions[0]
			logging.info('current session %s' % currentSession.to_xml())
			#self.agregateData(currentSession, message, processType, upper_limit_date)
			taskqueue.add(url='/aggregate_data', params={'sessionKey':currentSession.key(), 'message': message, 'processType': processType, 'upper_limit_date':upper_limit_date})
			memcache.set(self.memcache_key, currentSession.key())
			sessions = self.fetchSessions(date)
			break
		if len(sessions) == 1:
			currentSession = sessions[0]
			logging.info('current session %s' % currentSession.to_xml())
			#self.agregateData(currentSession, message, processType, upper_limit_date)
			taskqueue.add(url='/aggregate_data', params={'sessionKey':currentSession.key(), 'message': message, 'processType': processType, 'upper_limit_date':upper_limit_date})
		
	
	def fetchSessions(self, date):
		if memcache.get(self.memcache_key):
		  	key = memcache.get(self.memcache_key)
			logging.info('getting from memcache. retrieved: %s ' % key)
			sessions = SessionModel.gql('WHERE date = :1 and __key__ > :2 ORDER by  __key__ asc ', date, key).fetch(limit=2)
		else:
			sessions = SessionModel.gql('where date = :1 ORDER by __key__ asc ', date).fetch(limit=2)
			logging.info('getting from query: where date = :1 ORDER by __key__ asc')
		return sessions
		
			
	def agregateData(self, currentSession, message, processType, upper_limit_date):
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
			existingCountryStat = CountryStats.gql('WHERE countryCode = :1 and dateUpdated = :2' , countryCode, upper_limit_date).get()
			if existingCountryStat:
				existingCountryStat.count = existingCountryStat.count + 1
				existingCountryStat.put()
			else:
				countryStat = CountryStats()
				countryStat.countryCode = countryCode
				countryStat.count = 1
				#NOTE: make it default
				#countryStat.count = upper_limit_date
				countryStat.put()
				message.append(countryCode)
			logging.info('city update')
			existingCityStat = CityStats.gql('WHERE city = :1 and countryCode = :2 and dateUpdated = :3', city, countryCode, upper_limit_date).get()
			if existingCityStat:
				existingCityStat.count = existingCityStat.count + 1
				existingCityStat.put()
			else:
				cityStat = CityStats()
				cityStat.countryCode = countryCode
				cityStat.city = city
				cityStat.count = 1
				#NOTE: make it default
				#cityStat.updateDate = upper_limit_date
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

class AggregateDataHandler(webapp.RequestHandler):
	
	def post(self):
		key = self.request.get('sessionKey', None)
		processType = self.request.get('processType', None)
		upper_limit_date = self.request.get('update_limit_date', None)
		currentSession = None
		currentSessionKey = db.Key(key)
		if currentSessionKey is not None:
			currentSession = SessionModel.gql('WHERE __key__ = :1', currentSessionKey).get()
		if currentSession is None:
			logging.info('Can\'t process None session model')
			return
		self.aggregateData(currentSession, processType, upper_limit_date)

	def aggregateData(self, currentSession, processType, upper_limit_date):
		logging.info('agregate data for %s' % currentSession.date)
		locationData =StatsUtil.ipResolverAPI(currentSession.ip)
		if len(locationData) == 2:
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
			userLocation.put()
			# update country stats and city stats
			logging.info('country update')
			existingCountryStat = CountryStats.gql('WHERE countryCode = :1 and dateUpdated = :2' , countryCode, upper_limit_date).get()
			if existingCountryStat:
				existingCountryStat.count = existingCountryStat.count + 1
				existingCountryStat.put()
			else:
				countryStat = CountryStats()
				countryStat.countryCode = countryCode
				countryStat.count = 1
				#NOTE: make it default
				#countryStat.count = upper_limit_date
				countryStat.put()
			logging.info('city update')
			existingCityStat = CityStats.gql('WHERE city = :1 and countryCode = :2 and dateUpdated = :3', city, countryCode, upper_limit_date).get()
			if existingCityStat:
				existingCityStat.count = existingCityStat.count + 1
				existingCityStat.put()
			else:
				cityStat = CityStats()
				cityStat.countryCode = countryCode
				cityStat.city = city
				cityStat.count = 1
				#NOTE: make it default
				#cityStat.updateDate = upper_limit_date
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
			logging.info('updating session mode: %s' % mode)
			currentSession.put()
		else:
			logging.info('unchanged session' )
		logging.info('done data aggregation')

class UserDetailsConsolidation(webapp.RequestHandler):
        def get(self):
                dt = self.request.get('date' , None)
                memcache_key='user_details_key'+str(datetime.datetime.today().date())
                memcache_date='user_details_date'+str(datetime.datetime.today().date())
                memcache_prev_date='user_details_prev_date'+str(datetime.datetime.today().date())
                if dt is None:
                        key = memcache.get(memcache_key)
                        date = memcache.get(memcache_date)
                        logging.info('memcache key: %s %s' % (memcache_key, key))
                        logging.info('memcache key: %s %s' % (memcache_date, date))
                else:
                        logging.info('got it from request %s ' %dt)
			date = datetime.datetime.strptime(dt, '%Y-%m-%d').date() 
                        key = None
		path= os.path.join(os.path.dirname(__file__), 'templates/user_consolidation.html')
                template_variables = []
                if date is None:
                        #fist time
                        logging.info('fist usage')
                        session = SessionModel.gql('ORDER by date asc, __key__ asc').get()
                        logging.info('staring from date: %s' % session.date)
                        if session.date is None:
			        date = datetime.datetime.strptime('2009-11-15', '%Y-%m-%d').date()
                                logging.info('rewamping date %s' %date)
                                session.date = datetime.datetime.strptime('2009-11-15', '%Y-%m-%d')
                                session.put()
                                date = session.date
                elif key is None:
                        logging.info('new date %s ' % str(date))
                        #new date
                        session = SessionModel.gql('WHERE date = :1 ORDER by date asc, __key__ asc', date).get()
                else:
                        logging.info('contining from date %s ' % str(date))
                        session = SessionModel.gql('WHERE __key__ > :1  and date = :2 ORDER by  __key__ asc, date asc ', key, date).get()
                if session is None:
                        date = date + datetime.timedelta(days=1)
                        if date > datetime.datetime.today().date():
                                logging.info('user details consolidation - finaly done')
                                memcache.delete(memcache_date)
                                memcache.delete(memcache_key)
		                self.response.out.write(template.render(path,template_variables))
                                return
                        memcache.set(memcache_date, date)
                        memcache.delete(memcache_key)
		        self.response.out.write(template.render(path,template_variables))
                        return
                user_detail = UserDetails.gql('WHERE instapaper_account = :1' , session.instaright_account).get()
                if user_detail is None:
                        logging.info('new user: %s' % session.instaright_account)
                        user_detail = UserDetails()
                        user_detail.instapaper_account = session.instaright_account
                        user_detail.last_active_date = session.date
                        user_detail.put()
                else:
                        logging.info('updating usage for user: %s' % session.instaright_account)
                        user_detail.last_active_date = session.date
                        user_detail.links_added = user_detail.links_added + 1
                        user_detail.put()

                memcache.set(memcache_key, session.key())
                memcache.set(memcache_date, date)
		self.response.out.write(template.render(path,template_variables))
		
application = webapp.WSGIApplication(
                                     [('/data_consolidation',GeneralConsolidation), ('/user_consolidation', UserDetailsConsolidation), 
				      ('/aggregate_data', AggregateDataHandler)],debug=True)

def main():
	run_wsgi_app(application)
if __name__ == '__main__':
	main()

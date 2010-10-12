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

class UserDetailsConsolidation_batch(webapp.RequestHandler):
        def post(self):
                dt = self.request.get('date' , None)
                logging.info('date from request %s ' %dt)
                if dt is None:
			date = datetime.datetime.now().date() - datetime.timedelta(days=1)
                        logging.info('aggregatine users from yesterday.')
		else:
			date = datetime.datetime.strptime(dt, '%Y-%m-%d').date() 
                if date >= datetime.datetime.now().date():
                        logging.info('too early , wait')
                        self.response.out.write('too early . wait')
                        return
                memcache_key_sessions ='sessions_for_date_'+str(datetime.datetime.today().date())+'_'+str(date)
                cached_sessions = memcache.get(memcache_key_sessions)
                if cached_sessions:
                        logging.info('getting from cache for date %s' % str(date))
                        sessions = cached_sessions
                else:
                        sessions = SessionModel.getDailyStats(date)
                        memcache.set(memcache_key_sessions, sessions)
                if sessions is None:
                        logging.info('no sessions for date %s' % str(date))
                        return
                for s in sessions:
                        memcache_key_s = 'user_detail_'+str(datetime.datetime.now().date())+'_'+str(date)+'_'+str(s.key())
                        if memcache.get(memcache_key_s):
                                logging.info('skippin processed key %s for date %s' %(s.key(), str(date)))
                                continue
                        user_detail = UserDetails.gql('WHERE instapaper_account = :1' , s.instaright_account).get()
                        if user_detail is None:
                                logging.info('new user: %s' % s.instaright_account)
                                user_detail = UserDetails()
                                user_detail.instapaper_account = s.instaright_account
                                user_detail.last_active_date = s.date
                                user_detail.put()
                                #task queue that gathers info
                                fetch_task_url = '/user/'+s.instaright_account+'/fetch'
                                logging.info('adding task on url %s' %fetch_task_url)
                                taskqueue.add(queue_name='user-info', url=fetch_task_url)
                        else:
                                logging.info('updating usage for user: %s' % s.instaright_account)
                                user_detail.last_active_date = s.date
                                user_detail.links_added = user_detail.links_added + 1
                                user_detail.put()

                        memcache.set(memcache_key_s, s.key())
                logging.info('done for date %s' % str(date))
		self.response.out.write('done for date %s' %str(date))

#obsolete used one time for overall data aggregation
class UserDetailsConsolidation_task(webapp.RequestHandler):
        def get(self):
                date_from = self.request.get('from', None)
                date_to = self.request.get('to', None)
                if date_from is None and date_to is None:
                        logging.info('adding task for previuos day')
	                taskqueue.add(queue_name='user-consolidation', url='/user_consolidation')
                        return
                d_from = datetime.datetime.strptime(date_from, '%Y-%m-%d').date()
                d_to = datetime.datetime.strptime(date_to, '%Y-%m-%d').date()
                if d_from >= d_to:
                        logging.info('from must be less then to ')
                        self.response.out.write('from must be less then to ')
                        return
                while (d_from <= d_to):
                        logging.info('adding task: user consolidation for date %s' % str(d_from))
	                taskqueue.add(queue_name='user-consolidation', url='/user_consolidation', params={'date':d_from})
                        d_from = d_from + datetime.timedelta(days=1)

application = webapp.WSGIApplication(
                                     [
                                             ('/data_consolidation',GeneralConsolidation), 
                                             #('/user_consolidation', UserDetailsConsolidation), 
                                             ('/user_consolidation', UserDetailsConsolidation_batch), 
                                             ('/user_consolidation_task', UserDetailsConsolidation_task), 
				             ('/aggregate_data', AggregateDataHandler)
                                             ],debug=True)

def main():
	run_wsgi_app(application)
if __name__ == '__main__':
	main()

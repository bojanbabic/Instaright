import datetime, logging, os, urllib2, urllib
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache
from google.appengine.runtime import DeadlineExceededError
from google.appengine.ext.webapp import template
from google.appengine.api.labs import taskqueue

from utils import StatsUtil
from models import UserLocationModel, CityStats, CountryStats, LinkStats, UserDetails, SessionModel, UserStats
class GeneralConsolidation(webapp.RequestHandler):
	def post(self):
		message = []
		#lower_limit_date = datetime.datetime.strptime('2009-11-15', '%Y-%m-%d').date()
		dateStr = self.request.get('date',None)
	        if dateStr is None :
			logging.info('no date specified')
			return
		date = datetime.datetime.strptime(dateStr, "%Y-%m-%d").date()
		sessions = SessionModel.getDailyStats(date)
                if not sessions:
                        logging.info('no sessions for day %s' %date)
                        return
                for s in sessions:
	                memcache_key = 'domain_update_key'+dateStr+"_"+str(s.key())
                        if memcache.get(memcache_key):
                                logging.info('already processed key')
                                continue
			taskqueue.add(queue_name='data-consolidation',url='/aggregate_data', params={'sessionKey':s.key(), 'upper_limit_date':date})
			memcache.set(memcache_key, s.key())
			
class AggregateDataHandler(webapp.RequestHandler):
	
	def post(self):
		key = self.request.get('sessionKey', None)
		upper_limit_date = self.request.get('update_limit_date', None)
		currentSession = None
		currentSessionKey = db.Key(key)
		if currentSessionKey is not None:
			currentSession = SessionModel.gql('WHERE __key__ = :1', currentSessionKey).get()
		if currentSession is None:
			logging.info('Can\'t process None session model')
			return
		self.aggregateData(currentSession, upper_limit_date)

	def aggregateData(self, currentSession, upper_limit_date):
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
			existingCountryStat = CountryStats.gql('WHERE countryCode = :1 ' , countryCode).get()
			if existingCountryStat:
                                # hack to avoid exception
                                if existingCountryStat.count is None:
                                        existingCountryStat.count=1
                                else:
				        existingCountryStat.count += 1
                                logging.info('updating count %s' % existingCountryStat.count)
                                existingCountryStat.dateUpdated = upper_limit_date
				existingCountryStat.put()
			else:
                                logging.info('new country')
				countryStat = CountryStats()
				countryStat.countryCode = countryCode
				countryStat.count = 1
				countryStat.count = upper_limit_date
				countryStat.put()
			logging.info('city update')
			existingCityStat = CityStats.gql('WHERE city = :1 and countryCode = :2', city, countryCode).get()
			if existingCityStat:
                                # hack to avoid exception
                                if existingCityStat.count is None:
                                        existingCityStat.count=1
                                else:
				        existingCityStat.count += 1
                                existingCityStat.dateUpdated = upper_limit_date
                                logging.info('updating count %s' %existingCityStat.count)
				existingCityStat.put()
			else:
                                logging.info('new city')
				cityStat = CityStats()
				cityStat.countryCode = countryCode
				cityStat.city = city
				cityStat.count = 1
				cityStat.updateDate = upper_limit_date
				cityStat.put()
				
			
		existingLinkStat = LinkStats.gql('WHERE link = :1', currentSession.url).get()
                logging.info('link stats update')
		if existingLinkStat:
                        logging.info('new link %s' % currentSession.url)
			existingLinkStat.count = existingLinkStat.count + 1
			existingLinkStat.countUpdated = currentSession.date
			existingLinkStat.lastUpdatedBy = currentSession.instaright_account
			existingLinkStat.put()
		else:
                        logging.info('updating link stats: %s' % currentSession.url)
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
                cursor = self.request.get('last_cursor', None)
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
                memcache_key_sessions ='sessions_for_date_'+str(datetime.datetime.today().date())+'_'+str(date)+'_'+str(cursor)
                cached_sessions = memcache.get(memcache_key_sessions)
                if cached_sessions:
                        logging.info('getting from cache for date %s' % str(date))
                        sessions = cached_sessions
                else:
                        sessions = SessionModel.getDailyDataWithOffset(date, cursor)
                        logging.info('session batch size %d' % len(sessions))
                        memcache.set(memcache_key_sessions, sessions)
                if sessions is None:
                        logging.info('no sessions for date %s' % str(date))
                        return
                for s in sessions:
                        memcache_key_s = 'user_detail_'+str(datetime.datetime.now().date())+'_'+str(date)+'_'+str(s.key())
                        if memcache.get(memcache_key_s):
                                logging.info('skippin processed key %s for date %s' %(s.key(), str(date)))
                                continue
                        #links stats add to queue 
			taskqueue.add(queue_name='data-consolidation',url='/aggregate_data', params={'sessionKey':s.key(), 'upper_limit_date':date})
                        #TODO also create tas cue for user consolidation
                        userStats = UserStats.gql('WHERE instapaper_account = :1 and date = :2', s.instaright_account, date).get()
                        if userStats is None:
                                logging.info('no user stats for user: %s and date: %s' %(s.instaright_account, str(date)))
                                userStats= UserStats()
                                userStats.instapaper_account = s.instaright_account
                                userStats.count = 1
                                userStats.date = date
                                userStats.put()
                        else:
                                logging.info('updating user stats for user %s and date %s' %(s.instaright_account, str(date)))
                                userStats.count = userStats.count + 1
                                userStats.put()

                        user_detail = UserDetails.gql('WHERE instapaper_account = :1' , s.instaright_account).get()
                        if user_detail is None:
                                logging.info('new user: %s' % s.instaright_account)
                                user_detail = UserDetails()
                                user_detail.instapaper_account = s.instaright_account
                                user_detail.last_active_date = s.date
                                user_detail.put()
                                #task queue that gathers info
                                fetch_task_url = '/user/'+urllib2.quote(s.instaright_account)+'/fetch'
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

class UserConsolidationTask(webapp.RequestHandler):
        def get(self):
                dateStr=self.request.get('date', None)
                if dateStr is None:
                        date=datetime.datetime.now().date() - datetime.timedelta(days=1)
                else:
                        date=datetime.datetime.strptime(dateStr, '%Y-%m-%d').date()
                upperLimitDate = date + datetime.timedelta(days=1)
                cursor=None
		query = SessionModel.gql(' WHERE date >= :1 and date < :2 ', date, upperLimitDate)
                data=query.fetch(1000)
                logging.info('initial fetch got: %s' %len(data))
                taskqueue.add(queue_name='user-consolidation', url='/user_consolidation', params={'date':date})
                logging.info('added to queue task')
                while len(data) == 1000:
                      cursor=query.cursor()  
                      query= SessionModel.gql(' WHERE date >= :1 and date < :2 ', date, upperLimitDate).with_cursor(cursor)
                      data=query.fetch(1000)
                      logging.info('fetch got: %s' %len(data))
                      taskqueue.add(queue_name='user-consolidation', url='/user_consolidation', params={'date':date,'last_cursor':cursor})
                      logging.info('added to queue task')
                
#obsolete used one time for overall data aggregation
class SessionConsolidation_task(webapp.RequestHandler):
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
                while (d_from < d_to):
	                taskqueue.add(url='/data_consolidation',params={'date': d_from})
                        d_from+= datetime.timedelta(days=1)

class FeedLinkConsolidation(webapp.RequestHandler):
        def get(self):
                feedproxy='feedproxy.google.com'
                feedLinks = SessionModel.gql('WHERE domain= :1', feedproxy).fetch(5000)
                logging.info('fetched feedproxy links %s' %len(feedLinks))
                for l in feedLinks:
                        memcache_key='link_transform'+str(l.key())+'_'+str(datetime.datetime.now().date())
                        if memcache.get(memcache_key):
                                logging.info('allready processed link %s' % l.url)
                                continue
                        logging.info('transforming link %s' % l.url)
                        taskqueue.add(queue_name='link-consolidation', url='/link/transform/feed', params={'key':l.key()})
                        memcache.set(memcache_key, 1)

class ShortLinkConsolidation(webapp.RequestHandler):
        def get(self):
                short_bitly='bit.ly'
                shortLinks = SessionModel.gql('WHERE domain= :1', short_bitly).fetch(5000)
                #TODO identify other shortners
                logging.info('fetched short links %s' % len(shortLinks))
                for l in shortLinks:
                        memcache_key='link_transform'+str(l.key())+'_'+str(datetime.datetime.now().date())
                        if memcache.get(memcache_key):
                                logging.info('allready processed link %s' % l.url)
                                continue
                        logging.info('transforming link %s' % l.url)
                        taskqueue.add(queue_name='link-consolidation', url='/link/transform/short', params={'key':l.key()})
                        memcache.set(memcache_key, 1)


application = webapp.WSGIApplication(
                                     [
                                             ('/data_consolidation',GeneralConsolidation), 
                                             ('/session_consolidation_task', SessionConsolidation_task), 
                                             ('/user_consolidation', UserDetailsConsolidation_batch), 
                                             ('/user_consolidation_task', UserConsolidationTask), 
                                             ('/short_link_consolidation', ShortLinkConsolidation), 
                                             ('/feed_link_consolidation', FeedLinkConsolidation), 
				             ('/aggregate_data', AggregateDataHandler)
                                             ],debug=True)

def main():
	run_wsgi_app(application)
if __name__ == '__main__':
	main()

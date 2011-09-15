import datetime
import time
import urllib
import urllib2
import logging
import os
import sys
import ConfigParser
from google.appengine.ext import webapp
from google.appengine.api import urlfetch
from google.appengine.api import datastore_errors
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api.labs import taskqueue
from google.appengine.ext.webapp import template
from google.appengine.runtime import apiproxy_errors

from models import UserDetails, SessionModel, Badges
from models import UserStats, UserBadge, ScoreUsersDaily
from utils import BadgeUtil, UserScoreUtility
from generic_handler import GenericWebHandler

sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
import simplejson


class TopUserHandler(webapp.RequestHandler):
        def get(self, stat_range):
                format = self.request.get('format', None)
		if '-' in stat_range:
		        low, high = stat_range.split('-')
		else:
		        low, high = stat_range, None
       		memcache_key = 'top_users_' +str(datetime.datetime.now().date()) + '_' + stat_range
       		usrs = memcache.get(memcache_key)
		if usrs:
                        if format and format == 'txt':
                                self.response.headers["Content-type"] = "text/plain"
                                self.response.out.write("\n".join([u[0] for u in usrs]))
                                return 
                	template_variables = {'users': usrs}
        		path= os.path.join(os.path.dirname(__file__), 'templates/top_users.html')
                    	self.response.headers["Content-type"] = "text/html"
        		self.response.out.write(template.render(path, template_variables))
                        return
       	        elif high:
			logging.info('lower range %s ; higher range %s' %(low, high))
			users = UserDetails.gql('WHERE links_added >= :1 and links_added < :2 ORDER by links_added DESC', int(low), int(high))
		else:
			logging.info('lower range %s ' %low)
			users = UserDetails.gql('WHERE links_added >= :1 ORDER by links_added DESC', int(low))
                logging.info('fetched %d users ' % users.count())
	       	user_accounts = [ (u.instapaper_account, u.links_added) for u in users ]
		if users.count() > 0:
			logging.info('setting users cache. %s user entries' % users.count())
        		memcache.set(memcache_key, user_accounts)
                if format and format == 'txt':
                        self.response.headers["Content-type"] = "text/plain"
                        self.response.out.write("\n".join([ u[0] for u in user_accounts ]))
                        return
                template_variables = {'users' : user_accounts }
		path= os.path.join(os.path.dirname(__file__), 'templates/top_users.html')
        	self.response.headers["Content-type"] = "text/html"
		self.response.out.write(template.render(path,template_variables))


class UserGenericHandler(GenericWebHandler):
        def __init__(self):
                conf=ConfigParser.ConfigParser()
	        conf.read(os.path.split(os.path.realpath(__file__))[0]+'/properties/users.ini')
                self.visible_links=int(conf.get('dashboard','show_links'))
        def get(self):
                #redirect from appengine domain
                self.redirect_perm()
                self.get_user()

                if self.user_uuid is None or len(str(self.user_uuid)) == 0 or self.screen_name is None or self.user_detail_key is None:
                        logging.info('No cookies, redirecting to home page')
                        self.redirect('/')
                        return
                logging.info('user: %s' %self.instaright_account)
                sessions = SessionModel.gql('WHERE instaright_account = :1 ORDER by date desc ' , self.instaright_account).fetch(20)

                score = 0
                links = None
                if sessions is not None:
                        links = [ s for s in sessions if s is not None ]
                ud_key=db.Key(self.user_detail_key)
                logging.info('user detail key %s' % self.user_detail_key)
                template_variables=[]
                now=datetime.datetime.now().date()
                #start_of_week= time.asctime(time.strptime('%s %s 1' %(now.year, now.isocalendar()[1]), '%Y %W %w'))
                start_of_week= datetime.datetime.strptime('%s %s 1' %(now.year, now.isocalendar()[1]), '%Y %W %w')
                memcache_key='user_'+self.user_detail_key+'_score'
                cached_score=memcache.get(memcache_key)
                if cached_score is not None:
                        logging.info('got score from cache( %s ): %s' %( memcache_key, cached_score ))
                        score=cached_score
                else:
                        logging.info('parameters: start of week %s now %s for user_key %s ' % ( start_of_week,now, ud_key))
                        score_entities = ScoreUsersDaily.gql('WHERE user = :1 and date >= :2', ud_key, start_of_week).fetch(100)
                        #score_entities = ScoreUsersDaily.gql('WHERE user = :1 and date <= :2 and date >= :3', ud_key, now , start_of_week).fetch(100)
                        logging.info('got %s score entities' % len(score_entities))
                        if score_entities is not None:
                                scores = [ s.score for s in score_entities if s is not None ]
                                score=sum(scores)

                        logging.info('calculated score : %s' % score )
                        exp_ts=time.mktime((datetime.datetime.now() + datetime.timedelta(days=1)).timetuple())
                        memcache.set(memcache_key, score, time=exp_ts)
                badges = None
                all_badges = UserBadge.gql('WHERE user = :1 order by date desc', self.instaright_account).fetch(1000)
                if all_badges is not None:
                        badges = set([ (b.badge, b.badge_property.badge_desc) for b in all_badges if b is not None and b.badge_property is not None ])
                template_variables = {'user':self.screen_name, 'avatar':self.avatar,'instaright_account':self.instaright_account,'facebook_profile': self.facebook_profile, 'twitter_profile': self.twitter_profile, 'google_profile': self.google_profile, 'evernote_profile': self.evernote_profile, 'links':links, 'score': score, 'visible_items_num': self.visible_links, 'badges': badges,'logout_url':'/account/logout'}
                logging.info('templates %s' %template_variables)
                path= os.path.join(os.path.dirname(__file__), 'templates/user_info.html')
                self.response.headers["Content-type"] = "text/html"
		self.response.out.write(template.render(path,template_variables))

class UserHandler(webapp.RequestHandler):
        def get(self, user):
                if user is None or len(user) == 0:
                        logging.error('Empty user. Skipping')
                        return
                user_decoded = urllib.unquote(user)
                logging.info('user: %s' %user_decoded)
                ud=UserDetails.gql('WHERE instapaper_account = :1' , user_decoded).get()
                if ud is None:
                        logging.info('non existing user. redirect to home')
                        self.redirect('/')
                        return
                # sanity check
                if ud.instaright_account is None:
                        ud.instaright_account = ud.instapaper_account
                        ud.put()
                memcache_key ='user_info_' + user_decoded+'_'+str(datetime.datetime.now().date())
                sessions = SessionModel.gql('WHERE instaright_account = :1 ORDER by date desc ' , user_decoded).fetch(100)
                links = [ s for s in sessions if s is not None ]
                cached_info = memcache.get(memcache_key)
                if cached_info:
                        logging.info('getting from cache' )
                        template_variables = {'user':cached_info,'links':links}
                        path= os.path.join(os.path.dirname(__file__), 'templates/user_info.html')
                        self.response.headers["Content-type"] = "text/html"
		        self.response.out.write(template.render(path,template_variables))
                        return
                user_detail= UserDetails.gql('WHERE mail = :1', user_decoded).get()
                if user_detail is None:
			logging.info('new user %s added to queue' %user_decoded)
			fetch_url = '/user/'+user+'/fetch'
			taskqueue.add(queue_name='user-info', url= fetch_url)
                        ud = UserDetails()
                        ud.name = user_decoded
                        ud.instapaper_account = user_decoded
                        ud.instaright_account = user_decoded
                        ud.links_added = SessionModel.countAllForUser(user_decoded)
                        # tmp put until we find more info for user
                        ud.put()
                        template_variables = {'user':ud, 'links': links}
                        path= os.path.join(os.path.dirname(__file__), 'templates/user_info.html')
                        self.response.headers["Content-type"] = "text/html"
                        self.response.headers["Accept-Charset"] = "utf-8"
		        self.response.out.write(template.render(path,template_variables))
			return
                if user_detail.instaright_account is None:
                        user_detail.instaright_account = user_decoded
                        user_detail.put()
		memcache.set(memcache_key, user_detail)
                template_variables = {'user':user_detail, "links" : links}
                path= os.path.join(os.path.dirname(__file__), 'templates/user_info.html')
                self.response.headers["Content-type"] = "text/html"
		self.response.out.write(template.render(path,template_variables))

        def gather_info(self, user):
                if not '@' in user:
			logging.info('not email address: skipping ...')
                        user_detail = UserDetails()
			return user_detail
                user_detail = UserDetails.gql('where instapaper_account = :1' , user).get()
		if user_detail is None:
			user_detail = UserDetails()
		if user_detail.mail is None:
			logging.info('updating user details setting user mail %s' % user)
			user_detail.mail = user
                if user_detail.instaright_account is None:
                        logging.info('update instaright account for user %s' % user)
                        user_detail.instaright_account = user

                #PREPARE for request
                #time_milis = time.time() * 1000
                logging.info("user encoded %s" % user)
                RAPPORTIVE_LINK = "https://rapportive.com/contacts/email/%s" % user
		logging.info('fetchin url:%s' %RAPPORTIVE_LINK)
		#TILL here
                try:
                        response = urlfetch.fetch(RAPPORTIVE_LINK)
                except:
                        logging.info('error downloading rapportive info. reTRYing')
			try:
                        	response = urlfetch.fetch(RAPPORTIVE_LINK)
			except:
                        	e, e1 = sys.exc_info()[0], sys.exc_info()[1]
                        	return user_detail
                if response.status_code == 200:

                        json_string_response = simplejson.loads(simplejson.dumps(response.content))
                        json = simplejson.loads(json_string_response)
			name = None
			try:
                        	name = json["contact"]["name"]
			except:
				logging.info("unable to gather name from rapportive")

                        if name is None or len(name) < 1 or unicode(name).startswith('Thanks') or unicode(name).startswith('Sorry'):
				logging.info('did not find name for account %s' % user)
                                return user_detail
                        
                        logging.info('name: %s' % unicode(name))
                        user_detail.name = unicode(name)
                        memberships = json["contact"]["memberships"] 
                        memships = {}
                        for m in memberships:
                                service_name = m['site_name'].lower().replace(' ','_').replace('.','_')
                                memships[service_name]=m['profile_url']
				try:
                                	setattr(user_detail, service_name, m['profile_url'])
					logging.info('service %s profile %s' % (service_name, m['profile_url']))
                                        if service_name == 'twitter' and not user_detail.twitter_request_sent:
                                                # send twitter request and need to put since we need key for follow
						user_detail.twitter_request_sent=True
						user_detail.put()
                                                taskqueue.add(url='/util/twitter/follow/'+str(user_detail.key()), queue_name='twit-queue')
				except:
					logging.error('memberships error %s ::: more details %s ' % (sys.exc_info()[0], sys.exc_info()[1]))

                        user_detail.social_data = simplejson.dumps(memships)
                        occupations = json["contact"]["occupations"]
                        occups = []
                        for o in occupations:
                                tmp_o = o['job_title'] + " ^_^ " + o['company']
                                occups.append(tmp_o)
                        user_detail.occupations = '; '.join(occups)
			logging.info('occupations %s' %user_detail.occupations)
			avatar = None
			try:
                        	avatar = json["contact"]["images"][0]["url"]
                        	logging.info('avatar %s' % avatar)
			except:
				logging.info('no image info cause of %s' % sys.exc_info()[0])
                        if avatar is not None and len(avatar) > 0:
                                user_detail.avatar = avatar
			location = None
			try:
				location = json["contact"]["location"]
			except:
				logging.info('no location info cause of %' %sys.exc_info()[0])
			if location is not None and len(location):
				location_lines = location.splitlines()
				user_detail.location = ' '.join(location_lines)
                return user_detail

class UserDeleteHandler(webapp.RequestHandler):
        def get(self):
                user_details =  UserDetails.all()
                logging.info('fetched %d ' % user_details.count())
                for u in user_details:
                        logging.info('deleting %s' %(u.instapaper_account))
                        u.delete()

class UserInfoFetchHandler(webapp.RequestHandler):
        def post(self, user):
                logging.info('fetching info for user %s' % user)
                userhandler = UserHandler()
                user_decoded = urllib.unquote(user)
                user_decoded = user_decoded.strip()
                logging.info('fetching info for user %s' % user_decoded)
                userDetail = userhandler.gather_info(user_decoded)
                if userDetail.name:
                        userDetail.put()
	                logging.info('done fetching info for user %s' % user_decoded)
                	logging.info('fetching info for user %s' % user)

class UserUpdate(webapp.RequestHandler):
	def post(self):
                users = simplejson.loads(self.request.get('users',None))
                if users is None:
                        logging.info('nothing to process.exiting')
                        return
                logging.info('processing %s' % len(users))
		for u in users:
                        user = u['u']
                        if not '@' in user:
				logging.info('skipping %s' % user)
				continue
			memcache_user_key='user_'+user+'_'+str(datetime.datetime.now().date)
			if memcache.get(memcache_user_key):
				logging.info('skipping processed user %s ' % user)
                        taskqueue.add(queue_name='user-info', url='/user/'+urllib2.quote(user)+'/fetch')
			memcache.set(memcache_user_key, True)
        def get(self):
		users=UserDetails.gql('ORDER by __key__').fetch(100)
		if not users:
			return None
                taskqueue.add(url='/user/task/update_all', params={'users':simplejson.dumps(users, default=lambda u: {'u':u.instapaper_account})})
		lastKey = users[-1].key()
		while len(users) == 100:
			users=UserDetails.gql('WHERE __key__> :1 ORDER by __key__', lastKey).fetch(100)
			lastKey=users[-1].key()
                        taskqueue.add(url='/user/task/update_all', params={'users':simplejson.dumps(users, default=lambda u: {'u':u.instapaper_account})})

class UserLinksHandler(webapp.RequestHandler):
        def get(self, user):
                if user is None or len(user) == 0:
                        logging.error('Empty user. Skipping')
                        return
                user_decoded = urllib.unquote(user)
                sessions = SessionModel.gql('WHERE instaright_account = :1 ORDER by date desc ' , user_decoded).fetch(1000)
                links = [ s.url for s in sessions ]
                template_variables = {'links' : links }
                path= os.path.join(os.path.dirname(__file__), 'templates/user_links.html')
                self.response.headers["Content-type"] = "text/html"
		self.response.out.write(template.render(path,template_variables))
                
class UserFormKeyHandler(webapp.RequestHandler):
        def get(self, user, form_key):
                if user is None or len(user) == 0:
                        logging.error('Empty user. Skipping')
                        return
                user_decoded = urllib.unquote(user)
                user_detail= UserDetails.gql('WHERE instapaper_account = :1 ' , user_decoded).get()
                self.response.headers["Content-type"] = "text/plain"
                if user_detail and user_detail.form_key:
		        form_key=user_detail.form_key     
                else:
                        form_key=""
                self.response.out.write(form_key)

        def post(self, user, form_key):
                if user is None or len(user) == 0:
                        logging.error('Empty user. Skipping')
                        return
                user_decoded = urllib.unquote(user)
                user_detail= UserDetails.gql('WHERE instapaper_account = :1 ' , user_decoded).get()
                if user_detail:
                        user_detail.form_key=form_key
                        user_detail.put()
                self.response.headers["Content-type"] = "text/plain"
                self.response.out.write(form_key)
class UserStatsHandler(webapp.RequestHandler):
        def get(self, period):
                date_ = self.request.get('date', None)
                if date_:
                        date = datetime.datetime.strptime(date_, '%Y-%m-%d')
                else:   
                        date = datetime.datetime.now() - datetime.timedelta(days=1)
                logging.info('fetching stats for %s and %s' %(period,str(date.date())))
                if period == 'daily':
                        stats = UserStats.gql('WHERE date = :1 order by count desc', date).fetch(100)
                elif period == 'weekly':
                        self.response.out.write('TODO')
                        return
                else:
                        self.response.out.write('Get outta here')
                        return
                if not stats:
                        self.response.out.write('not stats for %s and date %s retreived no data' %( period, date_))
                        return
                self.response.headers["Content-type"] = "application/json"
                self.response.out.write(simplejson.dumps(stats, default=lambda s: {'u':{'account':s.instapaper_account, 'cout': s.count}}))
class UserStatsDeleteHandler(webapp.RequestHandler):
        def get(self, d):
                if d is None:
                        logging.info('no date.exit')
                        return
                date=datetime.datetime.strptime(d, '%Y-%m-%d').date()
                #if period == 'daily':
                #        allUsers = UserStats.all()
                #else:
                #        self.response.out.write('get outta here')
                #        return
                allUsers = UserStats.gql('WHERE date = :1', date).fetch(1000)
                if not allUsers:
                        logging.info('not stats for %s delete , exit' %d)
                        return
                logging.info('total stats for  %s delete %d' % (d, len(allUsers)))
                for u in allUsers:
                        u.delete()
                logging.info('done')

class ListUserHandler(webapp.RequestHandler):
        def get(self):
                prop=self.request.get('property',None)
                u = UserDetails()
                users = []
                buf = []
                if prop is not None and hasattr(u,prop):
                        logging.info('property %s' %prop)
                        if prop == 'mail':
                                logging.info('fetching users with mail')
                                users=UserDetails.gql('ORDER by mail desc').fetch(10000)
                else:
                        logging.info('missing property')
                if len(users) > 0:
                        logging.info('fetched %s' % len(users))
                        for u in users:
                                if u.mail is not None:
                                        buf.append('dn: cn='+u.name+',mail='+u.mail)
                                        buf.append('objectclass: top')
                                        buf.append('objectclass: person')
                                        buf.append('objectclass: organizationalPerson')
                                        buf.append('objectclass: inetOrgPerson')
                                        buf.append('objectclass: mozillaAbPersonAlpha')
                                        buf.append('givenName:'+u.name)
                                        buf.append('sn:')
                                        buf.append('cn:'+u.name)
                                        buf.append('mail:'+u.mail)
                                        buf.append('modifytimestamp: 0Z')
                                        buf.append('')
                                else:
                                        logging.info('missing mail %s' % u.name)
                                        
                                
                        self.response.headers['Content-type']='text/plain'
                        self.response.out.write('\n'.join(buf))

class UserBadgeTaskHandler(webapp.RequestHandler):
	def __init__(self):
		self.conf = ConfigParser.ConfigParser()
	        self.conf.read(os.path.split(os.path.realpath(__file__))[0]+'/properties/category2badge.ini')
        def post(self):
                user=self.request.get('user', None)
                url=self.request.get('url', None)
                domain=self.request.get('domain', None)
                version=self.request.get('version', None)
                client=self.request.get('client', None)
                badge=None
                if user is None:
                        logging.info('unknown user skipping')
                        return
                user_details = UserDetails.gql('WHERE instaright_account = :1', user).get()
                if user_details is None:
                        user_details = UserDetails()
                        user_details.instaright_account = user
                        user_details.put()
                client_badge = UserBadge.gql('WHERE badge = :1 and user = :2', client, user).get()
                if client_badge is None:
                        badge = Badges.gql('WHERE badge_label = :1' , client).get()
                        client_badge = UserBadge()
                        client_badge.badge = client
                        client_badge.badge_property = badge.key()
                        client_badge.date = datetime.datetime.now().date()
                        client_badge.user = user
                        client_badge.user_property = user_details.key()
                        client_badge.put()
                if version is not None and len(version) == 0:
                        version = None
                currentBadge = memcache.get('badge_'+user)
                if currentBadge is not None and (currentBadge == '1' or currentBadge == '2' or currentBadge == '3' or currentBadge == '5'):
                        logging.info('for user %s already using full day badge: %s' %(user,currentBadge))
                        return
                badger=BadgeUtil.getBadger(user, url, domain, version)
                if badger is None:
                        logging.info('no badger initialized. skipping')
                        return
                badge=badger.getBadge()
                if badge is not None:
                        # midnight timestamp - memcache expiration 
                        midnight=datetime.datetime.now().date() + datetime.timedelta(days=1)
                        midnight_ts=time.mktime(midnight.timetuple())
                        memcache.set('badge_'+user, badge, time=midnight_ts)
                        logging.info('setting badge cache: %s for user badge_%s valid until midnight %s' % (badge,user,midnight_ts))
                        existingBadge=UserBadge.gql('WHERE badge = :1 and user = :2 and date = :3', badge, user, datetime.datetime.now().date()).get()
                        if existingBadge is not None:
                                self.response.out.write('request processed')
                                return
                        b = Badges.gql('WHERE badge_label = :1' , badge).get()
                        if b is None:
                                b = Badges()
                                b.badge_label = badge
                                b.badge_icon = badge
                                b.put()
                        userBadge=UserBadge()
                        userBadge.user=user
                        userBadge.badge=badge
                        userBadge.badge_property = b.key()
                        userBadge.user_property = user_details.key()
                        userBadge.put()
			
                UserScoreUtility.updateBadgeScore(user, badge)
class UserUtil(object):

	@classmethod
        def getAvatar(cls,instapaper_account):
                if instapaper_account is None:
                        return '/static/images/noavatar.png'
		memcache_key='avatar_'+instapaper_account
		cached_avatar = memcache.get(memcache_key)
		if cached_avatar:
                        logging.info('getting avatar from cache: %s for user %s' %(cached_avatar, instapaper_account))
			return cached_avatar
		userDetails = UserDetails.gql('WHERE instapaper_account = :1', instapaper_account).get()
		if userDetails and userDetails.avatar is not None:
                        logging.info('%s avatar %s' % (instapaper_account, userDetails.avatar))
			memcache.set(memcache_key, userDetails.avatar)
			return userDetails.avatar
		else:
			return '/static/images/noavatar.png'


	@classmethod
	def getKloutScore(cls, user, klout_api_key):
		score = None
		logging.info('klout score for %s' % user)
		userDetails=UserDetails.gql('WHERE instapaper_account = :1' , user).get()
		if userDetails is None or userDetails.twitter is None:
                	userhandler = UserHandler()
                	logging.info(' trying get more info for user %s' % user)
                	userDetails = userhandler.gather_info(user)
			if userDetails is not None:
				logging.info('saving user info %s' %userDetails.mail)
			        try:
				        while True:
					        timeout_ms = 100
					        try:
				                        userDetails.put()
						        break
					        except datastore_errors.Timeout:
						        time.sleep(timeout_ms)
						        timeout_ms *= 2
			        except apiproxy_errors.DeadlineExceededError:
				        logging.info('run out of retries for writing to db')
		if userDetails is None or userDetails.twitter is None:
			logging.info('no twitter account for user %s . aborting' % user)
			return
			
                screen_name = str(userDetails.twitter).replace('http://twitter.com/', '')
		KLOUT_SCORE_URL='http://api.klout.com/1/klout.json?key=%s&users=%s' %(klout_api_key, screen_name)
		response = None
		try:
                        response = urlfetch.fetch(KLOUT_SCORE_URL)
		except:
			logging.info('error fetching url %s' % KLOUT_SCORE_URL)
		if response is None or response.status_code != 200:
               		logging.info('unexpected response') 
			return
		logging.info('klout api response %s' % response.content)
		json = eval(response.content)
		try:
			score = json["users"][0]["kscore"]
			logging.info('klout api returned score %s for user %s' % ( str(score), screen_name))
		except:
                        e, e1 = sys.exc_info()[0], sys.exc_info()[1]
                        logging.info('error: %s, %s for response: %s' %(e, e1, json))
		if score is not None:
			userDetails.klout_score=int(score)
			userDetails.put()
		return score
		

app = webapp.WSGIApplication([
                                ('/user/stats/top/(.*)', TopUserHandler),
                                ('/user/list', ListUserHandler),
                                ('/user/stats/(.*)/delete_all', UserStatsDeleteHandler),
                                ('/user/stats/(.*)', UserStatsHandler),
                                #NOTE: never uncomment this
                                #('/user/delete_all', UserDeleteHandler),
                                ('/user/dashboard', UserGenericHandler),
                                ('/user/(.*)/links', UserLinksHandler),
                                ('/user/(.*)/fetch', UserInfoFetchHandler),
                                ('/user/task/update_all', UserUpdate),
                                ('/user/badge/task', UserBadgeTaskHandler),
                                ('/user/(.*)/(.*)', UserFormKeyHandler),
                                ('/user/(.*)', UserHandler),
                                        ], debug = True)
def main():
        run_wsgi_app(app)

if __name__ == "__main__":
        main()


import sys
import os 
import logging
import ConfigParser
import time
import datetime

from google.appengine.api import urlfetch
from google.appengine.api import users, mail, memcache
from google.appengine.api import datastore_errors
from google.appengine.api.labs import taskqueue
from google.appengine.runtime import apiproxy_errors

sys.path.append(os.path.join(os.path.dirname(__file__), '../lib'))
import simplejson
import facebook
from oauth_handler import OAuthClient, OAuthAccessToken

from models import UserBadge, UserDetails, Badges
class UserUtils(object):
	def __init__(self):
		config=ConfigParser.ConfigParser()
		config.read(os.path.split(os.path.realpath(__file__))[0]+'/../properties/general.ini')
		self.facebook_key=config.get('facebook','key')
		self.facebook_secret=config.get('facebook','secret')
		config.read(os.path.split(os.path.realpath(__file__))[0]+'/../properties/users.ini')
                self.skip_list=config.get('notification','skip_notification').split(',')

	def getUserDetails(self, request_handler):
		
		#google_login_url = users.create_login_url('/') 
	        #twitter_logout_url = '/oauth/twitter/logout'

                twitter_cookie = request_handler.request.cookies.get('oauth.twitter')
        	evernote_user = OAuthClient('evernote', request_handler)
        	flickr_user = OAuthClient('flickr', request_handler)
        	screen_name=None
                avatar=None
		auth_service=None
                instaright_account=None
		# used to connect user details with session
		user_details_key=None
                evernote_username=None
                flickr_username=None

		google_user = users.get_current_user()
		#logging.info('trying to connect with fb key %s secret %s' %( self.facebook_key, self.facebook_secret))
        	facebook_user = facebook.get_user_from_cookie(request_handler.request.cookies, self.facebook_key, self.facebook_secret)
                facebook_access_token=None
                existing_user = None
        	if google_user:
                	screen_name=google_user.nickname()
			existing_user= UserDetails.gql('WHERE google_profile=\'%s\'' %google_user.email()).get()
			existing_user_by_mail = UserDetails.gql('WHERE mail=\'%s\'' %google_user.email()).get()
                        if self.ud is None:
                                self.ud = existing_user
                                if self.ud.mail is None:
                                        self.ud.mail = google_user.email()
                        #TODO what is both are not None and pointing to different entities
                        if existing_user is not None and existing_user_by_mail is not None and str(existing_user.key()) != str(existing_user_by_mail.key()):
                                logging.error('data inconsistancy for google user %s ' % google_user.email())
                        #NOTE: data consistency 
			if existing_user is None and existing_user_by_mail is not None:
                                existing_user_by_mail.google_profile = google_user.email()
                                existing_user_by_mail.put()
                                existing_user = existing_user_by_mail
                        if existing_user is None:
                                #TODO update google profile
				existing_user = UserDetails()
				existing_user.mail=google_user.email()
                                existing_user.google_profile=google_user.email()
                        elif existing_user.avatar is not None:
                                avatar = existing_user.avatar
				existing_user.mail=google_user.email()
                        existing_user.put()
			auth_service='google'
			user_details_key=existing_user.key()
			user_signup_badge = UserBadge.gql('WHERE user_property = :1 and badge = :2', existing_user.key(),'signup').get()
                        if user_signup_badge is None:
                                user_badge = UserBadge()
                                user_badge.user = screen_name
                                user_badge.badge = 'signup'
                                badge = Badges.gql('WHERE badge_label = :1', 'signup').get()
                                user_badge.badge_property = badge.key()
                                user_badge.user_property = existing_user.key()
                                user_badge.put()
                        instaright_account=existing_user.instaright_account
                elif twitter_cookie is not None and len(twitter_cookie) > 0:
			try:
                        	twitter_user = OAuthClient('twitter', request_handler)
				info = twitter_user.get('/account/verify_credentials')
                		screen_name = "%s" % info['screen_name']
				profile_image_url = "%s" %info['profile_image_url']
                                avatar=profile_image_url
				existing_user = UserDetails.gql('WHERE twitter = \'http://twitter.com/%s\'' % screen_name).get()
				if existing_user is None:
					logging.info('new twitter user login %s' % screen_name)
					existing_user=UserDetails()
					existing_user.twitter='http://twitter.com/%s' %screen_name
					existing_user.avatar = profile_image_url
				else:
					logging.info('existing twitter user login %s' % screen_name)
					if existing_user.avatar is None:
						existing_user.avatar = profile_image_url
                                        else:
                                                avatar = existing_user.avatar
                                existing_user.put()
				user_details_key=existing_user.key()
                                twitter_cookie = request_handler.request.cookies.get('oauth.twitter')
                                twitter_oauth = OAuthAccessToken.get_by_key_name(twitter_cookie)
                                if twitter_oauth is not None and existing_user is not None:
                                        twitter_token = twitter_oauth.oauth_token
                                        twitter_secret= twitter_oauth.oauth_token_secret
                                        taskqueue.add(url='/util/twitter/get_friends', params={'user_details_key': str(existing_user.key()),'user_token':twitter_token, 'user_secret': twitter_secret})
				auth_service='twitter'
                                logging.info('updating user score ...')
			        user_signup_badge = UserBadge.gql('WHERE user_property = :1 and badge = :2', existing_user.key(),'signup').get()
                                if user_signup_badge is None:
                                        user_badge = UserBadge()
                                        user_badge.user = screen_name
                                        user_badge.badge = 'signup'
                                        badge = Badges.gql('WHERE badge_label = :1', 'signup').get()
                                        user_badge.badge_property = badge.key()
                                        user_badge.user_property = existing_user.key()
                                        user_badge.put()
                                instaright_account=existing_user.instaright_account
			except:
				e0,e = sys.exc_info()[0], sys.exc_info()[1]
                                logging.error('got error while using twitter oauth: %s => %s' %(e0, e))
        	elif facebook_user:
                	graph = facebook.GraphAPI(facebook_user["access_token"])
			try:
                		profile = graph.get_object("me")
				profile_link=profile["link"]
				profile_id=profile["id"]
                		friends = graph.get_connections("me", "friends")
                		screen_name = profile["name"]
                                avatar='http://graph.facebook.com/%s/picture?typequare' % profile_id
				existing_user=UserDetails.gql('WHERE facebook = \'%s\'' % profile_link).get()
				if existing_user is not None:
					logging.info('existing facebook logging %s' % profile_link)
					existing_user.facebook=profile_link
					existing_user.facebook_friends=simplejson.dumps(friends)
					existing_user.facebook_profile=profile["name"]
					existing_user.facebook_id=profile_id
					if existing_user.avatar is None:
						existing_user.avatar = avatar
                                        else:
                                                avatar = existing_user.avatar
					existing_user.put()
				else:
					logging.info('new facebook logging %s' % profile_link)
					existing_user=UserDetails()
					existing_user.facebook=profile_link
					existing_user.facebook_profile=profile["name"]
					existing_user.facebook_friends=simplejson.dumps(friends)
					existing_user.facebook_id=profile_id
					existing_user.avatar = avatar
					existing_user.put()
				auth_service='facebook'
				user_details_key=existing_user.key()
			        user_signup_badge = UserBadge.gql('WHERE user_property = :1 and badge = :2', existing_user.key(),'signup').get()
                                if user_signup_badge is None:
                                        user_badge = UserBadge()
                                        user_badge.user = screen_name
                                        user_badge.badge = 'signup'
                                        badge = Badges.gql('WHERE badge_label = :1', 'signup').get()
                                        user_badge.badge_property = badge.key()
                                        user_badge.user_property = existing_user.key()
                                        user_badge.put()
                                instaright_account=existing_user.instaright_account
                                facebook_access_token=facebook_user["access_token"]
			except:
				e0,e = sys.exc_info()[0], sys.exc_info()[1]
				logging.info('error validating token %s === more info: %s' %(e0,e))
		
                if evernote_user.get_cookie() is not None and len(evernote_user.get_cookie()) > 0:
                        logging.info('evernote token active: %s' % evernote_user)
                        logging.info('evernote access token id: %s' % evernote_user.get_cookie())
                        evernote_access = evernote_user.get_cookie()
                        access_token = OAuthAccessToken.get_by_key_name(evernote_access)
                        if access_token is not None and access_token.service == 'evernote':
                                evernote_username = access_token.specifier
                                if existing_user is not None:
                                        existing_user.evernote_profile = evernote_username
                                        existing_user.put()
                        
                if flickr_user.get_cookie() is not None and len(flickr_user.get_cookie()) > 0:
                        logging.info('flickr token active: %s' % flickr_user)
                        logging.info('flickr access token id: %s' % flickr_user.get_cookie())
                        flickr_access = flickr_user.get_cookie()
                        access_token = OAuthAccessToken.get_by_key_name(flickr_access)
                        if access_token is not None and access_token.service == 'flickr':
                                flickr_username = access_token.specifier
                                if existing_user is not None:
                                        existing_user.flickr_profile = flickr_username
                                        existing_user.put()

		log_out_cookie = request_handler.request.cookies.get('user_logged_out')
		path=request_handler.request.path
		logging.info('path: %s' %path)
		#reset logout cookie in case of /account url
		if log_out_cookie and path == '/account':
			logging.info('deleting logout cookie')
                        expires = datetime.datetime.now()
                        exp_format = datetime.datetime.strftime(expires, '%a, %d-%b-%Y %H:%M:%S GMT')
			request_handler.response.headers.add_header('Set-Cookie', 'user_logged_out=%s; expires=%s; path=/' %( '0', exp_format))
			
		logging.info('user auth with %s: %s' %(auth_service, screen_name))
                if screen_name is not None and screen_name not in self.skip_list:
                        logging.info('user %s not in skip list %s ... sending mail' %(screen_name, str(self.skip_list)))
                        mail.send_mail(sender='gbabun@gmail.com', to='bojan@instaright.com', subject='User sign up!', html='Awesome new user signed up: %s <br>avatar <a href="%s"><img src="%s" width=20 height=20 /></a>' %( screen_name , avatar, avatar), body='Awesome new user signed up: %s avatar %s' %( screen_name, avatar))
                                        
                user_details = {'screen_name':screen_name, 'auth_service':auth_service, 'user_details_key':user_details_key, 'avatar':avatar, 'instaright_account':instaright_account,'facebook_access_token': facebook_access_token, 'evernote_name': evernote_username, 'flickr_name': flickr_username}
		return user_details

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
	@classmethod
	def getKloutScore(cls, user, klout_api_key):
		score = None
		logging.info('klout score for %s' % user)
		userDetails=UserDetails.gql('WHERE instapaper_account = :1' , user).get()
		if userDetails is None or userDetails.twitter is None:
                	logging.info(' trying get more info for user %s' % user)
                	userDetails = UserUtils.gather_info(user)
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
		

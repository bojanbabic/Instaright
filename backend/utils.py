import urllib
import logging
import urllib2
import datetime
import sys
import os
import ConfigParser
import struct
import base64
import hashlib
#urllib.getproxies_macosx_sysconf = lambda: {}
from google.appengine.api import memcache, mail
from models import UserDetails, DailyDomainStats, WeeklyDomainStats, LinkStats
from models import UserStats, SessionModel, UserBadge, CategoryDomains, LinkCategory, ScoreUsersDaily, Links
from models import Badges
from google.appengine.api import users
from google.appengine.api.labs import taskqueue
#from zbase62 import zbase62

sys.path.append(os.path.join(os.path.dirname(__file__),'lib'))
import facebook, simplejson
from oauth_handler import OAuthClient, OAuthAccessToken

class FeedUtil:
	def __init__(self):
		config=ConfigParser.ConfigParser()
		config.read(os.path.split(os.path.realpath(__file__))[0]+'/properties/general.ini')
		self.domain=config.get('app', 'domain')
	def sessionModel2Feed(self, model):
		item = {}
		item["title"]=model.domain
		item["link"]=self.domain+ '/article/' + str(model.key())
		item["description"]='Link submited by user %s' % model.instaright_account
		item["pubDate"]=model.date.timetuple()
		item["uid"]=str(model.key())

		return item
class LinkUtil(object):
        def __init__(self):
		config=ConfigParser.ConfigParser()
		config.read(os.path.split(os.path.realpath(__file__))[0]+'/properties/general.ini')
		key_key = ( datetime.datetime.now().day - 1 ) // 7 + 1
                self.embedly_key=config.get('embedly','key_'+ str(key_key))

        def getEmbededInfo(cls, url_hash):
                l = Links.gql('WHERE url_hash = :1', url_hash).get()
                if l is None or l.embeded is None:
                        return None
                return l.embeded
        def getLinkInfo(self, url):
                api_call="http://api.embed.ly/1/oembed?key="+urllib.quote(self.embedly_key)+"&url="+urllib.quote(url.encode('utf-8'))+"&maxwidth=500&format=json"
                json = LinkUtil.getJsonFromApi(api_call)
                title = LinkUtil.getJsonFieldSimple(json, "title")
                description = LinkUtil.getJsonFieldSimple(json, "description")
                image = LinkUtil.getJsonFieldSimple(json, "url")
                html = LinkUtil.getJsonFieldSimple(json, "html")
                type = LinkUtil.getJsonFieldSimple(json, "type")
                embeded = ""
                if image is not None and type == "photo":
                        embeded = '<a href="%s"><img src="%s" /></a>'  % ( url, image )
                if html is not None:
                        embeded = html
                return {"t":title,"d":description, "e": embeded}

        #deprecated
        @classmethod
        def getLinkTitle(cls,url):
                        title=None
                        try:
		                url=urllib2.quote(url.encode('utf-8'))
                                api_call="http://query.yahooapis.com/v1/public/yql?q=select%20*%20from%20html%20where%20url%3D%22"+url+"%22%20and%20xpath%3D'%2F%2Ftitle'&format=json&callback=" 
                                json = LinkUtil.getJsonFromApi(api_call)
                                title=json["query"]["results"]["title"]
                                if type(title) == list:
                                        logging.info('LIST')
                                        s_title=title[-1]
                                        title = s_title
                                if type(title) == dict:
                                        title=title['content']
                                        logging.info('DICT: %s' % title)
                                title = " ".join(title.splitlines())
                                title = (title.encode('ascii')).decode('utf-8')
                        except:
                                e0, e1 = sys.exc_info()[0], sys.exc_info()[1]
                                logging.info('title %s fetch failed... for %s error: %s ::: %s' %(title, url, e0, e1))
                        return title

        @classmethod
        def getJsonFieldSimple(cls, data, parameter=None):
                            field_value=None
                            if parameter is None:
                                logging.info('no parameter provided ... return None')
                                return None
                            try:
                                field_value = data[parameter]
                            except:
                                logging.info("error while retrieving parameter %s from data %s" %( parameter, data))
                            return field_value
                        
        def getFeedOriginalUrl(self,url):
                try:
                        req=urllib2.Request(url)
                        o=urllib2.build_opener()
                        f=o.open(req)
                        return f.url
                except:
                        logging.info('error while fetching feed orig url %s' % url)
                        return None
        def getShortOriginalUrl(self, url):
                try:
                        bitlylink='http://api.bit.ly/v3/expand?shortUrl='+urllib.quote(url)+'&login=bojanbabic&apiKey=R_62dc6488dc4125632884f32b84e7572b&hash=in&format=json'
                        data=urllib2.urlopen(bitlylink)
                        json=simplejson.load(data)
                        long_url=json["data"]["expand"][0]["long_url"]
                        return long_url
                except:
                        logging.info('could not shorten url %s' %url)
                        return None
        def shortenLink(self, url):
                try:
                       url = 'http://links.instaright.com/a947824b599193b3/?web=058421&dst='+url;
                       link='http://api.bit.ly/v3/shorten?longUrl='+urllib.quote(unicode(url))+'&login=bojanbabic&apiKey=R_62dc6488dc4125632884f32b84e7572b&hash=in&format=json'  
                       data=urllib2.urlopen(link)
                       json=simplejson.load(data)
                       short_url = json["data"]["url"]
                       return short_url
                except:
                        logging.info('could not short url %s' %unicode(url))
                        return None
        @classmethod
        def getUrlHash(cls, url):
                return base64.b64encode(hashlib.sha1(unicode(url).encode('utf-8')).digest())[:-1]
        def updateStats(self, s):
                dailyStats = DailyDomainStats.gql('WHERE domain = :1 and date = :2', s.domain, s.date).get()
                if dailyStats is not None:
                        dailyStats.count += 1
                        logging.info('updating daily stats count %s' % dailyStats.count)
                else:
                        logging.info('daily stats new domain: %s for date %s' %(s.domain, s.date))
                        dailyStats = DailyDomainStats()
                        dailyStats.domain = s.domain
                        dailyStats.count = 1
                        dailyStats.date = s.date.date()
                dailyStats.put()
                
                dow = s.date.weekday()
                if dow == 0:
                        #mon
                        date = s.date + datetime.timedelta(days=1)
                elif dow == 1:
                       #tue day of stats  
                        date = s.date 
                elif dow == 2:
                       #wed check next tues
                        date = s.date + datetime.timedelta(days=6)
                elif dow == 3:
                       #thu check next tues
                        date = s.date + datetime.timedelta(days=5)
                elif dow == 4:
                       #fri check next tues
                        date = s.date + datetime.timedelta(days=4)
                elif dow == 5:
                       #sat check next tues
                        date = s.date + datetime.timedelta(days=3)
                elif dow == 6:
                       #sun check next tues
                        date = s.date + datetime.timedelta(days=2)

                weeklyStats = WeeklyDomainStats.gql('WHERE domain = :1 and date = :2', s.domain, date).get()
                if weeklyStats is not None:
                        weeklyStats.count += 1
                        logging.info('updating weekly stats count %s' % weeklyStats.count)
                else:
                        logging.info('weekly stats new domain: %s for date %s' %(s.domain, str(date.date())))
                        weeklyStats = WeeklyDomainStats()
                        weeklyStats.domain = s.domain
                        weeklyStats.count = 1
                        weeklyStats.date = date.date()
                #weeklyStats.put()
                        
                linkStats = LinkStats.gql('WHERE link = :1', s.url).get()
                if linkStats is not None:
                        linkStats.count += 1
                        linkStats.countUpdated = datetime.datetime.now() 
                        linkStats.lastUpdatedBy = s.instaright_account
                        logging.info('updated link stats %s' % linkStats.count)
                else:
                        logging.info('new stat in link stats')
                        linkStats = LinkStats()
                        linkStats.count = 1
                        linkStats.link = s.url
                        linkStats.lastUpdatedBy = s.instaright_account
                linkStats.put()
        @classmethod
        def getJsonFromApi(cls,url):
                try:
                        dta = urllib2.urlopen(url)
                        json = simplejson.load(dta)
                        return json
                except:
                        logging.info('error while getting link %s reTRYing'  % url)
                	try:
                        	dta = urllib2.urlopen(url)
                        	json = simplejson.load(dta)
                        	return json
                	except:
                        	e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                        	logging.info('error %s %s, while getting link %s'  %( e0, e1, url))
                        	return None

        @classmethod
        def generateUrlTitle(cls, title):
                   return title


class Cast:
        @classmethod
        def toInt(cls, string, default):
                try:
                        return int(string)
                except ValueError:
                        logging.info('int parse error return default value %s' % default)
                        return default

        @classmethod
        def toFloat(cls, string, default):
                try:
                        return float(string)
                except:
                        return default
                
BADGES_VERSION={'0.4.0.4':['news','yen','movie', 'robot']}
TRESHOLD_VERSION='0.4.0.4'
class Version:
        @staticmethod
        def validateVersion(version,badge):
                if version is None:
                        logging.info('Older version of addon!')
                        return False
                logging.info('checking version %s ' % version)
                compRes=Version.compareVersions(version, TRESHOLD_VERSION)
                # all versions after 0.4.0.4 should be able to handle all badges
                if compRes >= 0:
                        logging.info('valid version allowing badge %s' % badge)
                        return True
                badges=BADGES_VERSION[version]
                if badges is not None and badge in badges:
                        logging.info('valid badge %s for version %s' %( badge, version))
                        return True
                else:
                        logging.info('can\'t find badges for %s' % version)
                logging.info('Older version of addon!')
                return False
                
        @staticmethod
        def compareVersions(v1, v2):
                if v1 is None and v2 is not None:
                        return -1
                if v1 is not None and v2 is None:
                        return 1
                if v1 is None and v2 is None:
                        return 0
                #v1Tokens=v1.split('.')
                #v2Tokens=v2.split('.')
                for x,y in zip(v1, v2):
                        if x < y: return -1
                        if x > y: return 1
                return 0

class LoginUtil():
	def __init__(self):
		config=ConfigParser.ConfigParser()
		config.read(os.path.split(os.path.realpath(__file__))[0]+'/properties/general.ini')
		self.facebook_key=config.get('facebook','key')
		self.facebook_secret=config.get('facebook','secret')
		config.read(os.path.split(os.path.realpath(__file__))[0]+'/properties/users.ini')
                self.skip_list=config.get('notification','skip_notification').split(',')

        @classmethod
        def create_urls(cls, federated_domains):
                login_div='<div>'
                for d in federated_domains:
                        d_name = d.split('.')[0]
                        d_url = d.lower()
                        login_div += '<p><a href="%s">%s</a></p>' %( users.create_login_url(federated_identity = d_url), d_name)
                login_div +='</div>'
                return login_div

	def getUserDetails(self, request_handler):
		
		#google_login_url = users.create_login_url('/') 
	        #twitter_logout_url = '/oauth/twitter/logout'

        	twitter_user = OAuthClient('twitter', request_handler)
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
			if existing_user is None and existing_user_by_mail is not None:
                                existing_user_by_mail.google_profile = google_user.email()
                                existing_user_by_mail.put()
                                existing_user = existing_user_by_mail
                        if existing_user is None:
                                #TODO update google profile
				existing_user = UserDetails()
				existing_user.mail=google_user.email()
                                existing_user.google_profile=google_user.email()
				existing_user.put()
                        elif existing_user.avatar is not None:
                                avatar = existing_user.avatar
				existing_user.mail=google_user.email()
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
        	elif twitter_user.get_cookie():
			try:
				info = twitter_user.get('/account/verify_credentials')
                		following = twitter_user.get('/friends/ids')
                		followers = twitter_user.get('/followers/ids')
                		screen_name = "%s" % info['screen_name']
				profile_image_url = "%s" %info['profile_image_url']
                                avatar=profile_image_url
				existing_user = UserDetails.gql('WHERE twitter = \'http://twitter.com/%s\'' % screen_name).get()
				if existing_user is None:
					logging.info('new twitter user login %s' % screen_name)
					ud=UserDetails()
					ud.twitter_followers=simplejson.dumps(followers)
					ud.twitter_following=simplejson.dumps(following)
					ud.twitter='http://twitter.com/%s' %screen_name
					ud.avatar = profile_image_url
					ud.put()
				else:
					logging.info('existing twitter user login %s' % screen_name)
					existing_user.twitter_followers=simplejson.dumps(followers)
					existing_user.twitter_following=simplejson.dumps(following)
					if existing_user.avatar is None:
						existing_user.avatar = profile_image_url
                                        else:
                                                avatar = existing_user.avatar
					existing_user.put()
				auth_service='twitter'
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
			except:
				e0,e = sys.exc_info()[0], sys.exc_info()[1]
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

class TaskUtil(object):
	@classmethod
	def execution_time(cls):
		
		# best time for tweet 1 PM EEST 4 AM EEST 2 AM EEST 2 PM EEST 9 AM PST( 7 PM EEST)
		(year, month, day, hour, min, sec)=datetime.datetime.now().timetuple()[:6]
		logging.info('calculating tweet execution time. now %s' % str(datetime.datetime.now()))
		ss_1=datetime.datetime(year, month, day, 0, 0, 0)
		ss_2=datetime.datetime(year, month, day, 5, 0, 0)
		ss_3=datetime.datetime(year, month, day, 10, 0, 0)
		ss_4=datetime.datetime(year, month, day, 15, 0, 0)
		ss_5=datetime.datetime(year, month, day, 22, 0, 0)
		now=datetime.datetime.now()
		if now < ss_1:
			return ss_1
		if now < ss_2:
			return ss_2
		if now < ss_3:
			return ss_3
		if now < ss_4:
			return ss_4
		if now < ss_5:
			return ss_5
		else:
			return ss_1
class CategoriesUtil(object):
        @classmethod
        def processDomainCategories(cls, categories, domain):
                if categories is None or len(categories) == 0:
                        logging.info('missing categories. skipping')
                        return
		cat_dict = eval(categories)
		if len(cat_dict) == 0:
			logging.info('no categories. skipping')
			return
		for cat, cnt in cat_dict.iteritems():
			catDomains=CategoryDomains.gql('WHERE category = :1' , cat).get()
			if catDomains is None:
				logging.info('new category %s , init domain %s' % (cat, domain))
				catDomains = CategoryDomains()
				catDomains.category = cat
				catDomains.domains = domain
				catDomains.put()
			else:
				domainsArray = catDomains.domains.split(',')
				if domain in domainsArray:
					logging.info('category %s already contains domain %s' % ( cat, domain))
				else:
					if domainsArray is None:
						domainsArray = []
					domainsArray.append(domain)
					catDomains.domains = ','.join(domainsArray)
                                        logging.info('updated category %s [ %s ]' % (cat, catDomains.domains))
					catDomains.put()
        @classmethod
        def processLinkCategoriesFromJson(cls, categories, url):
                if categories is None or len(categories) == 0:
                        logging.info('missing categories. skipping')
                        return
		cat_dict = eval(categories)
		if len(cat_dict) == 0:
			logging.info('no categories. skipping')
			return
		for cat, cnt in cat_dict.iteritems():
                        existingCategory=LinkCategory.gql('WHERE category = :1 and url = :2' , cat, url).get()
			if existingCategory is None:
				logging.info('new category %s , init url %s' % (cat, url))
				linkCategory = LinkCategory()
				linkCategory.category = cat
				linkCategory.url = url
				linkCategory.put()
			else:
                                logging.info('updated time for category %s [ %s ]' % (cat, existingCategory.url))
                                existingCategory.updated = datetime.datetime.now()
				existingCategory.put()

class UserScoreUtility(object):
        @classmethod
        def getCurrentScore(cls, user):
                if user is None:
                        return None
                userDetails = UserDetails.gql('WHERE  instaright_account = :1', user).get()
                if userDetails is None:
                        logging.info('no user with instaright account %s' % user)
                        userDetails = UserDetails.gql('WHERE  instapaper_account = :1', user).get()
                        if userDetails is None:
                                userDetails=UserDetails()
                                userDetails.instapaper_account=user
                        userDetails.instaright_account=user
                        userDetails.put()
                now =datetime.datetime.now().date()
                currentScore=ScoreUsersDaily.gql('WHERE user = :1 and date = :2', userDetails.key(), now).get()
                if currentScore is None:
                        currentScore = ScoreUsersDaily()
                        currentScore.user=userDetails.key()
                        currentScore.date = now
                return currentScore
                
        @classmethod
        def badgeScore(cls, user, badge):
                score=0
                if user is None or badge is None:
                        logging.info('no user no score or no badge no score')
                        return score
                if badge in ['1000','5000','10000']:
                        logging.info(' %s badge not uncluded into score')
                        return score
                logging.info('badge score calc for user %s' %user)
                badge_cache='score_for_badge_'+user+'_'+badge+'_'+str(datetime.datetime.now().date())
                badge_added=memcache.get(badge_cache)
                if badge_added:
                        logging.info('badge already included in scoring. skipping')
                        return score
                #TODO what is this doing here
                #currentScore=UserScoreUtility.getCurrentScore(user)
                config=ConfigParser.ConfigParser()
	        config.read(os.path.split(os.path.realpath(__file__))[0]+'/properties/score.ini')
                score=int(config.get('badge_point',badge))
                return score

        @classmethod
        def domainScore(cls,user, domain):
                score=0
                if user is None or domain is None:
                                     logging.info('domain score not enpugh data ... skipping')
                                     return score
                logging.info('domain score calc for for user %s' %user)
                config=ConfigParser.ConfigParser()
	        config.read(os.path.split(os.path.realpath(__file__))[0]+'/properties/score.ini')
                domain_points=int(config.get('domain_points','new_domain'))
                domain_memcache_key='visit_'+user+'_domain_'+domain
                visitedDomain=memcache.get(domain_memcache_key)
                if visitedDomain is None:
                        visitedDomain=SessionModel.gql('WHERE domain = :1 and instaright_account = :2', domain, user).get()
                if visitedDomain is None:
                        logging.info('new domain %s score for %s ' %(domain, user))
                        score=domain_points
                        memcache.set(domain_memcache_key, '1')
                else:
                        logging.info('user %s already visited domain %s ' %(user, domain))
                return score

        @classmethod
        def linkScore(cls,user, link):
                score=0
                if user is None or link is None:
                                     logging.info('link score not enpugh data ... skipping')
                                     return score
                logging.info('link score ...')
                config=ConfigParser.ConfigParser()
	        config.read(os.path.split(os.path.realpath(__file__))[0]+'/properties/score.ini')
                link_points=int(config.get('link_points','new_link'))
                link_memcache_key='visit_'+user+'_domain_'+link
                visitedLink=memcache.get(link_memcache_key)
                if visitedLink is None:
                        try:
                                visitedLink=SessionModel.gql('WHERE url = :1 and instaright_account = :2', link, user).get()
                        except:
                                logging.info('expection fetching %s' % link)
                if visitedLink is None:
                        logging.info('new link %s score for %s ' %(link, user))
                        score=link_points
                        memcache.set(link_memcache_key, '1')
                else:
                        logging.info('user %s already visited link %s ' %(user, link))
                return score
        @classmethod
        def updateLinkScore(cls,user,link):
                if user is None:
                        logging.info('no user no link score')
                        return
                currentScore=UserScoreUtility.getCurrentScore(user)
                linkPoints=UserScoreUtility.linkScore(user, link)
                logging.info('update score user %s score %s for link %s' %(user, linkPoints, link))
                currentScore.score+=linkPoints
                currentScore.put()
                taskqueue.add(url='/user/score/update/task', queue_name='score-queue', params={'user':user})

        @classmethod
        def updateDomainScore(cls,user,domain):
                if user is None:
                        logging.info('no user no domain score')
                        return
                currentScore=UserScoreUtility.getCurrentScore(user)
                domainPoints=UserScoreUtility.domainScore(user, domain)
                logging.info('update score user %s score %s for domain %s' %(user, domainPoints, domain))
                currentScore.score+=domainPoints
                currentScore.put()
                taskqueue.add(url='/user/score/update/task', queue_name='score-queue', params={'user':user})

        @classmethod
        def updateBadgeScore(cls,user,badge):
                if user is None:
                        logging.info('no user no badge score')
                        return
                currentScore=UserScoreUtility.getCurrentScore(user)
                badgePoints=UserScoreUtility.badgeScore(user, badge)
                logging.info('update score user %s score %s for badge %s' %(user, badgePoints, badge))
                currentScore.score+=badgePoints
                currentScore.put()
                taskqueue.add(url='/user/score/update/task', queue_name='score-queue', params={'user':user})

        @classmethod
        def updateScore(cls, user, domain, link, badge):
                if user is None:
                        logging.info('no user no score')
                        return
                        
                currentScore=UserScoreUtility.getCurrentScore(user)
                linkPoints=UserScoreUtility.linkScore(user, link)
                domainPoints=UserScoreUtility.domainScore(user,domain)
                badgePoints=UserScoreUtility.badgeScore(user, badge)
                currentScore.score+=linkPoints + domainPoints + badgePoints
                currentScore.put()
                #overAllScore=UserScoreUtility.getOverAllScore(user)
                #overAllScore.score += currentScore.score
                #overAllScore.put()
class EnriptionUtil(object):
        @classmethod
        def encode_url(cls, string):
                data = struct.pack('{{}}', string).rstrip('\x00')
                if len(data) == 0:
                        data='\x00'
                s=base64.urlsafe_b64encode(data).rstrip('=')
                return s
        @classmethod
        def decode_url(cls, string):
                data = base64.urlsafe_b64decode(string + '==')
                n = struct.unpack('{{}}', data, '\x00'*(8-len(data)))
                return n[0]

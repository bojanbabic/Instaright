import urlparse, urllib,logging, urllib2, datetime, sys, os, ConfigParser
#urllib.getproxies_macosx_sysconf = lambda: {}
from google.appengine.api import memcache, mail
from xml.dom import minidom
from models import UserDetails, DailyDomainStats, WeeklyDomainStats, LinkStats, UserStats, SessionModel, UserBadge, CategoryDomains, LinkCategory
from google.appengine.api import users

sys.path.append(os.path.join(os.path.dirname(__file__),'lib'))
import facebook, simplejson
from oauth_handler import OAuthHandler, OAuthClient

class StatsUtil(object):
	@classmethod
	def getDomain(cls, url):
		domain = None
		try:
			urlobject=urlparse.urlparse(url)
			domain = urlobject.netloc
		except:
			e0,e = sys.exc_info()[0], sys.exc_info()[1]
			logging.info('domain was not fetched due to: %s , %s' %(e0, e)) 
			
		# domain should not contain spaces
		if domain is None or domain.find(' ') != -1:
			return None
		#strip www.
		if domain.startswith('www.'):
			domain = domain.replace('www.','')
		return domain
	
        @classmethod
        def getTitle(cls, args):
                title = None
                try:
                    title = urllib2.unquote(args[2].encode('ascii')).decode('utf-8')
                    if title == "null":
                            raise Exception('null title from request')
                except:
                    e0, e1 = sys.exc_info()[0], sys.exc_info()[1]
                    logging.info('title value error: %s ::: %s' %(e0, e1))
                return title

        @classmethod
        def getVersion(cls, args):
                version = ""
                try:
		        version=urllib2.unquote(args[3])
                        int(version[0])
                except:
                        e0, e1 = sys.exc_info()[0], sys.exc_info()[1]
                        logging.info('version error: %s ::: %s' %(e0, e1))
                return version
        @classmethod
        def getClient(cls, args):
                client = "firefox"
                try:
                        client = urllib2.unquote(args[4])
                except:
                        e0, e1 = sys.exc_info()[0], sys.exc_info()[1]
                return client


        @classmethod
        def checkUrl(cls, args):
                url = cls.getUrl(args)
                if url is None:
                       return False
                if url.startswith('file://') or url.startswith('chrome://') or url.startswith('about:') or url.startswith('ed2k:') or url.startswith('liberator:') or url.startswith('irc:'):
                        logging.info('url not good: %s ' % url)
                        return False
                return True

        @classmethod
        def getUrl(cls, args):
                try:
                        return urllib2.unquote(args[1])
                except:
                        return None

        @classmethod
        def getUser(cls, args):
                try:
                        return args[0]
                except:
                        return None


	@classmethod
	def ipResolverAPI(cls, ip):
		data = []
                try:
		        apiCall="http://api.hostip.info/get_xml.php?ip="+ip
        		dom = minidom.parse(urllib.urlopen(apiCall))
        		city = dom.getElementsByTagName('gml:name')[1].firstChild.nodeValue
        		country = dom.getElementsByTagName('countryAbbrev')[0].firstChild.nodeValue
        		data.append(city)
        		data.append(country)
                except:
                        logging.info('error while getting ip state / city')
		#xml = libxml2.parseDoc(urllib2.urlopen(req).read())
		#data = [x.content for x in xml.xpathEval('//Hostip/node()')]	
		return data
		# TODO  parse xml 
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
class LinkUtil:
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
                       link='http://api.bit.ly/v3/shorten?longUrl='+urllib.quote(url)+'&login=bojanbabic&apiKey=R_62dc6488dc4125632884f32b84e7572b&hash=in&format=json'  
                       data=urllib2.urlopen(link)
                       json=simplejson.load(data)
                       short_url = json["data"]["url"]
                       return short_url
                except:
                        logging.info('could not expand short url %s' %url)
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


class BadgeUtil:

        @staticmethod
        def getBadger(user, url, domain, version):
               trophyBadger=TrophyBadger(user, url, domain, version)
               logging.info('getting proper badger for %s and domain %s (version %s)' %( user, domain , version))
               if trophyBadger.getBadge() is not None:
                        logging.info('initializing trophy badger')
                        return trophyBadger
	       siteSpecBadge=SiteSpecificBadge(user, url, domain, version)	
               if version is not None and siteSpecBadge.getBadge() is not None:
                        logging.info('initializing site specific badger: %s' %domain)
                        return 
               speedLimitBadger=SpeedLimitBadger(user, url, domain, version)
               clubBadger=ClubBadger(user, url, domain, version)
               if speedLimitBadger.getBadge() is not None:
                        logging.info('initializing speed limit badger')
                        return speedLimitBadger
               if clubBadger.getBadge() is not None:
                        logging.info('initializing club badger')
                        return clubBadger
               usageBadge=ContinuousUsageBadge(user, url, domain, version)
               if usageBadge.getBadge() is not None:
                        logging.info('initializing usage badger')
                        return usageBadge
               return None
                
class ContinuousUsageBadge:
        def __init__(self, user, url, domain, version):
                self.user = user
                self.url = url
                self.domain = domain
                self.version=version
        def getBadge(self):
                returnBadge=5
                existingBadge=UserBadge.gql('WHERE user = :1 and badge = :2', self.user, returnBadge).get()
                if existingBadge is  not None:
                        logging.info('Already assigned 5 day usage badge. Skipping.')
                        return None
                if self.version is None:
                        logging.info('Older version of addon not usage badge defined!')
                        return None
                yesterday=datetime.datetime.now().date() - datetime.timedelta(days=1)
                limit=datetime.datetime.now().date() - datetime.timedelta(days=4)
                active=True
                while yesterday >= limit:
                       s=SessionModel.gql('WHERE date = :1 and instaright_account = :2', yesterday, self.user).get()
                       if s is None:
                                logging.info('user %s NOT active for date %s' %(self.user, yesterday))
                                active=False
                                return None
                       else:
                                logging.info('user %s active for date %s' %(self.user, yesterday))
                       yesteday-=datetime.timedelta(days=1)
                if active:        
                        logging.info('user %s has been active in last %s' %(self.user, returnBadge))
                        return '5'
                logging.info('usage badge %s: not initialized' %self.user)
class SpeedLimitBadger:
        def __init__(self, user, url, domain, version):
                self.user = user
                self.url = url
                self.domain = domain
                self.version=version
        def getBadge(self):
               midnight = datetime.datetime.now().date()
               currentCount=SessionModel.gql('WHERE date >= :1 and instaright_account = :2', midnight, self.user).count()
               logging.info('current daily user count : %s -> %s' %(self.user, currentCount))
               if currentCount >= 105:
                        return '105'
               if currentCount >= 65:
                        return '65'
               if currentCount >= 55:
                        return '55'
               if currentCount >= 25:
                        return '25'
               logging.info('speed limit badge %s: not initialized' %self.user)
               return None
                
class SiteSpecificBadge(object):
	newsProps=ConfigParser.ConfigParser()
	movieProps=ConfigParser.ConfigParser()
	nyProps=ConfigParser.ConfigParser()
	economyProps=ConfigParser.ConfigParser()
	gadgetProps=ConfigParser.ConfigParser()
	wikiProps=ConfigParser.ConfigParser()
	sportProps=ConfigParser.ConfigParser()
        def __init__(self, user, url, domain, version):
                self.user = user
                self.url = url
                self.domain = domain
                self.version=version
		#read domain lists
		self.newsProps.read(os.path.split(os.path.realpath(__file__))[0]+'/properties/badges/news/news.properties')
		self.newsDomains=self.newsProps.get('news','domains').split(',')
		self.news_tresshold=int(self.newsProps.get('news','tresshold'))

		self.movieProps.read(os.path.split(os.path.realpath(__file__))[0]+'/properties/badges/movie/movie.properties')
		self.movieDomains=self.movieProps.get('movie','domains').split(',')
		self.movie_tresshold=int(self.movieProps.get('movie','tresshold'))

		self.nyProps.read(os.path.split(os.path.realpath(__file__))[0]+'/properties/badges/ny/ny.properties')
		self.nyDomains=self.nyProps.get('ny','domains').split(',')
		self.ny_tresshold=int(self.nyProps.get('ny','tresshold'))

		self.economyProps.read(os.path.split(os.path.realpath(__file__))[0]+'/properties/badges/economy/economy.properties')
		self.economyDomains=self.economyProps.get('economy','domains').split(',')
		self.economy_tresshold=int(self.economyProps.get('economy','tresshold'))

		self.gadgetProps.read(os.path.split(os.path.realpath(__file__))[0]+'/properties/badges/gadget/gadget.properties')
		self.gadgetDomains=self.gadgetProps.get('gadget','domains').split(',')
		self.gadget_tresshold=int(self.gadgetProps.get('gadget','tresshold'))

		self.wikiProps.read(os.path.split(os.path.realpath(__file__))[0]+'/properties/badges/wiki/wiki.properties')
		self.wikiDomains=self.wikiProps.get('wiki','domains').split(',')
		self.wiki_tresshold=int(self.wikiProps.get('wiki','tresshold'))

		self.sportProps.read(os.path.split(os.path.realpath(__file__))[0]+'/properties/badges/sport/sport.properties')
		self.sportDomains=self.sportProps.get('sport','domains').split(',')
		self.sport_tresshold=int(self.sportProps.get('sport','tresshold'))

        def getBadge(self):
                if self.domain in self.nyDomains:
                        return self.getnytbadge()
                if self.domain in self.movieDomains:
                        return self.getmoviebadge()
                if self.domain in self.economyDomains:
                        return self.geteconomybadge()
                if self.domain in self.gadgetDomains:
                        return self.getgadgetbadge()
                if self.domain in self.sportDomains:
                        return self.getsportbadge()
                if self.domain in self.wikiDomains:
                        return self.getwikibadge()
                if self.domain in self.newsDomains:
                        return self.getnewsbadge()
                else:
                        logging.info('no domain specific badge initialized or no addon version')
                        return None
        def getnytbadge(self):
               midnight = datetime.datetime.now().date()
               nyTotal=SessionModel.gql('where domain in :1 and date >= :2 and instaright_account = :3', self.nyDomains, midnight, self.user).count()
               logging.info('site specific badger(NY): fetched stats %s' % nyTotal)
               if nyTotal >= self.ny_tresshold:
                        logging.info('setting ny badge for user %s ' %self.user)
                        return 'ny'
               else:
                        logging.info('for user %s still tresshold of %s still not reached %s' %(self.user, self.ny_tresshold, nyTotal))
                        return None
        def getmoviebadge(self):
               midnight = datetime.datetime.now().date()
               currentCount=SessionModel.gql('where domain in :1 and date >= :2 and instaright_account = :3', self.movieDomains, midnight, self.user).count()
               logging.info('site specific badger(movie): fetched stats %s' % currentCount)
               if currentCount >= self.movie_tresshold:
                        logging.info('setting movie badge for user %s ' %self.user)
                        return 'movie'
               else:
                        logging.info('for user %s still tresshold of %s still not reached %s' %(self.user, self.movie_tresshold, currentCount))
                        return None
        def geteconomybadge(self):
               midnight = datetime.datetime.now().date()
               currentCount=SessionModel.gql('where domain in :1 and date >= :2 and instaright_account = :3', self.economyDomains, midnight, self.user).count()
               logging.info('site specific badger(economy): fetched stats %s' % currentCount)
               if currentCount >= self.economy_tresshold:
                        logging.info('setting economy badge for user %s ' %self.user)
                        return 'yen'
               else:
                        logging.info('for user %s still tresshold of %s still not reached %s' %(self.user, self.economy_tresshold, currentCount))
                        return None
        def getgadgetbadge(self):
               midnight = datetime.datetime.now().date()
               currentCount=SessionModel.gql('where domain in :1 and date >= :2 and instaright_account = :3', self.gadgetDomains, midnight, self.user).count()
               logging.info('site specific badger(gadget): fetched stats %s' % currentCount)
               if currentCount >= self.gadget_tresshold:
                        logging.info('setting gadget badge for user %s ' %self.user)
                        return 'robot'
               else:
                        logging.info('for user %s still tresshold of %s still not reached %s' %(self.user, self.gadget_tresshold, currentCount))
                        return None
        def getnewsbadge(self):
               midnight = datetime.datetime.now().date()
               currentCount=SessionModel.gql('where domain in :1 and date >= :2 and instaright_account = :3', self.newsDomains, midnight, self.user).count()
               logging.info('site specific badger(news): fetched stats %s' % currentCount)
               if currentCount >= self.news_tresshold:
                        logging.info('setting news badge for user %s ' %self.user)
                        return 'news'
               else:
                        logging.info('for user %s still tresshold of %s still not reached %s' %(self.user, self.news_tresshold, currentCount))
                        return None

        def getwikibadge(self):
               midnight = datetime.datetime.now().date()
               currentCount=SessionModel.gql('where domain in :1 and date >= :2 and instaright_account = :3', self.wikiDomains, midnight, self.user).count()
               logging.info('site specific badger(wiki): fetched stats %s' % currentCount)
               if currentCount >= self.wiki_tresshold:
                        logging.info('setting wiki badge for user %s ' %self.user)
                        return 'news'
               else:
                        logging.info('for user %s still tresshold of %s still not reached %s' %(self.user, self.wiki_tresshold, currentCount))
                        return None

        def getsportbadge(self):
               midnight = datetime.datetime.now().date()
               currentCount=SessionModel.gql('where domain in :1 and date >= :2 and instaright_account = :3', self.sportDomains, midnight, self.user).count()
               logging.info('site specific badger(sport): fetched stats %s' % currentCount)
               if currentCount >= self.sport_tresshold:
                        logging.info('setting news badge for user %s ' %self.user)
                        return 'sport'
               else:
                        logging.info('for user %s still tresshold of %s still not reached %s' %(self.user, self.sport_tresshold, currentCount))
                        return None

class ClubBadger:
        def __init__(self, user, url, domain, version):
                self.user = user
                self.url = url
                self.domain = domain
                self.version=version
        def getBadge(self):
                allForUser=SessionModel.all()
                allForUser.filter("instaright_account =", self.user)
                count=allForUser.count(10000)
                logging.info('club badger: fetched stats %s' % count)
                if count >= 10000:
                        return '10000'
                if count >= 5000:
                        return '5000'
                if count >= 1000:
                        return '1000'
                logging.info('club badger %s: not initialized' % self.user )
                return None
class TrophyBadger:
        def __init__(self, user, url, domain, version):
                self.user = user
                self.url = url
                self.domain = domain
                self.version=version
        def getBadge(self):
                targetdate=datetime.datetime.now().date() - datetime.timedelta(days=1)
                stats = UserStats.gql('WHERE date = :1 and count > 10 order by count desc', targetdate).fetch(3)
                logging.info('trophy badger: fetched stats %s' % len(stats))
		stats = [ s.instapaper_account for s in stats if s is not None ]
                if stats is None or len(stats) == 0:
			logging.info('Not enough data for calc badge')
			return None
                if stats[0] == self.user:
			logging.info('User was number ONE user yesterday')
                        return '1'
                if stats[1] == self.user:
			logging.info('User was number TWO user yesterday')
                        return '2'
                if stats[2] == self.user:
			logging.info('User was number THREE user yesterday')
                        return '3'
                logging.info('trophy badge %s: not initialized' % self.user )
                return None

                 
class Cast:
        @classmethod
        def toInt(cls, string, default):
                try:
                        return int(string)
                except ValueError:
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
                        logging.info('valid badge %s for version %s' %( bVersions[version], version))
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
                v1Tokens=v1.split('.')
                v2Tokens=v2.split('.')
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
		
		google_login_url = users.create_login_url('/') 
	        twitter_logout_url = '/oauth/twitter/logout'

        	twitter_user = OAuthClient('twitter', request_handler)
        	logged=False
        	screen_name=None
                avatar=None
		auth_service=None
		# used to connect user details with session
		user_details_key=None

		google_user = users.get_current_user()
		logging.info('trying to connect with fb key %s secret %s' %( self.facebook_key, self.facebook_secret))
        	facebook_user = facebook.get_user_from_cookie(request_handler.request.cookies, self.facebook_key, self.facebook_secret)
        	if google_user:
                	logged=True
                	screen_name=google_user.nickname()
			existing_user= UserDetails.gql('WHERE mail=\'%s\'' %google_user.email()).get()
			if existing_user is None:
				existing_user = UserDetails()
				existing_user.mail=google_user.email()
				existing_user.put()
                        elif existing_user.avatar is not None:
                                avatar = existing_user.avatar
			auth_service='google'
			user_details_key=existing_user.key()
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
			except:
				e0,e = sys.exc_info()[0], sys.exc_info()[1]
				logging.info('error validating token %s === more info: %s' %(e0,e))
		
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
                                        
                user_details = {'screen_name':screen_name, 'auth_service':auth_service, 'user_details_key':user_details_key, 'avatar':avatar}
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

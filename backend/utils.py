import urlparse, urllib,logging, urllib2, datetime, simplejson
from google.appengine.api import memcache
from xml.dom import minidom
from models import UserDetails, DailyDomainStats, WeeklyDomainStats, LinkStats, UserStats, SessionModel, UserBadge
DOMAIN='http://instaright.appspot.com'
class StatsUtil():
	@staticmethod
	def getDomain(url):
		urlobject=urlparse.urlparse(url)
		try:
			domain = urlobject.netloc
		except:
			e0,e = sys.exc_info()[0], sys.exc_info()[1]
			logging.info('domain was not fetched due to: %s , %s' %(e0, e)) 
			
		# domain should not contain spaces
		if not domain or domain.find(' ') != -1:
			return None
		#strip www.
		if domain.startswith('www.'):
			domain = domain.replace('www.','')
		return domain
	
	@staticmethod
	def ipResolverAPI(ip):
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
	def sessionModel2Feed(self, model):
		item = {}
		item["title"]=model.domain
		item["link"]=DOMAIN + '/article/' + str(model.key())
		item["description"]='Link submited by user %s' % model.instaright_account
		item["pubDate"]=model.date.timetuple()
		item["uid"]=str(model.key())

		return item
class UserUtil:
        def getAvatar(self,instapaper_account):
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
                        logging.info('could not expand short url %s' %url)
                        return None
        def shortenLink(self, url):
                try:
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

class BadgeUtil:
        global DOMAIN_SPECIFIC_BADGES
        DOMAIN_SPECIFIC_BADGES=['nytimes.com']
        @staticmethod
        def getBadger(user, url, domain):
               trophyBadger=TrophyBadger(user, url, domain)
               if trophyBadger.getBadge() is not None:
                        logging.info('initializing trophy badger')
                        return trophyBadger
               if domain in DOMAIN_SPECIFIC_BADGES:
                        logging.info('initializing site specific badger: %s' %domain)
                        return SiteSpecificBadge(user, url, domain)
               speedLimitBadger=SpeedLimitBadger(user, url, domain)
               clubBadger=ClubBadger(user, url, domain)
               if speedLimitBadger.getBadge() is not None:
                        logging.info('initializing speed limit badger')
                        return speedLimitBadger
               if clubBadger.getBadge() is not None:
                        logging.info('initializing club badger')
                        return clubBadger
               usageBadge=ContinuousUsageBadge(user, url, domain)
               if usageBadge.getBadge() is not None:
                        logging.info('initializing usage badger')
                        return usageBadge
               return None
                
class ContinuousUsageBadge:
        def __init__(self, user, url, domain):
                self.user = user
                self.url = url
                self.domain = domain
        def getBadge(self):
                returnBadge=5
                existingBadge=UserBadge.gql('WHERE user = :1 and badge = :2', self.user, returnBadge).get()
                if existingBadge is None:
                        logging.info('not usage date fetched for %s in last % days' %(self.user, returnBadge))
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
        def __init__(self, user, url, domain):
                self.user = user
                self.url = url
                self.domain = domain
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
                
class SiteSpecificBadge:
        def __init__(self, user, url, domain):
                self.user = user
                self.url = url
                self.domain = domain
        def getBadge(self):
                if self.domain == 'nytimes.com':
                        return self.getnytbadge()
                else:
                        return None
        def getnytbadge(self):
               nyt_tresshold=5
               midnight = datetime.datetime.now().date()
               currentCount=SessionModel.gql('where domain = :1 and date >= :2 and instaright_account = :3', self.domain, midnight, self.user).count()
               logging.info('site specific badger(NY): fetched stats %s' % currentCount)
               if currentCount >= nyt_tresshold:
                        logging.info('setting ny badge for user %s ' %self.user)
                        return 'ny'
               else:
                        logging.info('for user %s still tresshold of %s still not reached %s' %(self.user, nyt_tresshold, currentCount))
                        return None

class ClubBadger:
        def __init__(self, user, url, domain):
                self.user = user
                self.url = url
                self.domain = domain
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
        def __init__(self, user, url, domain):
                self.user = user
                self.url = url
                self.domain = domain
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
        @staticmethod
        def toInt(string,default):
                try:
                        return int(string)
                except ValueError:
                        return default
                

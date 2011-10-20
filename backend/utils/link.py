import os
import re
import sys
import urlparse
import urllib
import logging
import urllib2
import datetime
import ConfigParser
import base64
import hashlib
from models import DailyDomainStats, WeeklyDomainStats, LinkStats
from models import LinkCategory, Links
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext.db import NotSavedError
from google.appengine.ext.db import BadValueError

sys.path.append(os.path.join(os.path.dirname(__file__),'lib'))
import simplejson
from utils.handler import RequestUtils
from utils.general import Cast

#DO NOT TOUCH!!!!
chars='abcdefghijklmnopqrstuvwxyz'
mapping=range(28)
mapping.reverse()
class EncodeUtils(object):
	def encode(self, n):
		result=0
		for i,b in enumerate(mapping):
			b1 = 1 << i
			b2 = 1 << mapping[i]
			if b1 & n:
				result |= b2
		return result
	def decode(self, n):
		result = 0
		for i,c in enumerate(mapping):
			b1 = 1 << i
			b2 = 1 << mapping[i]
			if n & b2:
				result |= b1
		return result
	def enbase(self, x):
		n = len(chars)
		if x < n:
			return chars[x]
		return self.enbase(x/n) + chars[x%n]
	def debase(self, x):
		n = len(chars)
		result = 0
		for i, c in enumerate(reversed(x)):
			result += chars.index(c) * (n**i)
		return result
			
class LinkUtils(object):
        def __init__(self):
		config=ConfigParser.ConfigParser()
		config.read(os.path.split(os.path.realpath(__file__))[0]+'/../properties/general.ini')
		self.tw_margin=int(config.get('social', 'tw_margin'))
		self.tw_factor=int(config.get('social', 'tw_factor'))
		self.fb_factor=int(config.get('social', 'fb_factor'))
		self.klout_correction=int(config.get('social', 'klout_correction'))
		self.klout_api_key=config.get('social', 'klout_api_key')
                self.skip_domains=config.get('twit','skip_domain')
		key_key = ( datetime.datetime.now().day - 1 ) // 7 + 1
                self.embedly_key=config.get('embedly','key_'+ str(key_key))

        def getEmbededInfo(cls, url_hash):
                l = Links.gql('WHERE url_hash = :1', url_hash).get()
                if l is None or l.embeded is None:
                        return None
                return l.embeded
        def getLinkInfo(self, url):
                api_call="http://api.embed.ly/1/oembed?key="+urllib.quote(self.embedly_key)+"&url="+urllib.quote(url.encode('utf-8'))+"&maxwidth=500&format=json"
                json = LinkUtils.getJsonFromApi(api_call)
                title = LinkUtils.getJsonFieldSimple(json, "title")
                description = LinkUtils.getJsonFieldSimple(json, "description")
                image = LinkUtils.getJsonFieldSimple(json, "url")
                html = LinkUtils.getJsonFieldSimple(json, "html")
                ttype = LinkUtils.getJsonFieldSimple(json, "type")
                embeded = ""
                if image is not None and ttype == "photo":
                        embeded = '<a href="%s"><img src="%s" /></a>'  % ( url, image )
                if html is not None:
                        embeded = html
                return {"t":title,"d":description, "e": embeded}

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
        def generate_domain_link(cls, domain):
                return "http://www.instaright.com/domain/%s" % domain
        @classmethod
        def generate_instaright_link(cls, url_hash, generated_title, default=None):
                if url_hash is None or generated_title is None:
                        return default
                return "http://www.instaright.com/article/"+url_hash+"/"+generated_title
        @classmethod
        def make_title(cls, title):
                #TODO solve chinese/japan chars ie iemcps
                title = re.sub(r'\W+', '-', unicode(title))
                return title
        @classmethod
        def getLinkCategory(cls, link_model):
                category=''
                logging.info('looking category cache for url hash %s ( %s )' %(link_model.url_hash, link_model.url))
                if link_model is None or link_model.url_hash is None:
                        return category
                mem_key = link_model.url_hash+'_category'
                cached_category=memcache.get(mem_key)
                if cached_category is not None:
                        logging.info('got category from cache %s' %cached_category)
                        return ','.join(cached_category)
                linkCategory=None
                try:
                        linkCategory=LinkCategory.gql('WHERE category != NULL and url_hash = :1 ' , link_model.url_hash).fetch(1000)
                except NotSavedError:
                        logging.info('not saved key for url hash %s' % link_model.url_hash)
                if linkCategory is not None:
                        logging.info('got %s categories for %s' %( len(linkCategory), link_model.url))
                        cats_tag=[ l.category  for l in linkCategory if l.category is not None and len(l.category) > 2 ]
                        category=list(set(cats_tag))
                        logging.info('got category from query %s' %category)
                        memcache.set(mem_key, category)
                return ','.join(category)

        @classmethod
        def getCategoryListHTML(cls, categories):
                if categories is None:
                        return ''
                cats = []
                logging.info('categories: %s' % categories)
                for i,c in enumerate(categories):
                        cats.append('<p class="text_bubble"><a href="/category/'+c+'" title="Instaright popular category '+c+'"><span>'+c+'</span></a></p>')
                        if i % 5 == 0:
                                cats.append('<br><br>')
                logging.info('got category list: %s' % categories)
                return ''.join(cats)

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
                hash=None
                try:
                        hash = base64.b64encode(hashlib.sha1(unicode(url).encode('utf-8')).digest())[:-1]
                except:
                        e0, e1 = sys.exc_info()[0], sys.exc_info()[1]
                        logging.info('hash for url %s failed... error=> %s ::: %s' %(url, e0, e1))
                return hash
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
        def generateUrlTitle(cls, title):
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
                        
        @classmethod
        def getLinkTitle(cls,url):
                        title=None
                        try:
		                url=urllib2.quote(url.encode('utf-8'))
                                api_call="http://query.yahooapis.com/v1/public/yql?q=select%20*%20from%20html%20where%20url%3D%22"+url+"%22%20and%20xpath%3D'%2F%2Ftitle'&format=json&callback=" 
                                json = LinkUtils.getJsonFromApi(api_call)
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
        def getLinkCategoryHTML(cls, link_model):
                category=None
                logging.info('looking category cache for url hash %s ( %s )' %(link_model.url_hash, link_model.url))
                if link_model is None or link_model.url_hash is None:
                        return category
                mem_key = link_model.url_hash+'_category'
                cached_category=memcache.get(mem_key)
                if cached_category is not None:
                        logging.info('got category from cache %s' %cached_category)
                        category=cached_category
                linkCategory=None
                try:
                        linkCategory=LinkCategory.gql('WHERE category != NULL and url_hash = :1 ' , link_model.url_hash).fetch(1000)
                except NotSavedError:
                        logging.info('not saved key for url hash %s' % link_model.url_hash)
                if linkCategory is not None and category is None:
                        logging.info('got %s categories for %s' %( len(linkCategory), link_model.url))
                        cats_tag=[ l.category  for l in linkCategory if l.category is not None and len(l.category) > 2 ]
                        category=list(set(cats_tag))
                        logging.info('got category from query %s' %category)
                        memcache.set(mem_key, category)
                #NOTE: static css , error
                html = [ "<span class=\"text_bubble_cats\"><a href=\"/category/"+c+"\">"+c+"</a></span>" for c in category ]
                return " ".join(html)
        @classmethod
        def isRootDomain(cls, url):
                scheme, netloc, path, query, fragment = urlparse.urlsplit(url)
                var1=scheme + '://' + netloc + path
                var2=scheme + '://' + netloc + path + '/'
                if url == var1 or url == var2:
                        logging.info('url %s is root domain ' % url)
                        return True
                return False
        def getAllData(self,url, count=0):

		domain = RequestUtils.getDomain(url)
		logging.info('from %s domain %s' %( url, domain))
		url=urllib2.quote(url.encode('utf-8'))
                url_hash = LinkUtils.getUrlHash(url)

                topsy_api='http://otter.topsy.com/stats.json?url=%s' % url
                tweet_meme_api='http://api.tweetmeme.com/url_info.json?url=%s' %url
                delicious_api='http://feeds.delicious.com/v2/json/urlinfo/data?url=%s&type=json' % url
                digg_api='http://services.digg.com/1.0/endpoint?method=story.getAll&link=%s&type=json' %url
                reddit_api='http://www.reddit.com/api/info.json?url=%s' %url
                facebook_api='https://api.facebook.com/method/fql.query?query=select%20%20like_count,share_count%20from%20link_stat%20where%20url=%22'+url+'%22&format=json'
                linkedin_api='http://www.linkedin.com/cws/share-count?url=%s' % url
		stumble_upon_api='http://www.stumbleupon.com/services/1.01/badge.getinfo?url=%s' %url
		buzz_api = 'https://www.googleapis.com/buzz/v1/activities/count?alt=json&url=%s' % url
		alternate_api='http://api.sharedcount.com/?url=%s' %url

		link = None
		alternate_twitter_score = None
		alternate_buzz_score = None
		alternate_digg_score = None
		alternate_facebook_share_score = None
		alternate_facebook_like_score = None
		alternate_su_score = None
                alternate_linkedin_score = None
		
		try:
                	link = Links.gql('WHERE url_hash  = :1', url_hash).get()
                        if link is None:
                	        link = Links.gql('WHERE url = :1', url).get()
		except BadValueError:
			logging.info('url property too long')
                if link is None:
                        link = Links()
			link.domain = domain
                        link.instapaper_count = Cast.toInt(count,0)
                        link.url = urllib2.unquote(url).decode('utf-8')
                        link.url_hash = LinkUtils.getUrlHash(link.url)
                        link.redditups = 0
                        link.redditdowns = 0
                        link.tweets = 0
                        link.diggs = 0
                        link.delicious_count = 0
                        link.overall_score = 0
                        link.shared = False
                else:
                        link.date_updated = datetime.datetime.now().date()
			link.domain = domain
                        if link.title:
                                link.title=link.title.strip()[:199]
                        if link.url_hash is None:
                                link.url_hash =url_hash 

		#relaxation 
		link.relaxation = 0

                logging.info('trying to fetch shared count info %s' %alternate_api )
                json = LinkUtils.getJsonFromApi(alternate_api)
                if json:
                        try:
                                alternate_twitter_score=Cast.toInt(json['Twitter'],0)
                                alternate_buzz_score=Cast.toInt(json['Buzz'],0)
                                alternate_digg_score=Cast.toInt(json['Diggs'],0)
                                facebook_info = LinkUtils.getJsonFieldSimple(json, "Facebook")
                                logging.info('facebook alternate info %s' % facebook_info)
                                if type(facebook_info) is int:
                                        alternate_facebook_share_score = Cast.toInt(facebook_info, 0)
                                elif type(facebook_info) is dict:
                                        logging.info('likes: %s' % LinkUtils.getJsonFieldSimple(facebook_info, "like_count"))
                                        logging.info('shares : %s' % LinkUtils.getJsonFieldSimple(facebook_info, "share_count"))
                                        alternate_facebook_like_score = Cast.toInt(LinkUtils.getJsonFieldSimple(facebook_info, "like_count"), 0)
                                        alternate_facebook_share_score = Cast.toInt(LinkUtils.getJsonFieldSimple(facebook_info, "share_count"), 0)
                                logging.info('alternate fb likes %s fb share %s ' % (alternate_facebook_like_score, alternate_facebook_share_score))
                                alternate_su_score=Cast.toInt(json['StumbleUpon'],0)
                                alternate_linkedin_score=Cast.toInt(json['LinkedIn'],0)

                        except KeyError:
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('key error [[%s, %s]] in %s' %(e0, e1, json))

                logging.info('trying to fetch topsi info %s' %topsy_api)
                json = LinkUtils.getJsonFromApi(topsy_api)
                if json:
                        try:
                                link.influence_score=Cast.toInt(json['response']['influential'],0)
                                link.all_score=Cast.toInt(json['response']['all'],0)
                        except KeyError:
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('key error [[%s, %s]] in %s' %(e0, e1, json))

                logging.info('trying to fetch digg info %s' %digg_api)
                json =LinkUtils.getJsonFromApi(digg_api)
                if json:
                        try:
                                link.diggs =Cast.toInt(json['count'],0)
				logging.info('diggs %s' %link.diggs)
                        except KeyError:
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('key error [[%s, %s]] in %s' %(e0, e1, json))
		elif alternate_digg_score is not None:
			logging.info('using alternate digg score %s' % alternate_digg_score)
			link.diggs = alternate_digg_score
                if link.diggs is not None:
                        link.overall_score += link.diggs

                logging.info('trying to fetch tweet_meme info %s ' % tweet_meme_api )
                json = LinkUtils.getJsonFromApi(tweet_meme_api)
                if json and 'story' in json:
                        try:
                                link.tweets=Cast.toInt(json['story']['url_count'],0)
                                if json['story']['title'] is not None:
                                        link.title=json['story']['title'].strip()[:199]
			 	if 'excerpt' in json['story']:	
					logging.info('getting excerpt');
                                	link.excerpt = db.Text(unicode(json['story']['excerpt']))
				logging.info('tweets %s' % link.tweets)
                        except KeyError:
				link.relaxation = link.relaxation + 1
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('key error [[%s, %s]] in %s' %(e0, e1, json))
		elif alternate_twitter_score is not None:
			logging.info('using altenate twitter score %s' % alternate_twitter_score)
			link.tweets = alternate_twitter_score
                if link.tweets is not None:
                	link.overall_score += self.tw_factor * link.tweets

                logging.info('trying to fetch delicious info %s ' % delicious_api)
                json =LinkUtils.getJsonFromApi(delicious_api)
                if json:
                        try:
                                if not link.title and json[0]['title']:
                                        link.title = json[0]['title'].strip()[:199]
                                link.categories = db.Text(unicode(simplejson.dumps(json[0]['top_tags'])))
                                link.delicious_count = Cast.toInt(json[0]['total_posts'],0)
				logging.info('delicious count %s' % link.delicious_count)
                                if link.delicious_count is not None:
                                        link.overall_score += link.delicious_count
                        except KeyError:
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('key error [[%s, %s]] in %s' %(e0, e1, json))

                logging.info('trying to fetch reddit info %s' % reddit_api)
                json = LinkUtils.getJsonFromApi(reddit_api)
                if json and 'data' in json:
                        try:
                                data = [ x for x in json['data']['children']]
                                top_upped = sorted(data, key=lambda ups: ups['data']['ups'], reverse=True)
                                if top_upped:
                                     link.redditups = Cast.toInt(top_upped[0]['data']['ups'],0)
                                     link.redditdowns = Cast.toInt(top_upped[0]['data']['downs'],0)
                                     link.created = Cast.toInt(top_upped[0]['data']['created'],0)
				     logging.info('reddit ups %s' % link.redditups)
                                     if link.redditups is not None:
                                                link.overall_score += link.redditups
                                     if link.redditdowns is not None:
                                                link.overall_score -= link.redditdowns
                        except KeyError:
				link.relaxation = link.relaxation + 1
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('key error [[%s, %s]] in %s' %(e0, e1, json))
                logging.info('trying to fetch facebook info %s' %facebook_api)
                json = LinkUtils.getJsonFromApi(facebook_api)
                if json:
                        try:
                                link.facebook_like=Cast.toInt(json[0]['like_count'], 0)
                                link.facebook_share=Cast.toInt(json[0]['share_count'], 0)
				logging.info('facebook likes %s' % link.facebook_like)
				logging.info('facebook share %s' % link.facebook_share)

                        except KeyError:
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('request: %s == more info: key error [[%s, %s]] in %s' %(facebook_api, e0, e1, json))
		elif alternate_facebook_like_score is not None:
			logging.info('using alternate facebook like count %s' % alternate_facebook_like_score)
			link.facebook_like_score = alternate_facebook_like_score
		elif alternate_facebook_share_score is not None:
			logging.info('using alternate facebook share count %s' % alternate_facebook_share_score)
			link.facebook_share = alternate_facebook_share_score
                if link.facebook_like is not None:
                        link.overall_score += self.fb_factor * link.facebook_like
                if link.facebook_share is not None:
                        link.overall_score += link.facebook_share

		logging.info('trying to fetch stumple upon link %s' % stumble_upon_api)
		json = LinkUtils.getJsonFromApi(stumble_upon_api)
		if json:
			try:
				link.stumble_upons = Cast.toInt(json['result']['views'], 0)
				logging.info('stumle_score %s' % link.stumble_upons)
				if not link.title and json['result']['title']:
                                        link.title = json['result']['title'].strip()[:199]
					logging.info('settting stumble title: %s' % link.title)
			except KeyError:
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('request: %s == more info: key error [[%s, %s]] in %s' %(stumble_upon_api, e0, e1, json))
		elif alternate_su_score is not None:
			logging.info('using alternate su score %s' % alternate_su_score )
			link.stumble_upons = alternate_su_score
		if link.stumble_upons is not None:
			link.overall_score += link.stumble_upons

		# specific from linkedin since response is in jsonp
		logging.info('trying to fetch linkedin upon link %s' % linkedin_api)
		try:
                        dta = urllib2.urlopen(linkedin_api)
			res = dta.read()
			res = res.replace('IN.Tags.Share.handleCount(','')
			res = res.replace(');','')
			json = simplejson.loads(res)
			
			link.linkedin_share = Cast.toInt(json['count'], 0)
			logging.info('linked in shares %s' % link.linkedin_share)
			if link.linkedin_share is not None:
					link.overall_score += link.linkedin_share
		except:
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('request: %s == more info: [[%s, %s]] in %s' %(linkedin_api, e0, e1, json))

                if link.linkedin_share is None and alternate_linkedin_score is not None:
                        logging.info('using alternate linkedin score %s' % alternate_linkedin_score)
                        link.linkedin_share = alternate_linkedin_score
                        link.overall_score += alternate_linkedin_score

		logging.info('trying to fetch buzz upon link %s' % buzz_api)
		json = LinkUtils.getJsonFromApi(buzz_api)
		if json:
			try:
				link.buzz_count = Cast.toInt(json['data']['counts']["%s"][0]["count"] % url, 0)
				logging.info('buzz share %s' % link.buzz_count)
			except KeyError:
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('request: %s == more info: key error [[%s, %s]] in %s' %(stumble_upon_api, e0, e1, json))
		elif alternate_buzz_score is not None:
			logging.info('using alternate buzz score %s' % alternate_buzz_score)
			link.buzz = alternate_buzz_score
		if link.buzz_count is not None:
			link.overall_score += link.buzz_count

                return link


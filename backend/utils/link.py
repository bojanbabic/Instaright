import os
import re
import sys
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
from google.appengine.ext.db import NotSavedError

sys.path.append(os.path.join(os.path.dirname(__file__),'lib'))
import simplejson

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
                type = LinkUtils.getJsonFieldSimple(json, "type")
                embeded = ""
                if image is not None and type == "photo":
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

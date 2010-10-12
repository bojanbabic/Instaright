import urlparse, urllib,logging
from google.appengine.api import memcache
from xml.dom import minidom
from models import UserDetails
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
		apiCall="http://api.hostip.info/get_xml.php?ip="+ip
		dom = minidom.parse(urllib.urlopen(apiCall))
		data = []
		city = dom.getElementsByTagName('gml:name')[1].firstChild.nodeValue
		country = dom.getElementsByTagName('countryAbbrev')[0].firstChild.nodeValue
		data.append(city)
		data.append(country)
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

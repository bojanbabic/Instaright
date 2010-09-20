import urlparse, urllib
from xml.dom import minidom
DOMAIN='http://instaright.appspot.com'
class StatsUtil():
	@staticmethod
	def getDomain(url):
		urlobject=urlparse.urlparse(url)
		domain = urlobject.netloc
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

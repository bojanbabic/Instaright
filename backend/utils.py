import urlparse, urllib
from xml.dom import minidom

class StatsUtil():
	@staticmethod
	def getDomain(url):
		urlobject=urlparse.urlparse(url)
		return urlobject.netloc
	
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

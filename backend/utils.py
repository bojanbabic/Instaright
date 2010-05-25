import urlparse

class StatsUtil():
	@staticmethod
	def getDomain(url):
		urlobject=urlparse.urlparse(url)
		return urlobject.netloc
	
	def callResolverAPI(self, ip):
		apiCall="http://api.hostip.info/get_xml.php?ip="+ip
		req = urllib2.Request(apiCall)
		response = req.read()
		# TODO  parse xml 

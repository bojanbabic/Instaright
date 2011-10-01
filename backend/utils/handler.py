import urlparse
import os
import sys
import urllib
import urllib2
import ConfigParser
from xml.dom import minidom
import logging

class RequestUtils(object):
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
        def getSelection(cls, args):
                selection=None
                try:
                        selection = urllib2.unquote(args[5].encode('ascii')).decode('utf-8')
                        selection = ' '.join(unicode(selection).split())
                except:
                        e0, e1 = sys.exc_info()[0], sys.exc_info()[1]
                return selection


        @classmethod
        def checkUrl(cls, args, url=None):
                config=ConfigParser.ConfigParser()
	        config.read(os.path.split(os.path.realpath(__file__))[0]+'/../properties/general.ini')
	        skip_protocols=config.get('protocols', 'skip')
                url = cls.getUrl(args, url)
                scheme, netloc, path, query, fragment = urlparse.urlsplit(url)
                if url is None:
                       return False

                logging.info('checking scheme:%s' %scheme)
                if scheme in skip_protocols:
                       logging.info('url scheme not good: %s ' % url)
                       return False
                return True

        @classmethod
        def getUrl(cls, args, url=None):
                try:
                        if url is not None:
                            return urllib2.unquote(url)
                        else:
                            return urllib2.unquote(args[1])
                except:
                        return None

        @classmethod
        def getUser(cls, args):
                try:
                        return urllib2.unquote(args[0])
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

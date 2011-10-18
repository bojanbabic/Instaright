import urlparse
import os
import sys
import urllib
import urllib2
import ConfigParser
from xml.dom import minidom
import logging
import simplejson

from models import UserSessionFE, UserDetails
_MAX_LINK_PROPERTY_LENGTH=1040

class RequestUtils(object):
	@classmethod
	def parse_params(cls, params):
		args=None
		if params is None:
			logging.info('no params to parse')
			return
		try:
			p=dict([ s.split('=') for s in params.split('&')])
			logging.info('params as dict %s' % p)
			args=simplejson.loads(urllib.unquote(p["data"]))
		except:
			e0,e = sys.exc_info()[0], sys.exc_info()[1]
			logging.error('error while parsing params %s => %s' %( e0, e))
		return args

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
	def getShareMode(cls, args):
		share_mode=1
		try:
			share_mode = int(urllib2.unqoute(args[6]))
		except:
                        e0, e1 = sys.exc_info()[0], sys.exc_info()[1]
		return share_mode

        @classmethod
        def checkUrl(cls, args, url=None):
                config=ConfigParser.ConfigParser()
	        config.read(os.path.split(os.path.realpath(__file__))[0]+'/../properties/general.ini')
	        skip_protocols=config.get('protocols', 'skip')
                url = cls.getUrl(args, url)
                if url is None:
                       return False
                scheme, netloc, path, query, fragment = urlparse.urlsplit(url)
                logging.info('checking scheme:%s' %scheme)
                if scheme in skip_protocols:
                       logging.info('url scheme not good: %s ' % url)
                       return False
                logging.info('checking url lenght %s' % len(url)) 
                #if len(url.encode('utf-8')) > _MAX_LINK_PROPERTY_LENGTH:
                if len(url) > _MAX_LINK_PROPERTY_LENGTH:
                        logging.info('url too long for datastore, must be under %s' %str(_MAX_LINK_PROPERTY_LENGTH))
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
		user = None
                try:
			#TODO!!!
			param = urllib2.unquote(args[0])
			user = param
			#check account
			ud = UserDetails.gql('WHERE instaright_account = :1', param).get()
			if ud is None:
				logging.info("account name %s doesn't exist testing session" % param)
				usession = UserSessionFE.gql('where user_uuid = :1 order by last_updatetime desc', param).get()
				user=usession.user_details.instaright_account
			else:
				user=ud.instaright_account
                except:
			e0,e = sys.exc_info()[0], sys.exc_info()[1]
			logging.error('error while determing user account %s => %s' %( e0, e))
                return user


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

import urlparse
import os
import sys
import urllib
import urllib2
import ConfigParser
from xml.dom import minidom
import logging
import simplejson

from models import UserSessionFE

_MAX_LINK_PROPERTY_LENGTH=1040

class RequestUtils(object):
	@classmethod
	def parse_request(cls, request_body):
		args = None
		ud=None
		try:
			logging.info('just received: %s' %request_body)
			args=simplejson.loads(request_body)
		except:
			logging.error('could not parse request old style trying new ...')
			ud, args = RequestUtils.parse_params(request_body)
		logging.info('request processed: args=[%s] ud=[%s]' % (args, ud))
		return ud, args

	@classmethod
	def parse_params(cls, params):
		args=None
		ud=None
		if params is None:
			logging.info('no params to parse')
			return
		try:
			p=dict([ s.split('=') for s in params.split('&')])
			args=simplejson.loads(urllib.unquote_plus(p["data"]).decode('utf-8'))
			ud = urllib.unquote(p["ud"])
		except:
			e0,e = sys.exc_info()[0], sys.exc_info()[1]
			logging.error('error while parsing params %s => %s' %( e0, e))
		return ud, args

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
        def getTitle(cls, args, client):
                title = None
                try:
		    if client == "bookmarklet":
			title=args[2]
		    else:
                    	title = urllib2.unquote(args[2].encode('ascii')).decode('utf-8')
		    logging.info('got exploded title %s' % title)
		    #logging.info('got exploded title %s' % urllib.unquote_plus(title))
                    if title == "null":
                            raise Exception('null title from request')
                    title = ' '.join(title.splitlines())
                    title = (title.encode('ascii')).decode('utf-8')
                except:
                    e0, e1 = sys.exc_info()[0], sys.exc_info()[1]
                    logging.info('title error: %s ::: %s' %(e0, e1))
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
                        if selection.endswith("\""):
                                selection=selection[0:-1]
                        if selection.startswith("\""):
                                selection=selection[1:]
                        selection = selection[:500]
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
        def checkUrl(cls, url):
                if url is None:
                       return False
                config=ConfigParser.ConfigParser()
	        config.read(os.path.split(os.path.realpath(__file__))[0]+'/../properties/general.ini')
	        skip_protocols=config.get('protocols', 'skip')
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
        def getUser(cls, ud, args):
		user = None
                try:

			if ud is not None:
                		usession = UserSessionFE.gql('WHERE user_uuid = :1 order by last_updatetime desc', ud).get()
				if usession is None:
					return None
				if usession.user_details is not None:
					user=usession.user_details.instaright_account
			else:
				user = urllib2.unquote(args[0])
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

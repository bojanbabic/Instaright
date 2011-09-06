import logging, ConfigParser, urlparse, os, datetime, uuid
from google.appengine.ext import webapp
from utils import LoginUtil, LinkUtil
from models import UserSessionFE, UserDetails
from google.appengine.ext.webapp import template

class GenericWebHandler(webapp.RequestHandler):
	def html_snapshot(self, condition=None, type=None):
		template_variables=[]
                if condition is None and type is None:
                        url = 'http://www.instaright.com/feed?format=json'
                elif type is not None and condition is not None:
                        #NOTE: condition contains trailing slash
                        url = 'http://www.instaright.com/%s/%sfeed?format=json' %(type, condition)
                logging.info('feed lookup %s ' % url)
                json = LinkUtil.getJsonFromApi(url)
		if json is None:
			return None
                logging.info('list of links: %s ' % len(json))
                template_variables = { 'links': json, 'condition': condition, 'type': type }
		path = os.path.join(os.path.dirname(__file__), 'templates/html_snapshot.html')
		self.response.out.write(template.render(path, template_variables))
		
		
        def get_user(self):
		uu = LoginUtil()
		userSession = None
		self.screen_name=None
		self.auth_service=None
                self.avatar=None
                self.user_uuid=None
                self.instaright_account=None
                self.user_detail_key=None
		used_data_from_session = False

		uuid_cookie = self.request.cookies.get('user_uuid')
		logout_cookie = self.request.cookies.get('user_logged_out')

		# try to get user name by cookie or from login
		if uuid_cookie:
			#Connect uuid with registered user
			self.user_uuid = uuid_cookie
			userSession = UserSessionFE.gql('WHERE user_uuid = :1 order by last_updatetime desc' , self.user_uuid).get()
			logging.info('reusing uuid: %s' % uuid_cookie)
			if userSession is not None and userSession.user_details is not None:
				ud = UserDetails.gql('WHERE __key__ = :1', userSession.user_details).get()

                                #fix instaright_account TODO possibly deprecated
                                if ud is not None and ud.instapaper_account is not None:
                                        ud.instaright_account=ud.instapaper_account
                                        ud.put()
				if ud is None:
					logging.error('missing proper db entry for cookie %s' % uuid_cookie)
				else:
					user_data = ud.getUserInfo()
					self.screen_name = user_data["screen_name"]
                                        self.avatar = user_data["avatar"]
					user_data_from_session = True
                                        self.instaright_account=ud.instaright_account
                                        self.user_detail_key=str(ud.key())
					logging.info('using screen name %s from session %s' %(self.screen_name, self.user_uuid))
			# sanity check
			if userSession is None:
				logging.info('smth wicked ')
				userSession = UserSessionFE()
                        if userSession and userSession.user_uuid is None:
                                userSession.user_uuid = str(self.user_uuid)
		else:
			self.user_uuid = uuid.uuid4()
			logging.info('generated new uuid: %s' % self.user_uuid)
                        expires = datetime.datetime.now() + datetime.timedelta(minutes=60)
                        exp_format = datetime.datetime.strftime(expires, '%a, %d-%b-%Y %H:%M:%S GMT')
                        logging.info('expr date %s' %exp_format)
			self.response.headers.add_header('Set-Cookie', 'user_uuid=%s; expires=%s; path=/' %( self.user_uuid, exp_format))

			userSession = UserSessionFE()
			userSession.user_uuid = str(self.user_uuid)

		# not pretty but working
		if logout_cookie:
			logging.info('found logout cookie. reseting screen_name')
			self.screen_name = None
                        self.instaright_account=None
		else:
			user_details = uu.getUserDetails(self)
                        if user_details["screen_name"] is not None:
			        self.screen_name = user_details["screen_name"]
                        if user_details["avatar"] is not None:
                                self.avatar = user_details["avatar"]
                        if user_details["auth_service"] is not None:
			        self.auth_service = user_details["auth_service"]
                        if user_details["user_details_key"] is not None:
			        user_details_key = user_details["user_details_key"]
			        userSession.user_details = user_details_key
                                self.user_detail_key=str(user_details["user_details_key"])
                        if user_details["instaright_account"] is not None:
                                self.instaright_account=user_details["instaright_account"]

			userSession.active=True
			
		userSession.screen_name = self.screen_name
		userSession.auth_service = self.auth_service

                #determine path
                url=self.request.url
                scheme, netloc, path, query, fragment = urlparse.urlsplit(url)

                existingUserPathSession=UserSessionFE.gql('WHERE user_uuid = :1 and path = :2 and screen_name = :3' , userSession.user_uuid, path, userSession.screen_name).get()
                if existingUserPathSession is None:
                        logging.info('new path %s -> %s' %(userSession.path, path))
                        newPathUserSession=UserSessionFE()
                        newPathUserSession.active=userSession.active
                        newPathUserSession.auth_service=userSession.auth_service
                        newPathUserSession.screen_name=userSession.screen_name
                        newPathUserSession.user=userSession.user
                        newPathUserSession.user_details=userSession.user_details
                        newPathUserSession.user_uuid=userSession.user_uuid
                        newPathUserSession.path=path
                        newPathUserSession.put()
		#userSession.put()
                

        def get_redirect(self, url):
             config=ConfigParser.ConfigParser()
             config.read(os.path.split(os.path.realpath(__file__))[0]+'/properties/webapp.ini')
             redirects=eval(config.get('redirect','urls'))
             logging.info('request from url %s' % url)
             scheme, netloc, path, query, fragment = urlparse.urlsplit(url)
             netloc = netloc.split(':',1)[0]
             logging.info('request netloc %s' % netloc)

             if path == '':
                     path='/'
             if netloc in redirects:
                     redirect_info=redirects[netloc]
                     if not redirect_info[1]:
                             return 'http://' + redirect_info[0] + '/'
                     else:
                             return urlparse.urlunsplit(['http', redirect_info[0], path, query, fragment])
             else:
                     logging.info('path %s not in redirect list' % url)
                     return None

        def redirect_perm(self):
                redirect_url = self.get_redirect(self.request.url)
                if redirect_url is not None:
                        logging.info('redirecting 301:%s ==> %s' %(self.request.url, redirect_url)) 
                        self.redirect(redirect_url, permanent=True)
                else:
                        logging.info('url %s will not be redirected' % self.request.url)

import datetime, time, urllib, logging, simplejson, os, BeautifulSoup, sys
from google.appengine.ext import webapp
from google.appengine.api import urlfetch
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api.labs import taskqueue
from google.appengine.ext.webapp import template

from models import UserDetails, SessionModel, UserStats

class TopUserHandler(webapp.RequestHandler):
        def get(self, stat_range):
		#try:
                        format=self.request.get('format',None)
			if '-' in stat_range:
				low, high = stat_range.split('-')
			else:
				low, high = stat_range, None
       		 	memcache_key = 'top_users_'+str(datetime.datetime.now().date())+'_'+stat_range
       		        usrs = memcache.get(memcache_key)
		        if usrs:
                                if format and format == 'txt':
                                        self.response.headers["Content-type"] = "text/plain"
                                        self.response.out.write("\n".join([ u[0] for u in usrs ]))
                                        return 
                	        template_variables = {'users' : usrs }
        			path= os.path.join(os.path.dirname(__file__), 'templates/top_users.html')
                    		self.response.headers["Content-type"] = "text/html"
        			self.response.out.write(template.render(path,template_variables))
                                return
       			elif high:
				logging.info('lower range %s ; higher range %s' %(low, high))
				users = UserDetails.gql('WHERE links_added >= :1 and links_added < :2 ORDER by links_added DESC', int(low), int(high))
			else:
				logging.info('lower range %s ' %low)
				users = UserDetails.gql('WHERE links_added >= :1 ORDER by links_added DESC', int(low))
                        logging.info('fetched %d users ' % users.count())
	       		user_accounts = [ (u.instapaper_account, u.links_added) for u in users ]
			if users.count() > 0:
				logging.info('setting users cache. %s user entries' % users.count())
        			memcache.set(memcache_key, user_accounts)
                        if format and format == 'txt':
                                self.response.headers["Content-type"] = "text/plain"
                                self.response.out.write("\n".join([ u[0] for u in user_accounts ]))
                                return
                	template_variables = {'users' : user_accounts }
			path= os.path.join(os.path.dirname(__file__), 'templates/top_users.html')
        		self.response.headers["Content-type"] = "text/html"
			self.response.out.write(template.render(path,template_variables))
	#	except:
	#		e, e0 = sys.exc_info()[0], sys.exc_info()[1]
	#		logging.error('stats error: %s ; %s' %(e, e))
	#		self.response.out.write('oups, try something else')


class UserHandler(webapp.RequestHandler):
        def get(self, user):
                if user is None or len(user) == 0:
                        logging.error('Empty user. Skipping')
                        return
                user_decoded = urllib.unquote(user)
                logging.info('user: %s' %user_decoded)
                memcache_key ='user_info_' + user_decoded+'_'+str(datetime.datetime.now().date())
                sessions = SessionModel.gql('WHERE instaright_account = :1 ORDER by date desc ' , user_decoded).fetch(100)
                links = [ s for s in sessions if s is not None ]
                cached_info = memcache.get(memcache_key)
                if cached_info:
                        logging.info('getting from cache' )
                        template_variables = {'user':cached_info,'links':links}
                        path= os.path.join(os.path.dirname(__file__), 'templates/user_info.html')
                        self.response.headers["Content-type"] = "text/html"
		        self.response.out.write(template.render(path,template_variables))
                        return
                user_detail= UserDetails.gql('WHERE mail = :1', user_decoded).get()
                if user_detail is None:
			logging.info('new user %s added to queue' %user_decoded)
			fetch_url = '/user/'+user+'/fetch'
			taskqueue.add(queue_name='user-info', url= fetch_url)
                        ud = UserDetails()
                        ud.name = user_decoded
                        ud.instapaper_account = user_decoded
                        ud.links_added = SessionModel.countAllForUser(user_decoded)
                        # tmp put until we find more info for user
                        #ud.put()
                        template_variables = {'user':ud, 'links': links}
                        path= os.path.join(os.path.dirname(__file__), 'templates/user_info.html')
                        self.response.headers["Content-type"] = "text/html"
                        self.response.headers["Accept-Charset"] = "utf-8"
		        self.response.out.write(template.render(path,template_variables))
			return
		memcache.set(memcache_key, user_detail)
                template_variables = {'user':user_detail, "links" : links}
                path= os.path.join(os.path.dirname(__file__), 'templates/user_info.html')
                self.response.headers["Content-type"] = "text/html"
		self.response.out.write(template.render(path,template_variables))

        def gather_info(self, user):

                if not '@' in user:
			logging.info('not email address: skipping ...')
                        user_detail = UserDetails()
			return user_detail
                user_detail = UserDetails.gql('where instapaper_account = :1' , user).get()
		if user_detail is None:
			user_detail = UserDetails()
		if user_detail.mail is None:
			user_detail.mail = user

                #PREPARE for request
                time_milis = time.time() * 1000
                logging.info("user encoded %s" % user)
                RAPPORTIVE_LINK = "https://rapportive.com/lookup/email?q=%s&client_stamp=%d" %( user, time_milis)
		#TILL here
                try:
                        response = urlfetch.fetch(RAPPORTIVE_LINK)
                except:
                        e, e1 = sys.exc_info()[0], sys.exc_info()[1]
                        logging.error('error: %s, %s' %(e, e1))
                        return user_detail
                if response.status_code == 200:
			#stupid hack with double loads ?!?
                        json_string_response = simplejson.loads(simplejson.dumps(response.content))
                        json= simplejson.loads(json_string_response)
                        html = json["html"]
                        bHtml = BeautifulSoup.BeautifulSoup(html)
                        divVals = []
                        name = None
                        try:
                                name = bHtml.find('h1').contents[0]
                        except:
                                logging.info('Can\'t retrieve name from: %s' % bHtml.find('h1'))

                        if name is None or unicode(name).startswith('Thanks') or unicode(name).startswith('Sorry'):
                                return user_detail
                        
                        logging.info('name: %s' % unicode(name))
                        user_detail.name = unicode(name)
                        memberships = bHtml.findAll('a', {'class':'membership-link'})
                        memships = {}
                        for m in memberships:
                                service_name = m['site_name'].lower().replace(' ','_').replace('.','_')
                                memships[service_name]=m['href']
				try:
                                	setattr(user_detail, service_name, m['href'])
                                        if service_name == 'twitter':
                                                # send twitter request 
                                                screen_name = str(m['href']).replace('http://twitter.com/')
                                                taskqueue.add(url='/utils/twitter/follow/'+screen_name, queue_name='twitter-follow')
				except:
					logging.error('can\'t find attribute %s in UserDetail' % service_name)

                        user_detail.social_data = simplejson.dumps(memships)
                        occupations = bHtml.find('ul', {'class':'occupations'}).findAll('li')
                        occups = []
                        for o in occupations:
                                tmp_o = ''.join(o.findAll(text=True)).strip()
                                occups.append(tmp_o)
                        user_detail.occupations = ''.join(occups)
                        avatar = bHtml.find('table', {'class':'basics'}).find('img',image_url=True)['image_url']
                        logging.info('avatar %s' % avatar)
                        if avatar is not None and len(avatar) > 0:
                                user_detail.avatar = avatar
                return user_detail

class UserDeleteHandler(webapp.RequestHandler):
        def get(self):
                user_details =  UserDetails.all()
                logging.info('fetched %d ' % user_details.count())
                for u in user_details:
                        logging.info('deleting %s' %(u.instapaper_account))
                        u.delete()

class UserInfoFetchHandler(webapp.RequestHandler):
        def post(self, user):
                logging.info('fetching info for user %s' % user)
                userhandler = UserHandler()
                user_decoded = urllib.unquote(user)
                user_decoded = user_decoded.strip()
                logging.info('fetching info for user %s' % user_decoded)
                userDetail = userhandler.gather_info(user_decoded)
                if userDetail.name:
                        userDetail.put()
	                logging.info('done fetching info for user %s' % user_decoded)
                	logging.info('fetching info for user %s' % user)

class UserUpdate(webapp.RequestHandler):
	def post(self):
                users = simplejson.loads(self.request.get('users',None))
                if users is None:
                        logging.info('nothing to process.exiting')
                        return
                logging.info('processing %s' % len(users))
		for u in users:
                        user = u['u']
                        if not '@' in user:
				logging.info('skipping %s' % user)
				continue
			memcache_user_key='user_'+user+'_'+str(datetime.datetime.now().date)
			if memcache.get(memcache_user_key):
				logging.info('skipping processed user %s ' % user)
                        taskqueue.add(queue_name='user-info', url='/user/'+urllib2.quote(user)+'/fetch')
			memcache.set(memcache_user_key, True)
        def get(self):
		users=UserDetails.gql('ORDER by __key__').fetch(100)
		if not users:
			return None
                taskqueue.add(url='/user/task/update_all', params={'users':simplejson.dumps(users, default=lambda u: {'u':u.instapaper_account})})
		lastKey = users[-1].key()
		while len(users) == 100:
			users=UserDetails.gql('WHERE __key__> :1 ORDER by __key__', lastKey).fetch(100)
			lastKey=users[-1].key()
                        taskqueue.add(url='/user/task/update_all', params={'users':simplejson.dumps(users, default=lambda u: {'u':u.instapaper_account})})

class UserLinksHandler(webapp.RequestHandler):
        def get(self, user):
                if user is None or len(user) == 0:
                        logging.error('Empty user. Skipping')
                        return
                user_decoded = urllib.unquote(user)
                sessions = SessionModel.gql('WHERE instaright_account = :1 ORDER by date desc ' , user_decoded).fetch(1000)
                links = [ s.url for s in sessions ]
                template_variables = {'links' : links }
                path= os.path.join(os.path.dirname(__file__), 'templates/user_links.html')
                self.response.headers["Content-type"] = "text/html"
		self.response.out.write(template.render(path,template_variables))
                
class UserFormKeyHandler(webapp.RequestHandler):
        def get(self, user, form_key):
                if user is None or len(user) == 0:
                        logging.error('Empty user. Skipping')
                        return
                user_decoded = urllib.unquote(user)
                user_detail= UserDetails.gql('WHERE instapaper_account = :1 ' , user_decoded).get()
                self.response.headers["Content-type"] = "text/plain"
                if user_detail and user_detail.form_key:
		        form_key=user_detail.form_key     
                else:
                        form_key=""
                self.response.out.write(form_key)

        def post(self, user, form_key):
                if user is None or len(user) == 0:
                        logging.error('Empty user. Skipping')
                        return
                user_decoded = urllib.unquote(user)
                user_detail= UserDetails.gql('WHERE instapaper_account = :1 ' , user_decoded).get()
                if user_detail:
                        user_detail.form_key=form_key
                        user_detail.put()
                self.response.headers["Content-type"] = "text/plain"
                self.response.out.write(form_key)
class UserStatsHandler(webapp.RequestHandler):
        def get(self, period):
                date_ = self.request.get('date', None)
                if date_:
                        date = datetime.datetime.strptime(date_, '%Y-%m-%d')
                else:   
                        date = datetime.datetime.now() - datetime.timedelta(days=1)
                logging.info('fetching stats for %s and %s' %(period,str(date.date())))
                if period == 'daily':
                        stats = UserStats.gql('WHERE date = :1 order by count desc', date).fetch(100)
                elif period == 'weekly':
                        self.response.out.write('TODO')
                        return
                else:
                        self.response.out.write('Get outta here')
                        return
                if not stats:
                        self.response.out.write('not stats for %s and date %s retreived no data' %( period, date_))
                        return
                self.response.headers["Content-type"] = "application/json"
                self.response.out.write(simplejson.dumps(stats, default=lambda s: {'u':{'account':s.instapaper_account, 'cout': s.count}}))
class UserStatsDeleteHandler(webapp.RequestHandler):
        def get(self, d):
                if d is None:
                        logging.info('no date.exit')
                        return
                date=datetime.datetime.strptime(d, '%Y-%m-%d').date()
                #if period == 'daily':
                #        allUsers = UserStats.all()
                #else:
                #        self.response.out.write('get outta here')
                #        return
                allUsers = UserStats.gql('WHERE date = :1', date).fetch(1000)
                if not allUsers:
                        loging.info('not stats for %s delete , exit' %d)
                        return
                logging.info('total stats for  %s delete %d' % (d, len(allUsers)))
                for u in allUsers:
                        u.delete()
                logging.info('done')

app = webapp.WSGIApplication([
                                ('/user/stats/top/(.*)', TopUserHandler),
                                ('/user/stats/(.*)/delete_all', UserStatsDeleteHandler),
                                ('/user/stats/(.*)', UserStatsHandler),
                                #NOTE: never uncomment this
                                #('/user/delete_all', UserDeleteHandler),
                                ('/user/(.*)/links', UserLinksHandler),
                                ('/user/(.*)/fetch', UserInfoFetchHandler),
                                ('/user/task/update_all', UserUpdate),
                                ('/user/(.*)/(.*)', UserFormKeyHandler),
                                ('/user/(.*)', UserHandler),
                                        ], debug =True)
def main():
        run_wsgi_app(app)

if __name__ == "__main__":
        main()


import datetime, time, urllib, logging, simplejson, os, BeautifulSoup, sys
from google.appengine.ext import webapp
from google.appengine.api import urlfetch
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api.labs import taskqueue
from google.appengine.ext.webapp import template

from models import UserDetails
from main import SessionModel
class TopUserHandler(webapp.RequestHandler):
        def get(self, stat_range):
		#try:
			if '-' in stat_range:
				low, high = stat_range.split('-')
			else:
				low, high = stat_range, None
       		 	memcache_key = 'top_users_'+str(datetime.datetime.now().date())
       		        usrs = memcache.get(memcache_key)
		        if usrs:
       				users = usrs
       			elif high:
				logging.info('lower range %s ; higher range %s' %(low, high))
				users = UserDetails.gql('WHERE links_added >= :1 and links_added < :2 ORDER by links_added DESC', low, high)
			else:
				logging.info('lower range %s ;' %low)
				users = UserDetails.gql('WHERE links_added >= :1 ORDER by links_added DESC', low)
	       		user_accounts = [ u.instapaper_account for u in users ]
			if users.count() > 0:
				logging.info('setting users cache. % user entries' % users.count())
        			memcache.set(memcache_key, users )
                	template_variables = {'users' : user_accounts }
			path= os.path.join(os.path.dirname(__file__), 'templates/top_users.html')
        		self.response.headers["Content-type"] = "text/html"
			self.response.out.write(template.render(path,template_variables))
		#except:
		#	e, e0 = sys.exc_info()[0], sys.exc_info()[1]
		#	logging.error('stats error: %s ; %s' %(e, e))
		#	self.response.out.write('oups, try something else')


class UserHandler(webapp.RequestHandler):
        def get(self, user):
                if user is None or len(user) == 0:
                        logging.error('Empty user. Skipping')
                        return
                user_decoded = urllib.unquote(user)
                logging.info('user: %s' %user_decoded)
                memcache_key ='user_info_' + user_decoded+'_'+str(datetime.datetime.now().date())
                cached_info = memcache.get(memcache_key)
                if cached_info:
                        logging.info('getting from cache' )
                        self.response.headers["Content-Type"]="application/json"
                        self.response.out.write(cached_info)
                        return
                user_detail= UserDetails.gql('WHERE mail = :1', user_decoded).get()
                if user_detail is None:
			logging.info('new user %s added to queue' %user_decoded)
			fetch_url = '/user/'+user_decoded+'/fetch'
			taskqueue.add(queue_name='user-info', url= fetch_url)
                        out_json = {'name':'', 'occupations': [], 'memberships': [], 'avatar':''} 
                	self.response.headers["Content-Type"]="application/json"
                	self.response.out.write(simplejson.dumps(out_json))
			return
                out_json = {'name':user_detail.name, 'occupations': user_detail.occupations, 'memberships': user_detail.social_data, 'avatar':user_detail.avatar} 
		memcache.set(memcache_key, simplejson.dumps(out_json))
                self.response.headers["Content-Type"]="application/json"
                self.response.out.write(simplejson.dumps(out_json))

        def gather_info(self, user):

                if not '@' in user:
			logging.info('not email address: skipping ...')
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
                userhandler = UserHandler()
                user_decoded = urllib.unquote(user)
                logging.info('fetching info for user %s' % user_decoded)
                userDetail = userhandler.gather_info(user_decoded)
                if userDetail.name:
                        userDetail.put()
	                logging.info('done fetching info for user %s' % user_decoded)
                	logging.info('fetching info for user %s' % user)

class UserUpdate(webapp.RequestHandler):
	def get(self):
		memcache_key = 'all_users_'+str(datetime.datetime.now().date())
		cached_users=memcache.get(memcache_key)
		if cached_users:
			logging.info('getting users from cache')
			users = cached_users
		else:
			logging.info('getting users from gql')
			users= UserDetails.all()
		for u in users:
			if not '@' in u.instapaper_account:
				logging.info('skipping %s' % u.instapaper_account)
				continue
			memcache_user_key='user_'+u.instapaper_account+'_'+str(datetime.datetime.now().date)
			if memcache.get(memcache_user_key):
				logging.info('skipping processed user %s ' % u.instapaper_account)
			taskqueue.add(queue_name='user-info', url='/user/'+u.instapaper_account+'/fetch/')
			memcache.set(memcache_user_key, u.key())
		memcache.delete(memcache_key)


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
                

app = webapp.WSGIApplication([
                                ('/user/stats/top/(.*)', TopUserHandler),
                                ('/user/delete_all', UserDeleteHandler),
                                ('/user/(.*)/links', UserLinksHandler),
                                ('/user/(.*)/fetch', UserInfoFetchHandler),
                                ('/user/task/update_all', UserUpdate),
                                ('/user/(.*)', UserHandler),
                                        ], debug =True)
def main():
        run_wsgi_app(app)

if __name__ == "__main__":
        main()


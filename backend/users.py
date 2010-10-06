import datetime, time, urllib, logging, simplejson, os, BeautifulSoup, sys
from google.appengine.ext import webapp
from google.appengine.api import urlfetch
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.ext.webapp import template

from models import UserDetails
from main import SessionModel
class TopUserHandler(webapp.RequestHandler):
        def get(self):
                memcache_key = 'top_domains_'+str(datetime.datetime.today().date())
                usrs = memcache.get(memcache_key)
                if usrs is not None:
                        users = usrs
                else:
                        users = UserDetails.gql('ORDER by links_added desc').fetch(1800)
                user_accounts = [ u.instapaper_account for u in users ]
                memcache.set(memcache_key, users )
                template_variables = {'users' : user_accounts }
		path= os.path.join(os.path.dirname(__file__), 'templates/top_users.html')
                self.response.headers["Content-type"] = "text/html"
		self.response.out.write(template.render(path,template_variables))

class UserHandler(webapp.RequestHandler):
        def get(self, user):
                if user is None or len(user) == 0:
                        logging.error('Empty user. Skipping')
                        return
                user_decoded = urllib.unquote(user)
                if not "@" in user_decoded:
                        logging.error('Not email %s . Skipping' % user)
                        out_json = {'name':'', 'occupations': [], 'memberships': [], 'avatar':''} 
                        self.response.headers["Content-Type"]="application/json"
                        self.response.out.write(simplejson.dumps(out_json))
                        return
                logging.info('Valid user: %s' %user_decoded)
                memcache_key ='user_info_' + user_decoded+'_'+str(datetime.datetime.now().date())
                cached_info = memcache.get(memcache_key)
                if cached_info is not None:
                        logging.info('getting from cache' )
                        self.response.headers["Content-Type"]="application/json"
                        self.response.out.write(simplejson.loads(cached_info))
                        return
                user_detail= UserDetails.gql('WHERE mail = :1', user_decoded).get()
                if user_detail is None or user_detail.name is None:
                        logging.info('fetching details from outside for %s' % user_decoded)
                        #TODO stupidly executed
                        user_detail  = self.gather_info(user_decoded)
                        if user_detail.name is not None:
                                logging.info('saving fetched data: %s' %user_detail.name)
                                user_detail.put()

                out_json = {'name':user_detail.name, 'occupations': user_detail.occupations, 'memberships': user_detail.social_data, 'avatar':user_detail.avatar} 
                self.response.headers["Content-Type"]="application/json"
                self.response.out.write(simplejson.dumps(out_json))

        def gather_info(self, user):

                user_detail = UserDetails.gql('where instapaper_account = :1' , user).get()
                if user_detail is None:
                        user_detail = UserDetails()
                        user_detail.instapaper_account = user
                if '@' in user:
                        user_detail.mail = user
                #prepare for request
                time_milis = time.time() * 1000
                logging.info("user encoded %s" % user)
                RAPPORTIVE_LINK = "https://rapportive.com/lookup/email?q=%s&client_stamp=%d" %( user, time_milis)
                try:
                        response = urlfetch.fetch(RAPPORTIVE_LINK)
                except:
                        e, e1 = sys.exc_info()[0], sys.exc_info()[1]
                        logging.error('error: %s, %s' %(e, e1))
                        return user_detail
                if response.status_code == 200:
                        json_string_response = simplejson.loads(simplejson.dumps(response.content))
                        #memcache.set(memcache_key, json_response)
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
                        
                        logging.info('name: %s' % name)
                        user_detail.name = unicode(name)
                        memberships = bHtml.findAll('a', {'class':'membership-link'})
                        memships = {}
                        for m in memberships:
                                service_name = m['site_name'].lower().replace(' ','_').replace('.','_')
                                memships[service_name]=m['href']
                                setattr(user_detail, service_name, m['href'])

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
                userDetail = userhandler.gather_info(user_decoded)
                if userDetail.name is not None:
                        userDetail.put()
                logging.info('done fetching info for user %s' % user_decoded)

        def get(self, user):
                logging.info('get %s' % user)

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
                                ('/user/stats/top', TopUserHandler),
                                ('/user/delete_all', UserDeleteHandler),
                                ('/user/(.*)/links', UserLinksHandler),
                                ('/user/(.*)/fetch', UserInfoFetchHandler),
                                ('/user/(.*)', UserHandler),
                                        ], debug =True)
def main():
        run_wsgi_app(app)

if __name__ == "__main__":
        main()


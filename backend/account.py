import sys, os, urllib2, datetime, logging, cgi, uuid

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.api import channel 
from google.appengine.api.labs import taskqueue
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from django.utils import simplejson
from utils import StatsUtil, LoginUtil

from models import UserSessionFE, SessionModel, Links
from oauth_handler import OAuthHandler, OAuthClient

class AccountHandler(webapp.RequestHandler):
    def get(self):

        client = OAuthClient('twitter', self)
        gdata = OAuthClient('google', self, scope='http://www.google.com/calendar/feeds')

        write = self.response.out.write; 

        if not client.get_cookie():
            write('<a href="/oauth/twitter/login">Login via Twitter</a><br>')
        if not gdata.get_cookie():
            write('<a href="/oauth/google/login">Login via Google</a><br>')
            write( """
            <div id="fb-root"></div>
                  <script src="http://connect.facebook.net/en_US/all.js">
                  </script>
                  <script>
                  FB.init({ 
                  appId:'180962951948062', cookie:true, 
                  status:true, xfbml:true 
                  });
                  </script>
                  <fb:registration
                  fields="[{'name':'name'}, {'name':'email'},
                  {'name':'iusername','description':'Instaright username',
                  'type':'text'}, {'name':'password','description':'Instaright password', 'no_submit':true}
                  ]" onvalidate="validateAndSave" redirect-uri="http://instaright.appspot.com/account">
                  </fb:registration>
                  <script>
                        function validateAndSave(form){
                                        if (!form.password){
                                                return ({"password":"Type a password"});
                                        }
                                        var dt = new Date(), expiryTime = dt.setTime( dt.getTime() + 1000 * 5 );
                                        document.cookie= 'password='+form.password + ';expires='+ expiryTime.toGMTString();
                                        return {};
                        }
                  </script>
                """)
        if client.get_cookie():
                write('<a href="/oauth/twitter/logout">Logout from Twitter</a><br /><br />')

                info = client.get('/account/verify_credentials')

                write("<strong>Screen Name:</strong> %s<br />" % info['screen_name'])
                write("<strong>Location:</strong> %s<br />" % info['location'])

                rate_info = client.get('/account/rate_limit_status')

                write("<strong>API Rate Limit Status:</strong> %r" % rate_info)
        if gdata.get_cookie():
                write("<b>Logged in with google</b>")

application=webapp.WSGIApplication([
                             ('/account', AccountHandler),
                             ], debug=True)
def main():
        run_wsgi_app(application)

if __name__ == '__main__':
        main()

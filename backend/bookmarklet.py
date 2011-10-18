import os
import logging
from google.appengine.ext import webapp
from google.appengine.api import users
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

#ENVIRONMENT='http://localhost:8080'
ENVIRONMENT='http://www.instaright.com'
class BookmarkletHandler(webapp.RequestHandler):
        def get(self):
		template_vars={'env':ENVIRONMENT}
		path=os.path.join(os.path.dirname(__file__), 'templates/bookmarklet_response.js')
                self.response.headers["Content-Type"] = "text/javascript"
		self.response.out.write(template.render(path,template_vars))

class BookmarkletFrameHandler(webapp.RequestHandler):
        def get(self):
		google_login_url = users.create_login_url('/') 
		template_vars={'google_login_url': google_login_url, 'env': ENVIRONMENT}
		path=os.path.join(os.path.dirname(__file__), 'templates/bookmarklet_frame.html')
                self.response.headers["Content-Type"] = "text/html"
		self.response.out.write(template.render(path,template_vars))

class BookmarkletRequestHandler(webapp.RequestHandler):
        def post(self):
                link=self.request.get('link', None);
                title=self.request.get('title', None);
                parenturl=self.request.get('parenturl', None);
                note=self.request.get('note', None);
                logging.info('got from bookmarklet: %s %s %s %s' %(link, title, parenturl, note))
		self.response.out.write('{"close_html":"Link sucessfully sent"}')

application = webapp.WSGIApplication(
                [
                        ('/bookmarklet/javascript', BookmarkletHandler),
                        ('/bookmarklet/frame', BookmarkletFrameHandler),
                        ('/a/bookmarklet', BookmarkletRequestHandler),
                        ('/a/.*', DummyHandler),
                ],
                debug=True)
def main():
        run_wsgi_app(application)

if __name__ == "__main__":
        main()

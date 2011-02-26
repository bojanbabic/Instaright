import datetime, time, urllib, logging, simplejson, os, BeautifulSoup, sys
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import memcache
from google.appengine.ext.webapp import template

class DownloadHandler(webapp.RequestHandler):
        def get(self):
                template_variables = []
                logging.info('downloading xpi')
                try:
        	        path= os.path.join(os.path.dirname(__file__), 'tools/addon/instaright.xpi')
                        self.response.headers["Content-type"] = "application/zip"
        	        self.response.out.write(template.render(path,template_variables))
                except:
                        logging.info('error downloading xpi %s' % sys.exc_info()[0])

app = webapp.WSGIApplication([
                                ('/tools/addon/instaright.xpi', DownloadHandler),
                                        ], debug =True)
def main():
        run_wsgi_app(app)

if __name__ == "__main__":
        main()


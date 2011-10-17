import os, sys, logging
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

class BookmarkletHandler(webapp.RequestHandler):
        def get(self):
		template_vars={}
		path=os.path.join(os.path.dirname(__file__), 'templates/bookmarklet_response.js')
                self.response.headers["Content-Type"] = "text/javascript"
		self.response.out.write(template.render(path,template_vars))

class BookmarkletFrameHandler(webapp.RequestHandler):
        def get(self):
		template_vars={}
		path=os.path.join(os.path.dirname(__file__), 'templates/bookmarklet_frame.html')
                self.response.headers["Content-Type"] = "text/html"
		self.response.out.write(template.render(path,template_vars))

class DummyHandler(webapp.RequestHandler):
        def get(self):
		self.response.out.write("boo")
        def post(self):
                self.response.out.write('{"contacts":[["baboon1+friends","My feed",1],["scobleizer","Robert Scoble"],["plasticdreams","aka"],["bouriel","bouriel"]]}')
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

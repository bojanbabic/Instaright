import logging, datetime, os
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from main import SessionModel

from feedformatter import Feed

DOMAIN = 'http://instaright.appspot.com'

class FeedGenerator(webapp.RequestHandler):
	def get(self):
		entries = SessionModel.gql('ORDER by date DESC').fetch(10)
		if not entries:
			self.response.out.write('Nothing here')
		now = datetime.datetime.now().strftime("%Y-%m-%d\T%H\:%i\:%s\Z")
		template_variables = { 'entries' : entries, 'dateupdated' : datetime.datetime.today()}

		path= os.path.join(os.path.dirname(__file__), 'templates/feed.html')
		self.response.headers['Content-Type'] = "application/atom+xml"
		self.response.out.write(template.render(path,template_variables))

	def hideUsers(user):
		if len(user) < 3:
			return user
		if user.find('@'):
			endposition = user.find("@")
		else:
			endposition = len(user)-1
		return user.replace(user[1:endposition], 'xxxx')
		
			
class ArticleHandler(webapp.RequestHandler):
	def get(self, location):
		logging.info('fetching: %s' % location)
		keyS=location
		key = db.Key(keyS)
		if not key:
			logging.info('not provided proper key entry : %s' % keyS)
			self.response.out.write('not provided  proper key entry %s' % keyS)
		article = SessionModel.gql( 'WHERE __key__ = :1', key).get()
		if not article:
			self.response.out.write('For key %s no article has been found' % keyS)
		logging.info('redirecting to %s' % article.url)
		template_variables={ 'url' : article.url }
		path = os.path.join(os.path.dirname(__file__), 'templates/article.html')
		self.response.out.write(template.render(path, template_variables))

		
application = webapp.WSGIApplication(
                                     [
                                     	('/article/(.*)', ArticleHandler),
                                     	#('/feed', AtomGenerator)
                                     	('/feed', FeedGenerator)
                                     	#('/feed', FeedHandler)
				     ],
                                     debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()

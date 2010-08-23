import logging, datetime, os
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from main import SessionModel
from feedformatter import Feed

DOMAIN = 'http://instaright.appspot.com'

class AtomGenerator(webapp.RequestHandler):
	def get(self):

		entries = SessionModel.gql('ORDER by date DESC').fetch(10)

		feed = Feed()
		feed.feed["title"] = "Instaright live feed"
		feed.feed["link"] = "http://instaright.appspot.com/feed"
		feed.feed["author"]="@bojanbabic"

		if not entries:
			self.response.out.write('Nothing here')
		entries_list = list(entries)
		entries_list.reverse()
		for entry in entries_list:
			item = {}
			item["title"]=entry.domain
			item["link"]=DOMAIN + '/article/' + str(entry.key())
			item["description"]='Link submited by user %s' % entry.instaright_account
			item["pubDate"]=entry.date.timetuple()
			item["uid"]=str(entry.key())
			
			feed.items.insert(0, item)
		self.response.headers['Content-Type'] = "application/rss+xml"
		self.response.out.write(feed.format_atom_string())
class FeedGenerator(webapp.RequestHandler):
	def get(self):
		
		entries = SessionModel.gql('ORDER by date DESC').fetch(10)
		if not entries:
			self.response.out.write('Nothing here')
		now = datetime.datetime.now().strftime("%Y-%m-%d\T%H\:%i\:%s\Z")
		template_variables = { 'entries' : entries, 'dateupdated' : datetime.datetime.today()}

		path= os.path.join(os.path.dirname(__file__), 'templates/feed.html')
		self.response.out.write(template.render(path,template_variables))
			
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
		self.response.headers['Content-Type'] = "application/rss+xml"
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

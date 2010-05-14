from google.appengine.ext import db
from google.appengine.tools import bulkloader

class SessionLoader(bulkloader.Loader):
	def __init__(self):
		bulkloader.Loader.__init__(self, 'SessionModel',
			[ ('user_agent', str),
			  ('instaright_account', str),
			  ('ip', str),
			  ('url', lambda x: db.LinkProperty(x)),
			  ('date', lambda x: datetime.datetime.strptime(x).date()),
			  ('domain', str)
			])
loaders = [SessionLoader]

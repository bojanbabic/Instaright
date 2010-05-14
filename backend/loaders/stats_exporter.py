from google.appengine.ext import db
from google.appengine.tools import bulkloader

class SessionModel(db.Model):
	user_agent= db.StringProperty()
	instaright_account = db.StringProperty()
	ip = db.StringProperty()
	url = db.LinkProperty()
	date = db.DateProperty()
	domain = db.StringProperty()

class SessionExporter(bulkloader.Exporter):
	def __init__(self):
		bulkloader.Exporter.__init__(self, 'SessionModel',
			[ ('user_agent', str, None),
			  ('instaright_account', str, None),
			  ('ip', str, None),
			  ('url', str, None),
			  ('date', str, None),
			  ('domain', str, None)
			])
exporters = [SessionExporter]

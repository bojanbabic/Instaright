import datetime
from google.appengine.ext import db
from google.appengine.tools import bulkloader
import models

class WeeklyStatsLoader(bulkloader.Loader):
	def __init__(self):
		bulkloader.Loader.__init__(self, 'WeeklyDomainStats', 
						[('count', int),
						 ('date', lambda x: datetime.datetime.date()), 
						 ('domain', lambda x: x.decode('utf-8'))])

loaders = [WeeklyStatsLoader]
					

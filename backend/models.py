from google.appengine.ext import db 

class StatsModel(db.Model):
	totalNumber=db.IntegerProperty()
	totalDailyNumber=db.IntegerProperty()
	date=db.DateProperty(auto_now_add=True)

class DailyDomainStats(db.Model):
	domain=db.StringProperty()
	count=db.IntegerProperty()
	date=db.DateProperty(auto_now_add=True)

class WeeklyDomainStats(db.Model):
	domain=db.StringProperty()
	count=db.IntegerProperty()
	date=db.DateProperty(auto_now_add=True)

class YearDomainStats(db.Model):
	domain=db.StringProperty()
	count=db.IntegerProperty()
	date=db.DateProperty(auto_now_add=True)
class LinkStats(db.Model):
	link=db.StringProperty()
	countUpdated=db.DateTimeProperty(auto_now_add=True)
	count=db.IntegerProperty()
	lastUpdatedBy=db.StringProperty()
class UserLocationModel(db.Model):
	countryCode=db.StringProperty()
	city=db.StringProperty()
	date=db.DateTimeProperty(auto_now_add=True)
	user=db.StringProperty()
class CountryStats(db.Model):
	countryCode=db.StringProperty()
	count=db.IntegerProperty()
	dateUpdated=db.DateProperty(auto_now_add=True)
class CityStats(db.Model):
	city=db.StringProperty()
	countryCode=db.StringProperty()
	count=db.IntegerProperty()
	dateUpdated=db.DateProperty(auto_now_add=True)
class Subscription(db.Model):
	subscriber = db.IMProperty(required=True)
	subscriber_mail = db.StringProperty()
	domain = db.StringProperty(required=True)
	activationDate = db.DateTimeProperty(auto_now_add=True)
	active = db.BooleanProperty()
	mute = db.BooleanProperty()
class UserSessionFE(db.Model):
	user = db.UserProperty()
	user_uuid = db.StringProperty()
	last_updatetime = db.DateTimeProperty(auto_now_add = True)
	active = db.BooleanProperty()

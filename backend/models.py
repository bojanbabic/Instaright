import datetime, logging
from google.appengine.ext import db 

class SessionModel(db.Model):
	user_agent=db.StringProperty()
	instaright_account=db.StringProperty()
	ip=db.StringProperty()
	url=db.LinkProperty()
	date=db.DateTimeProperty()
	domain=db.StringProperty()
        title=db.StringProperty()
	def count_all(self):
		count = 0
		query = SessionModel.all().order('__key__')
		while count % 1000 == 0:
			current_count = query.count()
			count += current_count
			
			if current_count == 1000:
				last_key = query.fetch(1, 999)[0].key()
				query = query.filter('__key__ > ' , last_key)
		return count

	@staticmethod
	def countAll():
		data=SessionModel.gql('ORDER by __key__').fetch(1000)
		lastKey = data[-1].key()
		total=len(data)
		while len(data) == 1000:
			data=SessionModel.gql('WHERE __key__> :1 ORDER by __key__', lastKey).fetch(1000)
			lastKey=data[-1].key()
			total+=len(data)
		return total

	@staticmethod
	def countAllForUser(user):
                if user is None:
                        return 0
                data=SessionModel.gql('WHERE instaright_account = :1 ORDER by __key__', user).fetch(1000)
		lastKey = data[-1].key()
		total=len(data)
		while len(data) == 1000:
                        data=SessionModel.gql('WHERE __key__> :1 and instaright_account = :2 ORDER by __key__', lastKey, user).fetch(1000)
			lastKey=data[-1].key()
			total+=len(data)
		return total
	@staticmethod
	def getAll():
		data=SessionModel.gql('ORDER by __key__').fetch(1000)
		if not data:
			return None
		lastKey = data[-1].key()
		results=data
		while len(data) == 1000:
			data=SessionModel.gql('WHERE __key__> :1 ORDER by __key__', lastKey).fetch(1000)
			lastKey=data[-1].key()
			results.extend(data)
		return results
	@staticmethod
	def getDailyStats(targetDate):
		if targetDate is None:
			# take yesterday for targetDate
			targetDate=datetime.date.today() - datetime.timedelta(days=1)
		upperLimitDate = targetDate + datetime.timedelta(days=1)
		data = SessionModel.gql(' WHERE date >= :1 and date < :2 ', targetDate, upperLimitDate).fetch(5000)
		if not data:
			logging.info('no results returned for daily stats')
			return None
		result=[]
		result.extend(data)
		logging.info('daily stats retrieved %s ' % len(result))
		return result
	@staticmethod
	def getWeeklyStats(targetDate):
		if targetDate is None:
			targetDate=datetime.date.today() 
		previousWeek = targetDate - datetime.timedelta(days=7)
		logging.info('ranges %s -> %s ' %( targetDate, previousWeek))
		data = SessionModel.gql(' WHERE date <= :1 and date > :2 ORDER by date, __key__', targetDate, previousWeek).fetch(1000)
		if not data:
			logging.info('no records found for target date %s ' % str(targetDate))
			return None
		lastKey= data[-1].key()
		result = data
		while len(data) == 1000:
			nextK = SessionModel.gql(' WHERE __key__ > :1 ORDER by  __key__, date', lastKey).fetch(1000)
			lastKey=nextK[-1].key()
			data = [ x for x in nextK if x.date <= targetDate and x.date > previousWeek ]
			result.extend(data)
		return result

	@staticmethod
	def getYearStats(targetDate):
		if targetDate is None:
			targetDate=datetime.date.today()
		lastYear = targetDate - datetime.timedelta(days=365)
                result = []
		data = WeeklyDomainStats.gql(' WHERE date <= :1 and date > :2 ORDER by date, __key__', targetDate, lastYear).fetch(1000)
		result = data
                lastKey= data[-1].key()
		while len(data) == 1000:
			nextK = WeeklyDomainStats.gql(' WHERE __key__ > :1 ORDER by  __key__, date', lastKey).fetch(1000)
			lastKey=nextK[-1].key()
			data = [ x for x in nextK if x.date <= targetDate and x.date > lastYear ]
			result.extend(data)
		return result
		

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
class IMInvite(db.Model):
        im = db.StringProperty()
        date = db.DateTimeProperty(auto_now_add = True)
        subscribed = db.BooleanProperty()
class UserDetails(db.Model):
        instapaper_account=db.StringProperty()
        mail =db.StringProperty()
        name =db.StringProperty()
        jid = db.StringProperty()
        #key for download articles
        form_key=db.StringProperty()
        avatar = db.LinkProperty()
        occupations = db.StringProperty()
        location= db.StringProperty()
        facebook = db.LinkProperty()
        bebo = db.LinkProperty()
        myspace = db.LinkProperty()
        friendster = db.LinkProperty()
        linkedin = db.LinkProperty()
        google_reader = db.LinkProperty()
        google_profile = db.LinkProperty()
        twitter = db.LinkProperty()
        flickr = db.LinkProperty()
        youtube = db.LinkProperty()
        hi5 = db.LinkProperty()
        picasa = db.LinkProperty()
        plancast = db.LinkProperty()
        delicious = db.LinkProperty()
        multiply = db.LinkProperty()
        tungle_me = db.LinkProperty()
        livejournal = db.LinkProperty()
        wordpress = db.LinkProperty()
        xmpp_subscription = db.BooleanProperty()
        social_data = db.TextProperty()
	activated_date = db.DateProperty(auto_now_add=True)
        last_active_date = db.DateTimeProperty()
        links_added = db.IntegerProperty(default=0)
        info_updated = db.DateTimeProperty(auto_now_add=True)
	@staticmethod
	def getAll():
		data=UserDetails.gql('ORDER by __key__').fetch(1000)
		if not data:
			return None
		lastKey = data[-1].key()
		results=data
		while len(data) == 1000:
			data=UserDetails.gql('WHERE __key__> :1 ORDER by __key__', lastKey).fetch(1000)
			lastKey=data[-1].key()
			results.extend(data)
		return results

class Links(db.Model):
        url=db.StringProperty()
        all_score=db.IntegerProperty()
        influence_score = db.IntegerProperty()
        instapaper_count=db.IntegerProperty()
        instaright_count=db.IntegerProperty()
        redditups = db.IntegerProperty()
        redditdowns = db.IntegerProperty()
        title = db.StringProperty()
        tweets = db.IntegerProperty()
        diggs = db.IntegerProperty()
        excerpt = db.TextProperty()
        categories = db.StringProperty()
        delicious_count = db.IntegerProperty()
        overall_score = db.IntegerProperty()
        created = db.IntegerProperty()
        date_added = db.DateProperty(auto_now_add=True)



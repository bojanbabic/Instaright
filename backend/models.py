import datetime, logging
from google.appengine.ext import db 

class SessionModel(db.Model): 
	user_agent=db.StringProperty()
	instaright_account=db.StringProperty()
	ip=db.StringProperty()
	url=db.LinkProperty()
        url_hash = db.StringProperty()
        short_url=db.LinkProperty()
        feed_url=db.LinkProperty()
	date=db.DateTimeProperty()
	domain=db.StringProperty()
        title=db.StringProperty()
        version=db.StringProperty()
        client = db.StringProperty()
        embeded = db.TextProperty()
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
                if len(data) == 0:
                        return 0
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
                if len(data) == 0:
                        return 0
		lastKey = data[-1].key()
		total=len(data)
		while len(data) == 1000:
                        data=SessionModel.gql('WHERE __key__> :1 and instaright_account = :2 ORDER by __key__', lastKey, user).fetch(1000)
			lastKey=data[-1].key()
			total+=len(data)
		return total
        @staticmethod
	def countAllForUserForDate(user, date):
                if user is None:
                        return 0
                data=SessionModel.gql('WHERE instaright_account = :1 and date = :2  ORDER by __key__', user, date).fetch(1000)
                if len(data) == 0:
                        return 0
                upperDate = date + datetime.timedelta(days=1)
		lastKey = data[-1].key()
		total=len(data)
		while len(data) == 1000:
                        nextK=SessionModel.gql('WHERE __key__> :1 and instaright_account = :2 ORDER by __key__', lastKey, user).fetch(1000)
			data = [ x for x in nextK if x.date <= date and x.date > upperDate ]
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
        def getDailyDataWithOffset(targetDate, cursor):
                if targetDate is None:
                        targetDate = datetime.date.today() - datetime.timedelta(days=1)
                upperLimitDate = targetDate + datetime.timedelta(days=1)
                logging.info('fetching sessions within limits: %s -> %s' %(str(targetDate), str(upperLimitDate)))
                if cursor:
		        query = SessionModel.gql(' WHERE date >= :1 and date < :2 ', targetDate, upperLimitDate).with_cursor(cursor)
                else:
                        logging.info('no key offset fetching first 1K')
		        query = SessionModel.gql(' WHERE date >= :1 and date < :2 ', targetDate, upperLimitDate)
                data = query.fetch(1000)
                logging.info('fetched data %d' %len(data))
                return data

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
		query = SessionModel.gql(' WHERE date <= :1 and date > :2 ORDER by date, __key__', targetDate, previousWeek)
		data = query.fetch(1000)
		if not data:
			logging.info('no records found for target date %s ' % str(targetDate))
			return None
		result = data
		while len(data) == 1000:
                        cursor = query.cursor()
                        query= SessionModel.gql(' WHERE date <= :1 and date > :2 ORDER by date, __key__', targetDate, previousWeek).with_cursor(cursor)
		        data = query.fetch(1000)
			result.extend(data)
		return result

	@staticmethod
	def getYearStats(targetDate):
		if targetDate is None:
			targetDate=datetime.date.today()
		lastYear = targetDate - datetime.timedelta(days=365)
                result = []
		data = WeeklyDomainStats.gql(' WHERE date <= :1 and date > :2 ORDER by date, __key__', targetDate, lastYear).fetch(1000)
                if len(data) == 0:
                        return 0
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
	totalUserNumber=db.IntegerProperty()
	date=db.DateProperty(auto_now_add=True)

class DailyDomainStats(db.Model):
	domain=db.StringProperty()
	count=db.IntegerProperty(default=0)
	date=db.DateProperty(auto_now_add=True)

class WeeklyDomainStats(db.Model):
	domain=db.StringProperty()
	count=db.IntegerProperty(default=0)
	date=db.DateProperty(auto_now_add=True)

class YearDomainStats(db.Model):
	domain=db.StringProperty()
	count=db.IntegerProperty(default=0)
	date=db.DateProperty(auto_now_add=True)
class LinkStats(db.Model):
	link=db.StringProperty()
	countUpdated=db.DateTimeProperty(auto_now_add=True)
	count=db.IntegerProperty(default=0)
	lastUpdatedBy=db.StringProperty()
class UserLocationModel(db.Model):
	countryCode=db.StringProperty()
	city=db.StringProperty()
	date=db.DateTimeProperty(auto_now_add=True)
	user=db.StringProperty()
class CountryStats(db.Model):
	countryCode=db.StringProperty()
	count=db.IntegerProperty(default=0)
	dateUpdated=db.DateProperty(auto_now_add=True)
class CityStats(db.Model):
	city=db.StringProperty()
	countryCode=db.StringProperty()
	count=db.IntegerProperty(default=0)
	dateUpdated=db.DateProperty(auto_now_add=True)
class Subscription(db.Model):
	subscriber = db.IMProperty(required=True)
	subscriber_mail = db.StringProperty()
	domain = db.StringProperty(required=True)
	activationDate = db.DateTimeProperty(auto_now_add=True)
	active = db.BooleanProperty()
	mute = db.BooleanProperty()
class IMInvite(db.Model):
        im = db.StringProperty()
        date = db.DateTimeProperty(auto_now_add = True)
        subscribed = db.BooleanProperty()
class UserDetails(db.Model):
	instaright_account=db.StringProperty()
	instaright_pswd=db.StringProperty()
        instapaper_account=db.StringProperty()
        mail =db.StringProperty()
        name =db.StringProperty()
        jid = db.StringProperty()
        #key for download articles
        form_key=db.StringProperty()
        avatar = db.LinkProperty()
        occupations = db.TextProperty()
        location= db.StringProperty()
        facebook = db.LinkProperty()
        bebo = db.LinkProperty()
        myspace = db.LinkProperty()
        friendster = db.LinkProperty()
        linkedin = db.LinkProperty()
        google_reader = db.LinkProperty()
        google_profile = db.LinkProperty()
        twitter = db.LinkProperty()
	klout_score=db.IntegerProperty()
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
        twitter_request_sent = db.BooleanProperty()
	twitter_followers=db.TextProperty()
	twitter_following=db.TextProperty()
	facebook_id=db.StringProperty()
	facebook_friends=db.TextProperty()
	facebook_profile=db.StringProperty()
        
	@classmethod
	def getAll(cls):
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

	def getUserInfo(self):
		screen_name= None
		avatar = None
		if self.name is not None:
			screen_name = self.name
		elif self.facebook is not None and self.facebook_profile is not None:
			screen_name = self.facebook_profile
		elif self.twitter is not None:
			screen_name = self.twitter.replace('http://twitter.com/','')
		if self.avatar is not None:
			avatar = self.avatar
		user_info={'screen_name':screen_name, 'avatar': avatar}
		return user_info

class Links(db.Model):
        url=db.TextProperty()
        url_hash=db.StringProperty()
        domain=db.TextProperty()
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
        facebook_like = db.IntegerProperty()
        facebook_share = db.IntegerProperty()
	linkedin_share = db.IntegerProperty()
	buzz_count  = db.IntegerProperty()
	stumble_upons = db.IntegerProperty()
        overall_score = db.IntegerProperty(default=0)
        created = db.IntegerProperty()
        date_added = db.DateProperty(auto_now_add=True)
        date_updated = db.DateProperty(auto_now_add=True)
        recommendation = db.TextProperty()
        desc = db.TextProperty()
        embeded = db.TextProperty()
        shared = db.BooleanProperty(default=False)

class UserStats(db.Model):
        instapaper_account=db.StringProperty()
        count=db.IntegerProperty()
        date=db.DateProperty()
class DeliciousImporter(db.Model):
        instapaper_account=db.StringProperty()
        instapaper_pass=db.StringProperty()
        delicious_account=db.StringProperty()
        success=db.BooleanProperty(default=False)
        date=db.DateTimeProperty(auto_now_add=True)
        oauth_token_secret=db.StringProperty()
        oauth_token=db.StringProperty()
        oauth_expires_in=db.DateTimeProperty()
class Badges(db.Model):
        badge_label = db.StringProperty()
        badge_desc = db.StringProperty()
        badge_icon = db.StringProperty()
        badge_quote = db.StringProperty()
class UserBadge(db.Model):
        user=db.StringProperty()
        badge=db.StringProperty()
        badge_property = db.ReferenceProperty(Badges)
        user_property = db.ReferenceProperty(UserDetails)
        date=db.DateProperty(auto_now_add=True)
class UserSessionFE(db.Model):
	user = db.UserProperty()
	screen_name = db.StringProperty()
	auth_service = db.StringProperty()
	user_uuid = db.StringProperty()
	last_updatetime = db.DateTimeProperty(auto_now_add = True)
	active = db.BooleanProperty()
	user_details = db.ReferenceProperty(UserDetails)
        path=db.StringProperty()
class CategoryDomains(db.Model):
	category=db.StringProperty()
	domains = db.TextProperty()
	
class LinkCategory(db.Model):
        url=db.StringProperty()
        url_hash=db.StringProperty()
        category=db.StringProperty()
        updated=db.DateTimeProperty(auto_now_add = True)
        model_details=db.ReferenceProperty(SessionModel)
	@classmethod
	def getAll(cls):
		data=LinkCategory.gql('ORDER by __key__').fetch(1000)
		if not data:
			return None
		lastKey = data[-1].key()
		results=data
		while len(data) == 1000:
			data=LinkCategory.gql('WHERE __key__> :1 ORDER by __key__', lastKey).fetch(1000)
			lastKey=data[-1].key()
			results.extend(data)
		return results
        @classmethod
        def getAllCategoryCount(cls):
                cats=LinkCategory.getAll()
                if cats is None:
                        return None
                all_cats = [ c.category for c in cats ]
                result = dict((c, all_cats.count(c)) for c in set(all_cats) )
                logging.info(result)
                import operator
                sorted_cats = sorted(result.iteritems(), key=operator.itemgetter(1), reverse=True)
                return dict(sorted_cats)
                
        @classmethod
        def get_trending(cls):
                last_hour = datetime.datetime.now().date() - datetime.timedelta(hours=1)
                cats = LinkCategory.gql('WHERE updated > :1 ' , last_hour).fetch(1000)
                if cats is None:
                        return None
                all_cats = [ c.category for c in cats if len(c.category) > 2 ]
                result = dict( (c, all_cats.count(c)) for c in set(all_cats))
                import operator
                sorted_cats = sorted(result.iteritems(), key=operator.itemgetter(1), reverse=True)
                logging.info(sorted_cats)
                return dict(sorted_cats[:40])


class ScoreUsersDaily(db.Model):
        user=db.ReferenceProperty(UserDetails)
        score=db.IntegerProperty(default=0)
        date=db.DateProperty()

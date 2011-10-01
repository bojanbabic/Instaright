import os
import datetime
import logging
import ConfigParser

from models import SessionModel, LinkCategory, UserStats, UserBadge
class BadgeUtil:

        @staticmethod
        def getBadger(user, url, domain, version):
               trophyBadger=TrophyBadger(user, url, domain, version)
               logging.info('getting proper badger for %s and domain %s (version %s)' %( user, domain , version))
               if trophyBadger.getBadge() is not None:
                        logging.info('initializing trophy badger')
                        return trophyBadger
	       siteSpecBadge=SiteSpecificBadge(user, url, domain, version)	
               if version is not None and siteSpecBadge.getBadge() is not None:
                        logging.info('initializing site specific badger: %s' %domain)
                        return siteSpecBadge 
               speedLimitBadger=SpeedLimitBadger(user, url, domain, version)
               clubBadger=ClubBadger(user, url, domain, version)
               if speedLimitBadger.getBadge() is not None:
                        logging.info('initializing speed limit badger')
                        return speedLimitBadger
               if clubBadger.getBadge() is not None:
                        logging.info('initializing club badger')
                        return clubBadger
               usageBadge=ContinuousUsageBadge(user, url, domain, version)
               if usageBadge.getBadge() is not None:
                        logging.info('initializing usage badger')
                        return usageBadge
               return None
                
class ContinuousUsageBadge:
        def __init__(self, user, url, domain, version):
                self.user = user
                self.url = url
                self.domain = domain
                self.version=version
        def getBadge(self):
                returnBadge=5
                existingBadge=UserBadge.gql('WHERE user = :1 and badge = :2', self.user, returnBadge).get()
                if existingBadge is  not None:
                        logging.info('Already assigned 5 day usage badge. Skipping.')
                        return None
                if self.version is None:
                        logging.info('Older version of addon not usage badge defined!')
                        return None
                yesterday=datetime.datetime.now().date() - datetime.timedelta(days=1)
                limit=datetime.datetime.now().date() - datetime.timedelta(days=4)
                active=True
                while yesterday >= limit:
                       s=SessionModel.gql('WHERE date = :1 and instaright_account = :2', yesterday, self.user).get()
                       if s is None:
                                logging.info('user %s NOT active for date %s' %(self.user, yesterday))
                                active=False
                                return None
                       else:
                                logging.info('user %s active for date %s' %(self.user, yesterday))
                       yesterday-=datetime.timedelta(days=1)
                if active:        
                        logging.info('user %s has been active in last %s' %(self.user, returnBadge))
                        return '5'
                logging.info('usage badge %s: not initialized' %self.user)

class SpeedLimitBadger:
        def __init__(self, user, url, domain, version):
                self.user = user
                self.url = url
                self.domain = domain
                self.version=version
        def getBadge(self):
               midnight = datetime.datetime.now().date()
               currentCount=SessionModel.gql('WHERE date >= :1 and instaright_account = :2', midnight, self.user).count()
               logging.info('current daily user count : %s -> %s' %(self.user, currentCount))
               if currentCount >= 105:
                        return '105'
               if currentCount >= 65:
                        return '65'
               if currentCount >= 55:
                        return '55'
               if currentCount >= 25:
                        return '25'
               logging.info('speed limit badge %s: not initialized' %self.user)
               return None

class SiteSpecificBadge(object):
	newsProps=ConfigParser.ConfigParser()
	movieProps=ConfigParser.ConfigParser()
	nyProps=ConfigParser.ConfigParser()
	economyProps=ConfigParser.ConfigParser()
	gadgetProps=ConfigParser.ConfigParser()
	wikiProps=ConfigParser.ConfigParser()
	sportProps=ConfigParser.ConfigParser()
	categoryProps=ConfigParser.ConfigParser()
        def __init__(self, user, url, domain, version):
                self.user = user
                self.url = url
                self.domain = domain
                self.version=version
		#read domain lists
		self.newsProps.read(os.path.split(os.path.realpath(__file__))[0]+'/../properties/badges/news/news.properties')
		self.newsDomains=self.newsProps.get('news','domains').split(',')
		self.news_tresshold=int(self.newsProps.get('news','tresshold'))

		self.movieProps.read(os.path.split(os.path.realpath(__file__))[0]+'/../properties/badges/movie/movie.properties')
		self.movieDomains=self.movieProps.get('movie','domains').split(',')
		self.movie_tresshold=int(self.movieProps.get('movie','tresshold'))

		self.nyProps.read(os.path.split(os.path.realpath(__file__))[0]+'/../properties/badges/ny/ny.properties')
		self.nyDomains=self.nyProps.get('ny','domains').split(',')
		self.ny_tresshold=int(self.nyProps.get('ny','tresshold'))

		self.economyProps.read(os.path.split(os.path.realpath(__file__))[0]+'/../properties/badges/economy/economy.properties')
		self.economyDomains=self.economyProps.get('economy','domains').split(',')
		self.economy_tresshold=int(self.economyProps.get('economy','tresshold'))

		self.gadgetProps.read(os.path.split(os.path.realpath(__file__))[0]+'/../properties/badges/gadget/gadget.properties')
		self.gadgetDomains=self.gadgetProps.get('gadget','domains').split(',')
		self.gadget_tresshold=int(self.gadgetProps.get('gadget','tresshold'))

		self.wikiProps.read(os.path.split(os.path.realpath(__file__))[0]+'/../properties/badges/wiki/wiki.properties')
		self.wikiDomains=self.wikiProps.get('wiki','domains').split(',')
		self.wiki_tresshold=int(self.wikiProps.get('wiki','tresshold'))

		self.sportProps.read(os.path.split(os.path.realpath(__file__))[0]+'/../properties/badges/sport/sport.properties')
		self.sportDomains=self.sportProps.get('sport','domains').split(',')
		self.sport_tresshold=int(self.sportProps.get('sport','tresshold'))

		self.categoryProps.read(os.path.split(os.path.realpath(__file__))[0]+'/../properties/badges/category2badge.ini')
		self.gadgetCategories=self.categoryProps.get('category','gadget').split(',')
		self.economyCategories=self.categoryProps.get('category','economy').split(',')
		self.wikiCategories=self.categoryProps.get('category','wiki').split(',')
		self.sportCategories=self.categoryProps.get('category','sports').split(',')
		self.newsCategories=self.categoryProps.get('category','news').split(',')

        def getBadge(self):
                if self.domain in self.nyDomains:
                        return self.getnytbadge()
                logging.info('domain %s not in ny domains %s' %(self.domain, self.nyDomains))
                if self.domain in self.movieDomains:
                        return self.getmoviebadge()
                logging.info('domain %s not in movie domains %s' %(self.domain, self.movieDomains))
                if self.domain in self.economyDomains:
                        return self.geteconomybadge()
                logging.info('domain %s not in economy domains %s' %(self.domain, self.economyDomains))
                if self.domain in self.gadgetDomains:
                        return self.getgadgetbadge()
                logging.info('domain %s not in gadget domains %s' %(self.domain, self.gadgetDomains))
                if self.domain in self.sportDomains:
                        return self.getsportbadge()
                logging.info('domain %s not in sport domains %s' %(self.domain, self.sportDomains))
                if self.domain in self.wikiDomains:
                        return self.getwikibadge()
                logging.info('domain %s not in wiki domains %s' %(self.domain, self.wikiDomains))
                if self.domain in self.newsDomains:
                        return self.getnewsbadge()
                else:
                        logging.info('domain %s not in news domains %s' %(self.domain, self.newsDomains))
                        logging.info('no domain specific badge initialized or no addon version')
                        return None
        def getnytbadge(self):
               midnight = datetime.datetime.now().date()
               nyTotal=SessionModel.gql('where domain in :1 and date >= :2 and instaright_account = :3', self.nyDomains, midnight, self.user).count()
               logging.info('site specific badger(NY): fetched stats %s' % nyTotal)
               if nyTotal >= self.ny_tresshold:
                        logging.info('setting ny badge for user %s ' %self.user)
                        return 'ny'
               else:
                        logging.info('for user %s still tresshold of %s still not reached %s' %(self.user, self.ny_tresshold, nyTotal))
                        return None
        def getmoviebadge(self):
               midnight = datetime.datetime.now().date()
               currentCount=SessionModel.gql('where domain in :1 and date >= :2 and instaright_account = :3', self.movieDomains, midnight, self.user).count()
               logging.info('site specific badger(movie): fetched stats %s' % currentCount)
               if currentCount >= self.movie_tresshold:
                        logging.info('setting movie badge for user %s ' %self.user)
                        return 'movie'
               else:
                        logging.info('for user %s still tresshold of %s still not reached %s' %(self.user, self.movie_tresshold, currentCount))
                        return None
        def geteconomybadge(self):
               midnight = datetime.datetime.now().date()
               currentCount=SessionModel.gql('where domain in :1 and date >= :2 and instaright_account = :3', self.economyDomains, midnight, self.user).count()
	       categoryCount = LinkCategory.gql('WHERE category in :1 and date >= :2', self.economyCategories, midnight).fetch(1000)
	       categoryRefined = [ lc for lc in categoryCount if lc.model_details.instaright_account == self.user ]
	       cat_user_count = len(categoryRefined)
               logging.info('site specific badger(economy): fetched stats %s economy categories:%s' % (currentCount, cat_user_count))
               if currentCount + cat_user_count >= self.economy_tresshold:
                        logging.info('setting economy badge for user %s ' %self.user)
                        return 'yen'
               else:
                        logging.info('for user %s still tresshold of %s still not reached %s' %(self.user, self.economy_tresshold, currentCount))
                        return None
        def getgadgetbadge(self):
               midnight = datetime.datetime.now().date()
               currentCount=SessionModel.gql('where domain in :1 and date >= :2 and instaright_account = :3', self.gadgetDomains, midnight, self.user).count()
	       categoryCount = LinkCategory.gql('WHERE category in :1 and date >= :2', self.gadgetCategories, midnight).fetch(1000)
	       categoryRefined = [ lc for lc in categoryCount if lc.model_details.instaright_account == self.user ]
	       cat_user_count = len(categoryRefined)
               logging.info('site specific badger(gadget): fetched stats %s and category count %s' % (currentCount, cat_user_count))
               if currentCount + cat_user_count >= self.gadget_tresshold:
                        logging.info('setting gadget badge for user %s ' %self.user)
                        return 'robot'
               else:
                        logging.info('for user %s still tresshold of %s still not reached %s' %(self.user, self.gadget_tresshold, currentCount))
                        return None
        def getnewsbadge(self):
               midnight = datetime.datetime.now().date()
               currentCount=SessionModel.gql('where domain in :1 and date >= :2 and instaright_account = :3', self.newsDomains, midnight, self.user).count()
	       categoryCount = LinkCategory.gql('WHERE category in :1 and date >= :2', self.newsCategories, midnight).fetch(1000)
	       categoryRefined = [ lc for lc in categoryCount if lc.model_details.instaright_account == self.user ]
	       cat_user_count = len(categoryRefined)
               logging.info('site specific badger(news): fetched stats %s and category count %s' % (currentCount, cat_user_count))
               if currentCount + cat_user_count >= self.news_tresshold:
                        logging.info('setting news badge for user %s ' %self.user)
                        return 'news'
               else:
                        logging.info('for user %s still tresshold of %s still not reached %s' %(self.user, self.news_tresshold, currentCount))
                        return None

        def getwikibadge(self):
               midnight = datetime.datetime.now().date()
               currentCount=SessionModel.gql('where domain in :1 and date >= :2 and instaright_account = :3', self.wikiDomains, midnight, self.user).count()
	       categoryCount = LinkCategory.gql('WHERE category in :1 and date >= :2', self.wikiCategories, midnight).fetch(1000)
	       categoryRefined = [ lc for lc in categoryCount if lc.model_details.instaright_account == self.user ]
	       cat_user_count = len(categoryRefined)
               logging.info('site specific badger(wiki): fetched stats %s and category %s' % (currentCount, cat_user_count))
               if currentCount + cat_user_count >= self.wiki_tresshold:
                        logging.info('setting wiki badge for user %s ' %self.user)
                        return 'news'
               else:
                        logging.info('for user %s still tresshold of %s still not reached %s' %(self.user, self.wiki_tresshold, currentCount))
                        return None

        def getsportbadge(self):
               midnight = datetime.datetime.now().date()
               currentCount=SessionModel.gql('where domain in :1 and date >= :2 and instaright_account = :3', self.sportDomains, midnight, self.user).count()
	       categoryCount = LinkCategory.gql('WHERE category in :1 and date >= :2', self.sportCategories, midnight).fetch(1000)
	       categoryRefined = [ lc for lc in categoryCount if lc.model_details.instaright_account == self.user ]
	       cat_user_count = len(categoryRefined)
               logging.info('site specific badger(sport): fetched stats %s and category count %s' % (currentCount, cat_user_count))
               if currentCount + cat_user_count >= self.sport_tresshold:
                        logging.info('setting news badge for user %s ' %self.user)
                        return 'sport'
               else:
                        logging.info('for user %s still tresshold of %s still not reached %s' %(self.user, self.sport_tresshold, currentCount))
                        return None

class ClubBadger:
        def __init__(self, user, url, domain, version):
                self.user = user
                self.url = url
                self.domain = domain
                self.version=version
        def getBadge(self):
                allForUser=SessionModel.all()
                allForUser.filter("instaright_account =", self.user)
                count=allForUser.count(10000)
                logging.info('club badger: fetched stats %s' % count)
                if count >= 10000:
                        return '10000'
                if count >= 5000:
                        return '5000'
                if count >= 1000:
                        return '1000'
                logging.info('club badger %s: not initialized' % self.user )
                return None
class TrophyBadger:
        def __init__(self, user, url, domain, version):
                self.user = user
                self.url = url
                self.domain = domain
                self.version=version
        def getBadge(self):
                targetdate=datetime.datetime.now().date() - datetime.timedelta(days=1)
                stats = UserStats.gql('WHERE date = :1 and count > 10 order by count desc', targetdate).fetch(3)
                logging.info('trophy badger: fetched stats %s' % len(stats))
		stats = [ s.instapaper_account for s in stats if s is not None ]
                if stats is None or len(stats) == 0:
			logging.info('Not enough data for calc badge')
			return None
                if stats[0] == self.user:
			logging.info('User was number ONE user yesterday')
                        return '1'
                if stats[1] == self.user:
			logging.info('User was number TWO user yesterday')
                        return '2'
                if stats[2] == self.user:
			logging.info('User was number THREE user yesterday')
                        return '3'
                logging.info('trophy badge %s: not initialized' % self.user )
                return None

                 

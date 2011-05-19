import sys, urllib2, exceptions, os, logging, datetime, time

from utils import StatsUtil,Cast, TaskUtil, ConfigParser, LinkUtil
from users import UserUtil
from models import Links
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api.labs import taskqueue
from google.appengine.ext.db import BadValueError
                
sys.path.append('../social')
from social_activity import Twit

sys.path.append(os.path.join(os.path.dirname(__file__),'lib'))
import simplejson

class LinkHandler(webapp.RequestHandler):
	def __init__(self):
		config=ConfigParser.ConfigParser()
		config.read('../properties/general.ini')
		try:
			self.fb_factor=int(config.get('social', 'fb_factor'))
			self.tw_factor=int(config.get('social', 'tw_factor'))
			self.tw_margin=int(config.get('social', 'tw_margin'))
		except:
			logging.error('properties propblem on path %s' % os.path.join(os.path.dirname(__file__),'properties/general.ini'))

        def post(self):
                count = self.request.get('count',None)
                url = self.request.get('url',None)
                url = urllib2.unquote(url)
                domain = StatsUtil.getDomain(url)
                if not domain or len(domain) == 0:
                        self.response.out.write('not url: %s skipping!\n' %url)
                        return
                logging.info('url %s' % url)
                logging.info('count %s' % count)
                link = self.getAllData(url, count)
		self.update_link(url, link)
                self.response.out.write('put %s \n ' %url)

	def update_link(self, url, link):
		existingLink=None
		try:
                	existingLink = Links.gql('WHERE url = :1', url).get()
		except BadValueError:
			logging.info('bad value for url %s' % url)
                if existingLink is not None:
                        existingLink.date_updated= link.date_updated
                        existingLink.influence_score= link.influence_score
                        existingLink.instapaper_count= link.instapaper_count
                        existingLink.instaright_count=link.instaright_count
                        existingLink.redditups=link.redditups
                        existingLink.redditdowns=link.redditdowns
                        existingLink.tweets=link.tweets
                        existingLink.diggs=link.diggs
                        existingLink.excerpt=link.excerpt
                        existingLink.categories=link.categories
                        existingLink.delicious_count=link.delicious_count
                        existingLink.facebook_like=link.facebook_like
			existingLink.domain = link.domain
                        #if increase in score is more then 20%
                        if  existingLink.overall_score == 0 or link.overall_score  / existingLink.overall_score >= 1.2:
                                existingLink.shared=False
                        existingLink.overall_score=link.overall_score
                        existingLink.put()
                else:
			#greater probability for db timeout of new links
			try:
				while True:
					timeout_ms = 100
					try:
                        			link.put()
						break
					except datastore_errors.Timeout:
						thread.sleep(timeout_ms)
						timeout_ms *= 2
			except apiproxy_errors.DeadlineExceededError:
				logging.info('run out of retries for writing to db')
                logging.info('url %s : influence_score %s, instapaper_count %s, redditups %s, redditdowns %s, tweets %s, diggs %s, delicious count %s facebook like %s' %(url, link.influence_score , link.instapaper_count, link.redditups, link.redditdowns, link.tweets, link.diggs, link.delicious_count, link.facebook_like))

        def get(self):
                self.response.out.write('get')

	def delicious_data(self, url):
                delicious_api='http://feeds.delicious.com/v2/json/urlinfo/data?url=%s&type=json' % url
                logging.info('trying to fetch delicious info %s ' % delicious_api)
                json =LinkUtil.getJsonFromApi(delicious_api)
		link=Links()
                if json:
                        try:
                                if not link.title:
                                        link.title = json[0]['title']
                                link.categories = db.Text(unicode(simplejson.dumps(json[0]['top_tags'])))
                                if link.categories is not None:
                                        taskqueue.add(queue_name='category-queue', url='/link/category/delicious', params={'url':url, 'categories':link.categories})
                                link.delicious_count = Cast.toInt(json[0]['total_posts'],0)
				logging.info('delicious count %s' % link.delicious_count)
                        except KeyError:
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('key error [[%s, %s]] in %s' %(e0, e1, json))
		return link

        def getAllData(self,url, count=0):

		domain = StatsUtil.getDomain(url)
		logging.info('from %s domain %s' %( url, domain))
		url=urllib2.quote(url.encode('utf-8'))

                topsy_api='http://otter.topsy.com/stats.json?url=%s' % url
                tweet_meme_api='http://api.tweetmeme.com/url_info.json?url=%s' %url
                delicious_api='http://feeds.delicious.com/v2/json/urlinfo/data?url=%s&type=json' % url
                digg_api='http://services.digg.com/1.0/endpoint?method=story.getAll&link=%s&type=json' %url
                reddit_api='http://www.reddit.com/api/info.json?url=%s' %url
                facebook_api='https://api.facebook.com/method/fql.query?query=select%20%20like_count,share_count%20from%20link_stat%20where%20url=%22'+url+'%22&format=json'
                linkedin_api='http://www.linkedin.com/cws/share-count?url=%s' % url
		stumble_upon_api='http://www.stumbleupon.com/services/1.01/badge.getinfo?url=%s' %url
		buzz_api = 'https://www.googleapis.com/buzz/v1/activities/count?alt=json&url=%s' % url
		alternate_api='http://api.sharedcount.com/?url=%s' %url

		link = None
		alternate_twitter_score = None
		alternate_buzz_score = None
		alternate_digg_score = None
		alternate_facebook_share_score = None
		alternate_facebook_like_score = None
		alternate_su_score = None
                alternate_linkedin_score = None
		
		try:
                	link = Links.gql('WHERE url = :1', url).get()
		except BadValueError:
			logging.info('url property too long')
                if link is None:
                        link = Links()
			link.domain = domain
                        link.instapaper_count = Cast.toInt(count,0)
                        link.url = urllib2.unquote(url).decode('utf-8')
                        link.redditups = 0
                        link.redditdowns = 0
                        link.tweets = 0
                        link.diggs = 0
                        link.delicious_count = 0
                        link.overall_score = 0
                        link.shared = False
                else:
                        link.date_updated = datetime.datetime.now().date()
			link.domain = domain

		#relaxation 
		link.relaxation = 0

                logging.info('trying to fetch shared count info %s' %alternate_api )
                json = LinkUtil.getJsonFromApi(alternate_api)
                if json:
                        try:
                                alternate_twitter_score=Cast.toInt(json['Twitter'],0)
                                alternate_buzz_score=Cast.toInt(json['Buzz'],0)
                                alternate_digg_score=Cast.toInt(json['Diggs'],0)
                                alternate_facebook_share_score=Cast.toInt(json['Facebook']['share_count'],0)
                                alternate_facebook_like_score=Cast.toInt(json['Facebook']['like_count'],0)
                                alternate_su_score=Cast.toInt(json['StumbleUpon'],0)
                                alternate_linkedin_score=Cast.toInt(json['LinkedIn'],0)

                        except KeyError:
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('key error [[%s, %s]] in %s' %(e0, e1, json))

                logging.info('trying to fetch topsi info %s' %topsy_api)
                json = LinkUtil.getJsonFromApi(topsy_api)
                if json:
                        try:
                                link.influence_score=Cast.toInt(json['response']['influential'],0)
                                link.all_score=Cast.toInt(json['response']['all'],0)
                        except KeyError:
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('key error [[%s, %s]] in %s' %(e0, e1, json))

                logging.info('trying to fetch digg info %s' %digg_api)
                json =LinkUtil.getJsonFromApi(digg_api)
                if json:
                        try:
                                link.diggs =Cast.toInt(json['count'],0)
				logging.info('diggs %s' %link.diggs)
                        except KeyError:
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('key error [[%s, %s]] in %s' %(e0, e1, json))
		elif alternate_digg_score is not None:
			logging.info('using alternate digg score %s' % alternate_digg_score)
			link.diggs = alternate_digg_score
                if link.diggs is not None:
                        link.overall_score += link.diggs

                logging.info('trying to fetch tweet_meme info %s ' % tweet_meme_api )
                json = LinkUtil.getJsonFromApi(tweet_meme_api)
                if json and 'story' in json:
                        try:
                                link.tweets=Cast.toInt(json['story']['url_count'],0)
                                link.title=json['story']['title']
			 	if 'excerpt' in json['story']:	
					logging.info('getting excerpt');
                                	link.excerpt = db.Text(unicode(json['story']['excerpt']))
				logging.info('tweets %s' % link.tweets)
                        except KeyError:
				link.relaxation = link.relaxation + 1
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('key error [[%s, %s]] in %s' %(e0, e1, json))
		elif alternate_twitter_score is not None:
			logging.info('using altenate twitter score %s' % alternate_twitter_score)
			link.tweets = alternate_twitter_score
                if link.tweets is not None:
                	link.overall_score += self.tw_factor * link.tweets

                logging.info('trying to fetch delicious info %s ' % delicious_api)
                json =LinkUtil.getJsonFromApi(delicious_api)
                if json:
                        try:
                                if not link.title:
                                        link.title = json[0]['title']
                                link.categories = db.Text(unicode(simplejson.dumps(json[0]['top_tags'])))
                                link.delicious_count = Cast.toInt(json[0]['total_posts'],0)
				logging.info('delicious count %s' % link.delicious_count)
                                if link.delicious_count is not None:
                                        link.overall_score += link.delicious_count
                        except KeyError:
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('key error [[%s, %s]] in %s' %(e0, e1, json))

                logging.info('trying to fetch reddit info %s' % reddit_api)
                json = LinkUtil.getJsonFromApi(reddit_api)
                if json and 'data' in json:
                        try:
                                data = [ x for x in json['data']['children']]
                                top_upped = sorted(data, key=lambda ups: ups['data']['ups'], reverse=True)
                                if top_upped:
                                     link.redditups = Cast.toInt(top_upped[0]['data']['ups'],0)
                                     link.redditdowns = Cast.toInt(top_upped[0]['data']['downs'],0)
                                     link.created = Cast.toInt(top_upped[0]['data']['created'],0)
				     logging.info('reddit ups %s' % link.redditups)
                                     if link.redditups is not None:
                                                link.overall_score += link.redditups
                                     if link.redditdowns is not None:
                                                link.overall_score -= link.redditdowns
                        except KeyError:
				link.relaxation = link.relaxation + 1
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('key error [[%s, %s]] in %s' %(e0, e1, json))
                logging.info('trying to fetch facebook info %s' %facebook_api)
                json = LinkUtil.getJsonFromApi(facebook_api)
                if json:
                        try:
                                link.facebook_like=Cast.toInt(json[0]['like_count'], 0)
                                link.facebook_share=Cast.toInt(json[0]['share_count'], 0)
				logging.info('facebook likes %s' % link.facebook_like)
				logging.info('facebook share %s' % link.facebook_share)

                        except KeyError:
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('request: %s == more info: key error [[%s, %s]] in %s' %(facebook_api, e0, e1, json))
		elif alternate_facebook_like_score is not None:
			logging.info('using alternate facebook like count %s' % alternate_facebook_like_score)
			link.facebook_like_score = alternate_facebook_like_score
		elif alternate_facebook_share_score is not None:
			logging.info('using alternate facebook share count %s' % alternate_facebook_share_score)
			link.facebook_share = alternate_facebook_share_count
                if link.facebook_like is not None:
                        link.overall_score += self.fb_factor * link.facebook_like
                if link.facebook_share is not None:
                        link.overall_score += link.facebook_share

		logging.info('trying to fetch stumple upon link %s' % stumble_upon_api)
		json = LinkUtil.getJsonFromApi(stumble_upon_api)
		if json:
			try:
				link.stumble_upons = Cast.toInt(json['result']['views'], 0)
				logging.info('stumle_score %s' % link.stumble_upons)
				if not link.title:
					link.title = json['result']['title']
					logging.info('settting stumble title: %s' % link.title)
			except KeyError:
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('request: %s == more info: key error [[%s, %s]] in %s' %(stumble_upon_api, e0, e1, json))
		elif alternate_su_score is not None:
			logging.info('using alternate su score %s' % alternate_su_score )
			links.stumble_upons = alternate_su_score
		if link.stumble_upons is not None:
			link.overall_score += link.stumble_upons

		# specific from linkedin since response is in jsonp
		logging.info('trying to fetch linkedin upon link %s' % linkedin_api)
		try:
                        dta = urllib2.urlopen(linkedin_api)
			res = dta.read()
			res = res.replace('IN.Tags.Share.handleCount(','')
			res = res.replace(');','')
			json = simplejson.loads(res)
			
			link.linkedin_share = Cast.toInt(json['count'], 0)
			logging.info('linked in shares %s' % link.linkedin_share)
			if link.linkedin_share is not None:
					link.overall_score += link.linkedin_share
		except:
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('request: %s == more info: [[%s, %s]] in %s' %(linkedin_api, e0, e1, json))

                if link.linkedin_share is None and alternate_linkedin_score is not None:
                        logging.info('using alternate linkedin score %s' % alternate_linkedin_score)
                        link.linkedin_share = alternate_linkedin_score
                        link.overall_score += alternate_linkedin_score

		logging.info('trying to fetch buzz upon link %s' % buzz_api)
		json = LinkUtil.getJsonFromApi(buzz_api)
		if json:
			try:
				link.buzz_count = Cast.toInt(json['data']['counts']["%s"][0]["count"] % url, 0)
				logging.info('buzz share %s' % link.buzz_count)
			except KeyError:
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('request: %s == more info: key error [[%s, %s]] in %s' %(stumble_upon_api, e0, e1, json))
		elif alternate_buzz_score is not None:
			logging.info('using alternate buzz score %s' % alternate_buzz_score)
			link.buzz = alternate_buzz_score
		if link.buzz_count is not None:
			link.overall_score += link.buzz_count

                return link

        def getData(self, url):
                try:
                        dta = urllib2.urlopen(url)
                        json = simplejson.load(dta)
                        return json
                except:
                        logging.info('error while getting link %s reTRYing'  % url)
                	try:
                        	dta = urllib2.urlopen(url)
                        	json = simplejson.load(dta)
                        	return json
                	except:
                        	e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                        	logging.info('error %s %s, while getting link %s'  %( e0, e1, url))
                        	return None

class LinkTractionTask(webapp.RequestHandler):
	def __init__(self):
		config=ConfigParser.ConfigParser()
		config.read(os.path.split(os.path.realpath(__file__))[0]+'/../properties/general.ini')
		self.tw_margin=int(config.get('social', 'tw_margin'))
		self.tw_factor=int(config.get('social', 'tw_factor'))
		self.klout_correction=int(config.get('social', 'klout_correction'))
		self.klout_api_key=config.get('social', 'klout_api_key')
	def post(self):

                url = self.request.get('url',None)
		if url is None:
			logging.info('no url detected. skipping...')
			return
		user = self.request.get('user', None)
		title = self.request.get('title', None)
		logging.info('title %s' % title)
		
                count = 1
                url = urllib2.unquote(url)
                domain = StatsUtil.getDomain(url)
                if not domain or len(domain) == 0:
                        self.response.out.write('not url: %s skipping!\n' %url)
                        return
                if "lifehacker.com" in url or "twitter.com" in url or "google.com" in url or "instapaper.com" in url or  "facebook.com" in url or  "edition.cnn.com" in url or "maps.google.com" in url or "wikipedia.org" in url or "yahoo.com" in url or "doubleclick.net" in url or "instaright.com" in url:
                                logging.info('filering out %s' %url)
                                return
		lh = LinkHandler()
                link = lh.getAllData(url, count)
		logging.info('link overall score: %s' % link.overall_score)

		existingLink = None
		try:
	                existingLink = Links.gql('WHERE url = :1', url).get()
		except BadValueError:
			logging.info('bad value url %s' % url)
		#if hasattr(link, 'relaxation') and link.relaxation > 0:
		#	twit_margin = twit_margin - 100 * link.relaxation
		#	logging.info('margin relaxation: %s' % twit_margin)
		klout_score = UserUtil.getKloutScore(user, self.klout_api_key)
		share_margin = self.tw_margin
		if klout_score is not None:
			link.overall_score = link.overall_score * int(klout_score)
			logging.info('adjusted overall score %s' % link.overall_score)
			share_margin = share_margin * self.klout_correction
			logging.info('adjusting twit margin: %s' % share_margin)
                
		if link.overall_score > share_margin and existingLink is None:
                        t=Twit()
                        t.style=True
                        t.textFromHotLink(link, title)
			if t.text is None:
				logging.info('twit with no body. aborting')
				return
			execute_time=TaskUtil.execution_time()
			logging.info('scheduling tweet for %s' %str(execute_time))
			
                        taskqueue.add(url='/util/twitter/twit/task', eta=execute_time, queue_name='twit-queue', params={'twit':t.text})
		lh.update_link(url, link)

application = webapp.WSGIApplication(
                                        [
                                                ('/link/add', LinkHandler),
                        			('/link/traction/task',LinkTractionTask),
                                                ],
                                        debug=True)
def main():
        run_wsgi_app(application)


if __name__ == "__main__":
        main()

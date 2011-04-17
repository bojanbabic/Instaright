import sys, urllib2, simplejson, exceptions, os, logging, datetime, time, urllib
#TODO create class for all APIes used
#class GenericApi:
#        def __init__:

#class TopsyApi:
#        def getInfo(self):
#print os.environ['INSTAPAPER']
#sys.path.append('..')
from utils import StatsUtil,Cast, TaskUtil, ConfigParser
from users import UserUtil
from models import Links
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api.labs import taskqueue
from google.appengine.ext.db import BadValueError
                
sys.path.append('../social')
from social_activity import Twit

class LinkHandler(webapp.RequestHandler):
	def __init__(self):
		config=ConfigParser.ConfigParser()
		config.read('../properties/general.ini')
		self.fb_factor=int(config.get('social', 'fb_factor'))
		self.tw_factor=int(config.get('social', 'tw_factor'))
		self.tw_margin=int(config.get('social', 'tw_margin'))

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

        def getAllData(self,url, count):
		url=urllib.quote(url)
                topsy_api='http://otter.topsy.com/stats.json?url=%s' % url
                tweet_meme_api='http://api.tweetmeme.com/url_info.json?url=%s' %url
                delicious_api='http://feeds.delicious.com/v2/json/urlinfo/data?url=%s&type=json' % url
                digg_api='http://services.digg.com/1.0/endpoint?method=story.getAll&link=%s&type=json' %url
                reddit_api='http://www.reddit.com/api/info.json?url=%s'
                facebook_api='https://api.facebook.com/method/fql.query?query=select%20%20like_count%20from%20link_stat%20where%20url=%22'+url+'%22&format=json'
		link = None
		try:
                	link = Links.gql('WHERE url = :1', url).get()
		except BadValueError:
			logging.info('url property too long')
                if link is None:
                        link = Links()
                        link.instapaper_count = Cast.toInt(count,0)
                        link.url = url
                        link.redditups = 0
                        link.redditdowns = 0
                        link.tweets = 0
                        link.diggs = 0
                        link.delicious_count = 0
                        link.overall_score = 0
                        link.shared = False
                else:
                        link.date_updated = datetime.datetime.now().date()

		#relaxation 
		link.relaxation = 0
                logging.info('trying to fetch topsi info %s' %topsy_api)
                json = self.getData(topsy_api)
                if json:
                        try:
                                link.influence_score=Cast.toInt(json['response']['influential'],0)
                                link.all_score=Cast.toInt(json['response']['all'],0)
                        except KeyError:
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('key error [[%s, %s]] in %s' %(e0, e1, json))

                logging.info('trying to fetch digg info %s' %digg_api)
                json =self.getData(digg_api)
                if json:
                        try:
                                link.diggs =Cast.toInt(json['count'],0)
                                if link.diggs is not None:
                                        link.overall_score += link.diggs

                        except KeyError:
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('key error [[%s, %s]] in %s' %(e0, e1, json))

                logging.info('trying to fetch tweet_meme info %s ' % tweet_meme_api )
                json = self.getData(tweet_meme_api)
                if json and 'story' in json:
                        try:
                                link.tweets=Cast.toInt(json['story']['url_count'],0)
                                link.title=json['story']['title']
			 	if 'excerpt' in json['story']:	
					logging.info('getting excerpt');
                                	link.excerpt = db.Text(unicode(json['story']['excerpt']))
                                if link.tweets is not None:
                                        link.overall_score += self.tw_factor * link.tweets
                        except KeyError:
				link.relaxation = link.relaxation + 1
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('key error [[%s, %s]] in %s' %(e0, e1, json))

                logging.info('trying to fetch delicious info %s ' % delicious_api)
                json =self.getData(delicious_api)
                if json:
                        try:
                                if not link.title:
                                        link.title = json[0]['title']
                                link.categories = db.Text(unicode(simplejson.dumps(json[0]['top_tags'])))
                                link.delicious_count = Cast.toInt(json[0]['total_posts'],0)
                                if link.delicious_count is not None:
                                        link.overall_score += link.delicious_count
                        except KeyError:
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('key error [[%s, %s]] in %s' %(e0, e1, json))

                logging.info('trying to fetch reddit info %s' % reddit_api)
                json = self.getData(reddit_api)
                if json and 'data' in json:
                        try:
                                data = [ x for x in json['data']['children']]
                                top_upped = sorted(data, key=lambda ups: ups['data']['ups'], reverse=True)
                                if top_upped:
                                     link.redditups = Cast.toInt(top_upped[0]['data']['ups'],0)
                                     link.redditdowns = Cast.toInt(top_upped[0]['data']['downs'],0)
                                     link.created = Cast.toInt(top_upped[0]['data']['created'],0)
                                     if link.redditups is not None:
                                                link.overall_score += link.redditups
                                     if link.redditdowns is not None:
                                                link.overall_score -= link.redditdowns
                        except KeyError:
				link.relaxation = link.relaxation + 1
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('key error [[%s, %s]] in %s' %(e0, e1, json))
                logging.info('trying to fetch facebook info %s' %facebook_api)
                json = self.getData(facebook_api)
                if json:
                        try:
                                link.facebook_like=Cast.toInt(json[0]['like_count'], 0)
                                if link.facebook_like is not None:
                                        link.overall_score += self.fb_factor * link.facebook_like
                        except KeyError:
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('request: %s == more info: key error [[%s, %s]] in %s' %(facebook_api, e0, e1, json))

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
		config.read('../properties/general.ini')
		self.tw_margin=int(config.get('social', 'tw_margin'))
		self.tw_factor=int(config.get('social', 'tw_factor'))
		self.klout_correction=int(config.get('social', 'klout_correction'))
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
		klout_score = UserUtil.getKloutScore(user)
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

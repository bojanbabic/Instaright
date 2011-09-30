# -*- coding: utf-8 -*-
import datetime
import os
import sys
import urllib2
import logging
import ConfigParser

from google.appengine.ext import webapp
from google.appengine.api import memcache, urlfetch
from google.appengine.ext import db
from google.appengine.api.labs import taskqueue
from google.appengine.ext.webapp.util import run_wsgi_app

from models import UserDetails, Links
from utils import LinkUtil,StatsUtil

sys.path.append('social')
sys.path.append(os.path.join(os.path.dirname(__file__),'lib'))
import simplejson
import twitter

tweet_replies = [ 
                ' Definitely you should try #instapaper #firefox addon http://bit.ly/instaright #getsatisfaction ',
                ' You can also check Instapaper firefox addon http://bit.ly/instaright. If you are using Instapaper then it is addon for you.',
                ' Firefox addon http://bit.ly/instaright  will enhance Instapaper experience - instead of going to link and then save it via bookmarklet – you can save it using right click', 
                'If you use Instapaper with Firefox addon http://bit.ly/instaright you’ll get enlighted pretty fast',
                'Instaright will change how you use Instapaper',
                'Instaright, right?',
                ]
DM_POLE='Thanks for following! Can you score Instaright service from 1-10? '
KLOUT_URL="http://api.klout.com/1/users/show.json?key=z9kqxgrwa5te3yuheaevyhxn&users="

class TwitterFollowHandler(webapp.RequestHandler):
        def get(self, empty_name):
                memcache_key = 'users_w_twitter_' + str(datetime.datetime.now().date())
                users = memcache.get(memcache_key)
                if not users:
                        all_users = UserDetails.getAll()
                        users_with_twitter = [ u for u in all_users if u.twitter is not None ] #and ((hasattr(u, 'twitter_request_sent') and u.twitter_request_sent == False) or (not hasattr(u, 'twitter_request_sent')) ]
                        memcache.set(memcache_key, users)
                        users = users_with_twitter
                if not users or len(users) == 0:
                        logging.info('currently, no users on twitter')
                        return
                logging.info('retreived %d users with twitter account' % len(users))
                for u in users:
                        taskqueue.add(url='/util/twitter/follow/'+str(u.key()), queue_name='twit-queue')

        def post(self, user_account_key):
                api = twitter.Api(
                                consumer_key='WZ9re48FXCmnaNlN4rbuhg',
                                consumer_secret='jEQ7gDsE2aR9AXrA6aMZHBvKvvFgurjXoSiYLiyjQ', 
                                access_token_key='193034839-oI43CpQA6Mf1JC2no0mKwGxgT7wyWdDL6HpSKlMz', 
                                access_token_secret='q2CP7JR8wNrMNbqgRs9YezZtdMtZO7OgcgTRjCSY'
                                ) 
                #print user.screen_name
                key = db.Key(user_account_key)
                user = UserDetails.gql('WHERE __key__ = :1' , key).get()
                if user is None:
                        logging.info('no user with key %s' % user_account_key)
                        return 
                if not user.twitter or user.twitter_request_sent:
                        logging.info('user %s has not twitter account' % user.instapaper_account)
                        return
                screen_name = str(user.twitter).replace('http://twitter.com/', '')
                screen_name='bojanbabic'
                logging.info('sending request to twitter user %s ' % screen_name)
                try:
                        api.CreateFriendship(screen_name)
                        logging.info('request send succesfully to user %s' %screen_name)
                except:
                        logging.info('error sending twiter request %s, trying to resend request.' % screen_name)
                        try:
                                api.DestroyFriendship(screen_name)
                                api.CreateFriendship(screen_name)
                                logging.info('request send succesfully to user %s' %screen_name)
                        except:
                                logging.info('error resending twiter request %s' % screen_name)
                user.twitter_request_sent = True
                user.put()

class TweetHotLinks(webapp.RequestHandler):
        def __init__(self):
                config=ConfigParser.ConfigParser()
                config.read(os.path.split(os.path.append(__file__)[0]+'/../properties/general.ini'))
                self.skip_domains=config.get('twit','skip_domain')
        def get(self):
                 not_shared=False
                 hotLinks = Links.gql('WHERE shared = :1 ORDER by date_added desc, overall_score desc', not_shared).fetch(30)
                 for h in hotLinks:
                        if h.domain is None:
                                h.domain=StatsUtil.getDomain(h.url)
                                h.put()

                        if h.domain in self.skip_domains:
                                logging.info('filering out %s' %h.url)
                                h.delete()
                                continue
                        t=Twit()
                        t.style=True
                        t.textFromHotLink(h)
                        taskqueue.add(url='/util/twitter/twit/task', queue_name='twit-queue', params={'twit':t.text})
                        h.shared=True
                        h.put()

class TweetHotLinksTask(webapp.RequestHandler):
        def __init__(self):
               config=ConfigParser.ConfigParser()
               config.read(os.path.split(os.path.append(__file__)[0]+'/../properties/general.ini'))
               self.access_token_key=config.get('twit','access_token_key')
               self.access_token_secret=config.get('twit','access_token_secret')
        def post(self):
               twit=self.request.get('twit', None)
               if twit is None or twit == 'None' or 'story: None' in twit:
                        logging.info('no twit skipping')
			return
	       logging.info('twitting new story: %s' % twit)
               api = twitter.Api(
                                consumer_key='WZ9re48FXCmnaNlN4rbuhg',
                                consumer_secret='jEQ7gDsE2aR9AXrA6aMZHBvKvvFgurjXoSiYLiyjQ', 
                                access_token_key=self.access_token_key,
                                access_token_secret=self.access_token_secret
                                ) 
               try:
                        api.PostUpdate(twit)
                        logging.info('twit: %s' % twit)
               except:
                        logging.info('tweeting error %s' % sys.exc_info()[0])
                

class TwitterReplyHandler(webapp.RequestHandler):
        def get(self, twitter_id):
                url = 'http://search.twitter.com/search.json?q=instapaper'
                response = urlfetch.fetch(url)
                if response.status_code != 200:
                        logging.info('error while fetching twitter content')
                        self.response.out.write("can't fetch content from twitter %s" %response.status_code)
                        return
                t_json= simplejson.loads(response.content)
                twitts=self.loadTwitts(t_json)
                texts = '<br>'.join([ '<a href="http://twitter.com/'+t.sender+'">@'+t.sender+'</a>:::'+t.text for t in twitts ])
                url = 'http://search.twitter.com/search.json?q=firefox+tabs'
                feed = urllib2.urlopen(url)
                t_json = simplejson.load(feed)
                twitts=self.loadTwitts(t_json)
                texts_1 = '<br>'.join([ '<a href="http://twitter.com/'+t.sender+'">@'+t.sender+'</a>:::'+t.text for t in twitts ])
                self.response.out.write(texts)
                self.response.out.write(texts_1)
        def loadTwitts(self, t_json):
                twitts = []
                for t in t_json["results"]:
                        tweet_id = t['id']
                        text = t['text']
                        sender = t['from_user']
                        twit = Twit(tweet_id, text, sender)
                        if twit.filter():
                                twitts.append(twit)

                return twitts

class TwitterResetSendHandler(webapp.RequestHandler):
        def get(self):
                tweetsSent = UserDetails.gql('WHERE twitter_request_sent = True').fetch(1000)
                if len(tweetsSent) == 0 or tweetsSent is None:
                        logging.info('no user tweeter request has been sent. exiting ')
                        return
                logging.info('requests send %d' %len(tweetsSent))
                for t in tweetsSent:
                        t.twitter_request_sent = False
                        t.put()
                logging.info('Done')

class Twit:
        exclude_elements=['instapaper.com', 'marcoarment', 'via Instapaper', 'App Updates'] 
        def __init__(self, tweet_id=None, text=None, sender=None, style=False):
                self.tweet_id = tweet_id
                self.text = text
                self.sender = sender
                self.style=style
        #TODO take smarter approach
        # ie spam filter or machine learninig
        def filter(self):
                for e in self.exclude_elements:
                        if e.lower() in self.text.lower():
                                return False
                return True
        def textFromHotLink(self, link, link_title=None):
                if self.style:
                        logging.info('picking new style')
                        return self.textNewStyle(link, link_title)
                else:
                        logging.info('picking old style')
                        return self.textOldStyle(link)
        def textOldStyle(self,link):
                linkUtil=LinkUtil()
                short_link = linkUtil.shortenLink(link.url)
		if short_link is None:
			self.text=None
			return
                self.text = "check out this story: %s " %short_link
                if link.facebook_like is not None and link.facebook_like > 5:
                                self.text+=" #facebooklikes %s" %link.facebook_like
                if link.redditups is not None and link.redditups > 5:#reddit ups %s #delicious save %s #instapaper %s #twitter %s
                                self.text+=" #reddit ups %s" % link.redditups
                if link.delicious_count is not None and link.delicious_count > 5:
                                self.text+=" #delicious saves %s" % link.delicious_count
                if link.instapaper_count is not None and link.instapaper_count > 5:
                                self.text+=" #instaright %s" %link.instapaper_count
                if link.tweets is not None and link.tweets > 5:
                                self.text+=" #twitter %s #RTs" %link.tweets
                top_category=None
                if link.categories is not None and len(link.categories) > 0:
                                logging.info('init cat : %s' % str(link.categories))
                                #dicti = ast.literal_eval(link.categories)
                                dicti = eval(link.categories)
                                if len(dicti) > 0:
                                        import operator
                                        logging.info('categories:'+str(dicti))
                                        sorteddict = sorted(dicti.iteritems(), key=operator.itemgetter(1))
                                        top_category = sorteddict[len(sorteddict)-1]
                if len(self.text) <= 140:
                                if top_category is not None and top_category[0] not in self.text and len(top_category[0]) + len(self.text) +2 <= 140:
                                        self.text +=" #%s" % unicode(top_category[0])
                                if link.diggs is not None and link.diggs > 4 and 8 + len(self.text) +2 <= 140:
                                        self.text +=" #digg %s" % link.diggs
                logging.info('self.text: %s' % self.text)
        def textNewStyle(self,link, title_from_url=None):
                linkUtil=LinkUtil()
                short_link = linkUtil.shortenLink(link.url)
                logging.info('new style title %s' %title_from_url)

                if (not link.title or link.title is None) and title_from_url is None:
                        logging.info('title not known going back to old style')
                        return self.textOldStyle(link)
                if link.categories is not None and len(link.categories) > 0:
                        logging.info('init cat : %s' % str(link.categories))
                        #dicti = ast.literal_eval(link.categories)
                        dicti = eval(link.categories)
                        if len(dicti) == 0:
				if title_from_url is not None and len(title_from_url) > 10:
                        		logging.info('trying from title to get twit text')
					self.text = unicode(title_from_url[0:80]) + " .... " + short_link + " #recommended"
				else:
                               		logging.info('no cat. generating old style')
                               		self.textOldStyle(link)
                        else:
                               import operator
			       # remove some categories
			       if 'via:packrati.us' in dicti:
			       		del dicti['via:packrati.us']
                               logging.info('categories:'+str(dicti))
                               sorteddict = sorted(dicti.iteritems(), key=operator.itemgetter(1), reverse=True)
                               top_category = None
                               top_category1 = None
                               top_category2 = None
                               try:
                                        top_category = sorteddict[0]
                                        top_category1 = sorteddict[1]
                                        top_category2 = sorteddict[2]
                                        logging.info('top cats %s' % sorteddict)
                               except:
                                        logging.info('can\'t get all cats from %s' % sorteddict)
			       if short_link is None:
					self.text=None
					return
                               self.text=""+unicode(link.title[0:59]) + "... " +short_link
                               if top_category is not None and top_category[0] not in self.text and len(top_category[0]) + len(self.text) +2 <= 140:
                                        logging.info("appending cat1 to tweet %s ( %s )" % (unicode(top_category[0]) , top_category))
                                        self.text += " #%s" % unicode(top_category[0])
                               if top_category1 is not None and top_category1[0] not in self.text and len(top_category1[0]) + len(self.text) +2 <= 140:
                                        logging.info("appending cat2 to tweet %s ( %s )" % (unicode(top_category1[0]) , top_category1))
                                        self.text += " #%s" % unicode(top_category1[0])
                               if top_category2 is not None and top_category2[0] not in self.text and len(top_category2[0]) + len(self.text) +2 <= 140:
                                        logging.info("appending cat3 to tweet %s ( %s )" % (unicode(top_category2[0]) , top_category2))
                                        self.text += " #%s" % unicode(top_category2[0])
                else:
			if title_from_url is not None and len(title_from_url) > 20:
                        	logging.info('trying from title to get twit text')
                                short_link = linkUtil.shortenLink(link.url)
				if short_link is None:
					self.text = None
				else:
					self.text = unicode(title_from_url[0:80]) + " .... " + short_link + " #recommended"
			else:
                        	logging.info('no categories going back to old style')
                        	self.textOldStyle(link)
                logging.info('self text %s' % self.text)
                        


application = webapp.WSGIApplication(
                                        [
                                                ('/util/twitter/follow/(.*)', TwitterFollowHandler),
                                                ('/util/twitter/reply/(.*)', TwitterReplyHandler), 
                                                #('/util/twitter/twit', TweetHotLinks), 
                                                ('/util/twitter/twit/task', TweetHotLinksTask), 
                                                ('/util/twitter/reset_sent', TwitterResetSendHandler),
                                                ], debug=True
                                    )
def main():
        run_wsgi_app(application)

if __name__ == "__main__":
        main()

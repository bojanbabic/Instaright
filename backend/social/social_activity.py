# -*- coding: utf-8 -*-
import datetime, os, simplejson, sys, urllib2, logging, urllib

from google.appengine.ext import webapp
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.api.labs import taskqueue
from google.appengine.ext.webapp.util import run_wsgi_app

from models import UserDetails
sys.path.append('social')
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
                        users_with_python = [ u for u in all_users if u.twitter is not None ] #and ((hasattr(u, 'twitter_request_sent') and u.twitter_request_sent == False) or (not hasattr(u, 'twitter_request_sent')) ]
                        memcache.set(memcache_key, users)
                        users = users_with_python
                if not users or len(users) == 0:
                        logging.info('currently, no users on twitter')
                        return
                logging.info('retreived %d users with twitter account' % len(users))
                for u in users:
                        taskqueue.add(url='/util/twitter/follow/'+str(u.key()), queue_name='twitter-follow')

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
                if not user:
                        logging.info('no user with name %s' % user.instapaper_account)
                        return 
                if not user.twitter:
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


class TwitterReplyHandler(webapp.RequestHandler):
        def get(self, twitter_id):
                url = 'http://search.twitter.com/search.json?q=instapaper'
                feed = urllib2.urlopen(url)
                t_json = simplejson.load(feed)
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
                for t in t_json['results']:
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
        def __init__(self, tweet_id=None, text=None, sender=None):
                self.tweet_id = tweet_id
                self.text = text
                self.sender = sender
        #TODO take smarter approach
        # ie spam filter or machine learninig
        def filter(self):
                for e in self.exclude_elements:
                        if e.lower() in self.text.lower():
                                return False
                return True


application = webapp.WSGIApplication(
                                        [
                                                ('/util/twitter/follow/(.*)', TwitterFollowHandler),
                                                ('/util/twitter/reply/(.*)', TwitterReplyHandler), 
                                                ('/util/twitter/reset_sent', TwitterResetSendHandler),
                                                ], debug=True
                                    )
def main():
        run_wsgi_app(application)

if __name__ == "__main__":
        main()

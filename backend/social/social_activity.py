# -*- coding: utf-8 -*-
import datetime
import os
import sys
import logging
import ConfigParser

from google.appengine.ext import webapp
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.api.labs import taskqueue
from google.appengine.ext.webapp.util import run_wsgi_app

from models import UserDetails

sys.path.append(os.path.join(os.path.dirname(__file__),'/../lib'))
import twitter

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

class TweetHotLinksTask(webapp.RequestHandler):
        def __init__(self):
               config=ConfigParser.ConfigParser()
               config.read(os.path.split(os.path.realpath(__file__))[0]+'/../properties/general.ini')
               self.instaright_consumer_key=config.get('twit','instaright_consumer_key')
               self.instaright_consumer_secret=config.get('twit','instaright_consumer_secret')
               self.access_token_key=config.get('twit','access_token_key')
               self.access_token_secret=config.get('twit','access_token_secret')
        def post(self):
               twit=self.request.get('twit', None)
               if twit is None or twit == 'None' or 'story: None' in twit:
                        logging.info('no twit skipping')
			return
	       logging.info('twitting new story: %s' % twit)
               api = twitter.Api(
                                consumer_key=self.instaright_consumer_key,
                                consumer_secret=self.instaright_consumer_secret,
                                access_token_key=self.access_token_key,
                                access_token_secret=self.access_token_secret
                                ) 
               try:
                        api.PostUpdate(twit)
                        logging.info('twit: %s' % twit)
               except:
                        logging.info('tweeting error %s' % sys.exc_info()[0])
                

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

application = webapp.WSGIApplication(
                                        [
                                                ('/util/twitter/follow/(.*)', TwitterFollowHandler),
                                                ('/util/twitter/twit/task', TweetHotLinksTask), 
                                                ('/util/twitter/reset_sent', TwitterResetSendHandler),
                                                ], debug=True
                                    )
def main():
        run_wsgi_app(application)

if __name__ == "__main__":
        main()

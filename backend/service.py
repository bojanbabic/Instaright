import urllib
import logging
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

from models import UserTokens, SessionModel
from service_util import ServiceUtil
from utils.social import Twit,FBMessage

class ServicePromoSubmitHandler(webapp.RequestHandler):
        def post(self, service):
                user_token=self.request.get('user_token', None)
                user_secret=self.request.get('user_secret', None)
                service_util = ServiceUtil()
                if service == 'twitter':
                        logging.info('sending promo twit')
                        if user_token is None or user_secret is None:
                                logging.info('aborting tweet since to credentials from user provided')
                                return
                        service_util.send_tweet_promo(Twit.promo_message(), user_token, user_secret)
                if service == 'facebook':
                        service_util.send_to_facebook(user_token, session=None, promo=True)

class ServiceSubmitHandler(webapp.RequestHandler):
        def post(self):
                user_details_key=self.request.get('user_details_key', None)
                if user_details_key is None:
                        logging.info('user details key not defined ... skipping services submit')
                        return
                session_key=self.request.get('session_key', None)
                if session_key is None:
                        logging.info('session key not defined ... skipping services submit')
                        return
		session=SessionModel.gql('WHERE __key__ = :1', db.Key(session_key)).get()
		user_token = UserTokens.gql('WHERE user_details = :1', db.Key(user_details_key)).get()
                if user_token is None:
                        logging.info('skipping service submit no tokens found')
                        return
		service_util = ServiceUtil()
		evernote_token = user_token.evernote_token
                evernote_token_additional_info = user_token.evernote_additional_info
                evernote_enabled = user_token.evernote_enabled

		flickr_token = user_token.flickr_token
                flickr_token_additional_info = user_token.flickr_additional_info
                flickr_enabled = user_token.flickr_enabled

		facebook_token = user_token.facebook_token
                facebook_enabled = user_token.facebook_enabled

		twitter_token = user_token.twitter_token
		twitter_secret = user_token.twitter_secret
                twitter_enabled = user_token.twitter_enabled

		picplz_token = user_token.picplz_token
                picplz_enabled = user_token.picplz_enabled

                if evernote_token is not None and evernote_enabled == True and session.selection is not None and session.selection != 'None':
			service_util.send_to_evernote(urllib.unquote(evernote_token), session, evernote_token_additional_info)
		if picplz_token is not None and session.isImage():
			service_util.send_to_picplz(picplz_token, session)
		#if facebook_token is not None and facebook_enabled == True:
		#	service_util.send_to_facebook(facebook_token, session)
		#if twitter_token is not None and twitter_enabled == True and session.instaright_account == 'gbabun@gmail.com':
		#	service_util.send_to_twitter(twitter_token, twitter_secret, session)

app = webapp.WSGIApplication([
                                ('/service/submit/(.*)/promo', ServicePromoSubmitHandler),
                                ('/service/submit', ServiceSubmitHandler),
                                        ], debug = True)
def main():
        run_wsgi_app(app)

if __name__ == "__main__":
        main()


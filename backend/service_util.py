import os
import logging
import sys
import ConfigParser
import urllib

from utils.link import LinkUtils
from utils.social import Twit, FBMessage

from xml.sax.saxutils import escape
sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
import thrift.protocol.TBinaryProtocol as TBinaryProtocol
import thrift.transport.THttpClient as THttpClient
import evernote.edam.userstore.UserStore as UserStore
import evernote.edam.userstore.constants as UserStoreConstants
import evernote.edam.notestore.NoteStore as NoteStore
import evernote.edam.type.ttypes as Types
import evernote.edam.error.ttypes as Errors

import twitter
import facebook
import urllib2
from picplz.api import PicplzAPI

from google.appengine.api import mail
from google.appengine.api import urlfetch

sys.path.append(os.path.join(os.path.dirname(__file__),'/lib'))
from StringIO import StringIO
import uuid



class ServiceUtil(object):
        def __init__(self):
                config=ConfigParser.ConfigParser()
                logging.info('reading props from %s' % os.path.split(os.path.realpath(__file__))[0]+'/properties/general.ini')
                config.read(os.path.split(os.path.realpath(__file__))[0]+'/properties/general.ini')
                self.flickr_key=config.get('flickr', 'key')
                self.flickr_secret=config.get('flickr', 'secret')

                self.evernoteHost="www.evernote.com"
                self.noteStoreUriBase = "https://" + self.evernoteHost + "/edam/note/"
                self.userStoreUri = "https://" + self.evernoteHost + "/edam/user"
                self.twitter_consumer_key=config.get('twit','consumer_key')
                self.twitter_consumer_secret=config.get('twit','consumer_secret')
                self.twitter_access_token_secret=config.get('twit','access_token_secret')
        def send_to_picplz(self, picplz_token, session):
                #try:
                        api = PicplzAPI()
                        response=api.upload_pic_url(picplz_token, session.url)
                        logging.info('picplz api response %s' %response)
                #except:
                #        logging.error('Error while sending to picplz: %s => %s ' % (sys.exc_info()[0],sys.exc_info()[1]))
	def send_to_evernote(self, evernote_token, session, additionalInfo=None):
                if additionalInfo is None:
                        logging.info('not additional info for token %s trying alternative view to get shared id' % evernote_token)
                        additional_dict=dict(i.split('=') for i in evernote_token.split(':'))
                        edam_shardId = additional_dict["S"]
                else:
                        additional_dict=dict(i.split('=') for i in additionalInfo.split('&'))
                        edam_shardId = additional_dict["edam_shard"]

                userStoreHttpClient = THttpClient.THttpClient(self.userStoreUri)
                userStoreProtocol = TBinaryProtocol.TBinaryProtocol(userStoreHttpClient)
                userStore = UserStore.Client(userStoreProtocol)

                try:
                        user= userStore.getUser(evernote_token)
                        logging.info('token owned by %s' %user)
                except Errors.EDAMUserException:
                        logging.info('out dated token ... sending user indformation');
                        mail.send_mail(sender='gbabun@gmail.com', to=session.instaright_account, subject='Instaright evernote authentication has expired!', html='We applogize for inconvenience.<br>Inorder to renew authentication for another year please visit: <a href="http://www.instaright.com/user/dashboard">user dashboard</a>.<br><br>Sincerly, <br>Your Instaright Team<br>', body='We applogize for inconvenience.<br>Inorder to renew authentication for another year please visit: <a href="http://www.instaright.com/user/dashboard">user dashboard</a>.<br><br>Sincerly, <br>Your Instaright Team<br>')
                        return

                noteStoreUri =  self.noteStoreUriBase + edam_shardId
                noteStoreHttpClient = THttpClient.THttpClient(noteStoreUri)
                noteStoreProtocol = TBinaryProtocol.TBinaryProtocol(noteStoreHttpClient)
                noteStore = NoteStore.Client(noteStoreProtocol)

                note = Types.Note()
                if session.title is None:
                        note.title = "{Instaright-Evernote article}" 
                else:
                        note.title = "{Instaright-Evernote update - %s}" % session.title.encode('utf-8')
                note.content = '<?xml version="1.0" encoding="UTF-8"?>'
                note.content += '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
                if session.selection is not None or session.selection != 'None':
                        note.content += '<en-note>'+escape(session.selection)+'<br/><br/>from url:<b>'+escape(session.url)+'</b><br/></en-note>'
                else:
                        note.content += '<en-note>%s<br/>' % escape(session.url)
                        note.content += '</en-note>'
                note.content = note.content.encode('utf-8')
                note.title = 'Sample'
                logging.info('note content:%s ' % note.content)

                createdNote = noteStore.createNote(evernote_token, note)
                logging.info(' create note with GUID %s' % createdNote.guid)

	def send_to_facebook(self, facebook_token, session, promo=False):
                message=FBMessage.generateText(session,promo)
                if message is None:
                        logging.info('skipping sending fb message - not defined ')
                        return
                logging.info('sending  fb message: %s' % (message))
                message=message.encode('utf-8')
                try:
                        api= facebook.GraphAPI(facebook_token)
                        api.put_wall_post(message)
                except: 
                        logging.error('Error while sending fbmessage %s: %s => %s ' % (message, sys.exc_info()[0],sys.exc_info()[1]))

		return
	def send_to_twitter(self, twitter_token, twitter_secret, session):
               api = twitter.Api(
                                consumer_key=self.twitter_consumer_key,
                                consumer_secret=self.twitter_consumer_secret,
                                access_token_key=twitter_token,
                                access_token_secret=twitter_secret
                                ) 
               twit = Twit()
               lu=LinkUtils()
               link = lu.getAllData(session.url)
               if link.overall_score == 0:
                       logging.debug('skipping to send twitt since content is not popular %s ' % session.url)
                       return
               twit.generate_content(link, session.title, "via:@instaright")
               logging.info('twit: %s' % twit.text)
               if twit.text is None:
                       logging.info('twit has no text ... skipping')
                       return
               try:
                   api.PostUpdate(twit.text)
               except:
                   logging.error('Error while sending tweet %s: %s => %s ' % (twit.text, sys.exc_info()[0],sys.exc_info()[1]))
        def send_tweet_promo(self, tweet, twitter_token, twitter_secret):
               api = twitter.Api(
                                consumer_key=self.twitter_consumer_key,
                                consumer_secret=self.twitter_consumer_secret,
                                access_token_key=twitter_token,
                                access_token_secret=twitter_secret
               )
               try:
		       logging.info('sending promo tweet %s' % tweet)
                       api.PostUpdate(tweet)
               except:
                       logging.error('Error while sending promo tweet:%s ( %s => %s )' % (tweet, sys.exc_info()[0],sys.exc_info()[1]))


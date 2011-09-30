import os
import logging
import urllib
import urllib2
import sys
import ConfigParser

from xml.sax.saxutils import escape
sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
import simplejson
import thrift.protocol.TBinaryProtocol as TBinaryProtocol
import thrift.transport.THttpClient as THttpClient
import evernote.edam.userstore.UserStore as UserStore
import evernote.edam.userstore.constants as UserStoreConstants
import evernote.edam.notestore.NoteStore as NoteStore
import evernote.edam.type.ttypes as Types
import evernote.edam.error.ttypes as Errors

import flickrapi
import twitter

from google.appengine.api import mail


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
        def send_to_flickr(self, flickr_token, session, additionalInfo=None):
                try:
                        logging.info('flickr token %s' % flickr_token)
                        flickr = flickrapi.FlickrAPI(self.flickr_key, self.flickr_secret, token=flickr_token)
			rsp=flickr.auth_checkToken(auth_token=flickr_token, format='xmlnode')
			logging.info('response %s' % rsp)
			logging.info('permissions %s' % rsp.auth[0].perms[0].text)
                        flickr.upload(filename=session.url, title="%s via Instaright" % session.title)
                except:
		        e0,e = sys.exc_info()[0], sys.exc_info()[1]
                        logging.error('error while uploading img to flickr: %s => %s' %( e0, e))
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
                note.title = "{Instaright-Evernote update - %s}" % session.title
                note.content = '<?xml version="1.0" encoding="UTF-8"?>'
                note.content += '<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
                if session.selection is not None or session.selection != 'None':
                        note.content += '<en-note>'+escape(session.selection)+'<br/><br/>from url:<b>'+escape(session.url)+'</b><br/></en-note>'
                else:
                        note.content += '<en-note>%s<br/>' % escape(session.url)
                        note.content += '</en-note>'
                #note.content = unicode(note.content)
                logging.info('note content:%s' % note.content)

                createdNote = noteStore.createNote(evernote_token, note)
                logging.info(' create note with GUID %s' % createdNote.guid)


	def send_to_facebook(self, facebook_token, session):
		return
	def send_to_twitter(self, twitter_token, twitter_secret, session):
               logging.info('sending to twitter :user token %s and secret %s ' % (twitter_token , twitter_secret))
               logging.info('client:consumer key %s and consumer secret %s ' % (self.twitter_consumer_key, self.twitter_consumer_secret))
               api = twitter.Api(
                                consumer_key=self.twitter_consumer_key,
                                consumer_secret=self.twitter_consumer_secret,
                                access_token_key=twitter_token,
                                access_token_secret=twitter_secret
                                ) 
               #TODO totally deprecated use some-utils after refactoring utils 
               url = 'http://links.instaright.com/a947824b599193b3/?web=058421&dst='+session.url;
               link='http://api.bit.ly/v3/shorten?longUrl='+urllib.quote(unicode(url))+'&login=bojanbabic&apiKey=R_62dc6488dc4125632884f32b84e7572b&hash=in&format=json'  
               data=urllib2.urlopen(link)
               json=simplejson.load(data)
               short_url = json["data"]["url"]
               twit = 'Just market awesome article %s via:instaright' % short_url
               api.PostUpdate(twit)
               logging.info('twit: %s' % twit)

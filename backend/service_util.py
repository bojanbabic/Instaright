import os
import logging
import sys
from xml.sax.saxutils import escape
sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
import thrift.protocol.TBinaryProtocol as TBinaryProtocol
import thrift.transport.THttpClient as THttpClient
import evernote.edam.userstore.UserStore as UserStore
import evernote.edam.userstore.constants as UserStoreConstants
import evernote.edam.notestore.NoteStore as NoteStore
import evernote.edam.type.ttypes as Types
import evernote.edam.error.ttypes as Errors

import flickrapi
from google.appengine.api import mail
import ConfigParser

config=ConfigParser.ConfigParser()
config.read(os.path.split(os.path.realpath(__file__))[0]+'/properties/general.ini')
flickr_key=config.get('flickr', 'key')
flickr_secret=config.get('flickr', 'secret')

evernoteHost="www.evernote.com"
noteStoreUriBase = "https://" + evernoteHost + "/edam/note/"
userStoreUri = "https://" + evernoteHost + "/edam/user"

class ServiceUtil(object):
        def send_to_flickr(self, flickr_token, session, additionalInfo=None):
                try:
                        logging.info('flickr token %s' % flickr_token)
                        flickr = flickrapi.FlickrAPI(flickr_key, flickr_secret, token=flickr_token)
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

                userStoreHttpClient = THttpClient.THttpClient(userStoreUri)
                userStoreProtocol = TBinaryProtocol.TBinaryProtocol(userStoreHttpClient)
                userStore = UserStore.Client(userStoreProtocol)

                try:
                        user= userStore.getUser(evernote_token)
                        logging.info('token owned by %s' %user)
                except Errors.EDAMUserException:
                        logging.info('out dated token ... sending user indformation');
                        mail.send_mail(sender='gbabun@gmail.com', to=session.instaright_account, subject='Instaright evernote authentication has expired!', html='We applogize for inconvenience.<br>Inorder to renew authentication for another year please visit: <a href="http://www.instaright.com/user/dashboard">user dashboard</a>.<br><br>Sincerly, <br>Your Instaright Team<br>', body='We applogize for inconvenience.<br>Inorder to renew authentication for another year please visit: <a href="http://www.instaright.com/user/dashboard">user dashboard</a>.<br><br>Sincerly, <br>Your Instaright Team<br>')
                        return

                noteStoreUri =  noteStoreUriBase + edam_shardId
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
	def send_to_twitter(self, twitter_token, session):
		return

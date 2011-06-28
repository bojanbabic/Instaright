import os, ConfigParser, urllib2, urllib, unittest, logging, time, threading, sys
from google.appengine.api import urlfetch, memcache
from users import UserUtil

class BadgesTest(unittest.TestCase):

        def test_movie_badge(self):
                config = ConfigParser.ConfigParser()
                config.read(os.path.split(os.path.realpath(__file__))[0]+'/../properties/badges/movie/movie.properties')
                movie_tresshold=int(config.get('movie', 'tresshold'))
                
                user='gbabun@gmail.com'
                memcache_key='badge_'+user
                #clear memcache
                memcache.delete(memcache_key)
                while movie_tresshold > 0:
                        movie_tresshold -= 1
                        badge_thread=threading.Thread(target=BadgesTest.send_request)
                        badge_thread.start()
                        
                memcache_thread=threading.Thread(target=BadgesTest.get_badge)
                memcache_thread.start()

        @classmethod
        def get_badge(cls):
                time.sleep(15)
                user='gbabun@gmail.com'
                badge_key='badge_'+user
                current_badge=memcache.get(badge_key)
                self.assertEquals('movie', current_badge)

        @classmethod
        def send_request(cls):
                try:
                                data={'user':'gbabun@gmail.com','url':'http://youtube.com', 'domain':'youtube.com','title':'Test movie title','version':'0.4.0.4'}
                                data = urllib.urlencode(data)
                                req=urllib2.Request('http://localhost:8080/user/badge/task', data)
                                urllib2.urlopen(req)
                except:
	        		e, e0 = sys.exc_info()[0], sys.exc_info()[1]
	        		logging.error('stats error: %s ; %s' %(e, e))
                                logging.info('no response it is ok ' )



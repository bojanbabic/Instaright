import logging, ConfigParser, urlparse, os
from google.appengine.ext import webapp

class GenericWebHandler(webapp.RequestHandler):
        def get_redirect(self, url):
             config=ConfigParser.ConfigParser()
             config.read(os.path.split(os.path.realpath(__file__))[0]+'/properties/webapp.ini')
             redirects=eval(config.get('redirect','urls'))
             logging.info('request from url %s' % url)
             scheme, netloc, path, query, fragment = urlparse.urlsplit(url)
             netloc = netloc.split(':',1)[0]
             logging.info('request netloc %s' % netloc)

             if path == '':
                     path='/'
             if netloc in redirects:
                     redirect_info=redirects[netloc]
                     if not redirect_info[1]:
                             return 'http://' + redirect_info[0] + '/'
                     else:
                             return urlparse.urlunsplit(['http', redirect_info[0], path, query, fragment])
             else:
                     logging.info('path %s not in redirect list' % url)
                     return None

        def redirect_perm(self):
                redirect_url = self.get_redirect(self.request.url)
                if redirect_url is not None:
                        logging.info('redirecting 301:%s ==> %s' %(self.request.url, redirect_url)) 
                        self.redirect(redirect_url, permanent=True)
                else:
                        logging.info('url %s will not be redirected' % self.request.url)

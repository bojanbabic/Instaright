import logging
import urllib
import sys
import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template

from models import SessionModel
from generic_handler import GenericWebHandler
from main import UserMessager

from utils.link import LinkUtils
from utils.user import UserUtils
from utils.page import PageUtils

sys.path.append(os.path.join(os.path.dirname(__file__), 'lib'))
import simplejson

class DomainHandler(GenericWebHandler):
        def get(self,domain):
                crawler = self.request.get('_escaped_fragment_', None)
                if crawler is not None:
                        self.html_snapshot(domain,'domain')
                        return
                logging.info('domain handler ')
                self.redirect_perm()
                self.get_user()
                logging.info('domain screen_name %s' %self.screen_name)
                if self.avatar is None:
                        self.avatar='/static/images/noavatar.png'

		userMessager = UserMessager(str(self.user_uuid))
		channel_id = userMessager.create_channel()

		template_variables = []
                template_variables = {'page_footer': PageUtils.get_footer(), 'user':self.screen_name, 'logout_url':'/account/logout', 'avatar':self.avatar,'channel_id':channel_id,'domain':domain}
		path= os.path.join(os.path.dirname(__file__), 'templates/domain.html')
                self.response.headers["Content-Type"] = "text/html; charset=utf-8"
		self.response.out.write(template.render(path,template_variables))

class DomainFeedHandler(webapp.RequestHandler):
        def get(self, domain):
                format=self.request.get('format',None)
                if domain is None or len(domain) == 0:
                        logging.info('not category in request. return empty')
                        return
                if format == 'json':
                        logging.info('domain %s json feed' % domain)
                        userUtil = UserUtils()
                        entries = SessionModel.gql('WHERE domain = :1 order by date desc', domain).fetch(10)
			self.response.headers['Content-Type'] = "application/json"
			#TODO insert categories for domain's view
                        self.response.out.write(simplejson.dumps(entries, default=lambda o: {'u':{'id':str(o.key()), 't':unicode(o.title), 'l': LinkUtils.generate_instaright_link(o.url_encode26, LinkUtils.make_title(o.title), o.url), 'user': urllib.unquote(o.instaright_account), 'source': o.client, 'html_lc':LinkUtils.getLinkCategoryHTML(o), 'd': o.domain, 'lc': LinkUtils.getLinkCategory(o), 'dd':LinkUtils.generate_domain_link(o.domain), 'u': o.date.strftime("%Y-%m-%dT%I:%M:%SZ"), 'a':userUtil.getAvatar(o.instaright_account),'ol':o.url}}))
			return
                self.response.headers['Content-Type'] = "application/json"
                self.response.out.write("[{}]")

def main():
        run_wsgi_app(application)

application=webapp.WSGIApplication(
                [
                        ('/domain/(.*)/feed',DomainFeedHandler),
                        ('/domain/(.*)',DomainHandler),
                        ],debug=True
                )

if __name__ == "__main__":
        main()

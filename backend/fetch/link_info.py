import sys
import urllib2
import os
import logging
import time

import ConfigParser

from utils.general import Cast
from utils.task import TaskUtil
from utils.link import LinkUtils
from utils.handler import RequestUtils
from utils.user import UserUtils
from utils.social import Twit

from models import Links
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api.labs import taskqueue
from google.appengine.api import datastore_errors
from google.appengine.ext.db import BadValueError
from google.appengine.runtime import apiproxy_errors
from google.appengine.api import mail

sys.path.append(os.path.join(os.path.dirname(__file__),'lib'))
import simplejson

class LinkHandler(webapp.RequestHandler):
	def __init__(self):
		config=ConfigParser.ConfigParser()
		config.read(os.path.split(os.path.realpath(__file__))[0]+'/../properties/general.ini')
		try:
			self.fb_factor=int(config.get('social', 'fb_factor'))
			self.tw_factor=int(config.get('social', 'tw_factor'))
			self.tw_margin=int(config.get('social', 'tw_margin'))
		except:
			logging.error('properties propblem on path %s' % os.path.join(os.path.dirname(__file__),'properties/general.ini'))

        def post(self):
                count = self.request.get('count',None)
                url = self.request.get('url',None)
                url = urllib2.unquote(url)
                domain = RequestUtils.getDomain(url)
                if not domain or len(domain) == 0:
                        self.response.out.write('not url: %s skipping!\n' %url)
                        return
                logging.info('url %s' % url)
                logging.info('count %s' % count)
                lu = LinkUtils()
                link = lu.getAllData(url, count)
		self.update_link(url, link)
                self.response.out.write('put %s \n ' %url)

	def update_link(self, url, link):
		existingLink=None
                url_hash = LinkUtils.getUrlHash(url)
                link.url_hash = url_hash
                #qfix for title TODO: find proper solution
                if link.title is not None:
                        link.title=link.title.strip()[:199]
		try:
                	existingLink = Links.gql('WHERE url_hash  = :1', url_hash).get()
                        if existingLink is None:
                	        existingLink = Links.gql('WHERE url = :1', url).get()
		except:
			logging.info('bad value for url %s' % url)
                if existingLink is not None:
                        existingLink.date_updated= link.date_updated
                        existingLink.influence_score= link.influence_score
                        existingLink.instapaper_count= link.instapaper_count
                        existingLink.instaright_count=link.instaright_count
                        existingLink.redditups=link.redditups
                        existingLink.redditdowns=link.redditdowns
                        existingLink.tweets=link.tweets
                        existingLink.diggs=link.diggs
                        existingLink.excerpt=link.excerpt
                        existingLink.categories=link.categories
                        existingLink.delicious_count=link.delicious_count
                        existingLink.facebook_like=link.facebook_like
			existingLink.domain = link.domain
                        if existingLink.url_hash is None:
                                existingLink.url_hash = url_hash
                        if link.title is not None:
                                existingLink.title = link.title.strip()[:199]
                        #if increase in score is more then 20%
                        if  existingLink.overall_score is None or existingLink.overall_score == 0 or link.overall_score  / existingLink.overall_score >= 1.2:
                                existingLink.shared=False
                        existingLink.overall_score=link.overall_score
                        existingLink.put()
                else:
			#greater probability for db timeout of new links
			try:
				while True:
					timeout_ms = 100
					try:
                        			link.put()
						break
					except datastore_errors.Timeout:
						time.sleep(timeout_ms)
						timeout_ms *= 2
			except apiproxy_errors.DeadlineExceededError:
				logging.info('run out of retries for writing to db')
                logging.info('url %s : influence_score %s, instapaper_count %s, redditups %s, redditdowns %s, tweets %s, diggs %s, delicious count %s facebook like %s' %(url, link.influence_score , link.instapaper_count, link.redditups, link.redditdowns, link.tweets, link.diggs, link.delicious_count, link.facebook_like))

        def get(self):
                self.response.out.write('get')

        #TODO see if this is still used
	def delicious_data(self, url):
                delicious_api='http://feeds.delicious.com/v2/json/urlinfo/data?url=%s&type=json' % url
                logging.info('trying to fetch delicious info %s ' % delicious_api)
                json =LinkUtils.getJsonFromApi(delicious_api)
		link=Links()
                if json:
                        try:
                                if not link.title:
                                        link.title = json[0]['title'].strip()
                                link.categories = db.Text(unicode(simplejson.dumps(json[0]['top_tags'])))
                                if link.categories is not None:
                                        taskqueue.add(queue_name='category-queue', url='/link/category/delicious', params={'url':url, 'categories':link.categories})
                                link.delicious_count = Cast.toInt(json[0]['total_posts'],0)
				logging.info('delicious count %s' % link.delicious_count)
                        except KeyError:
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('key error [[%s, %s]] in %s' %(e0, e1, json))
		return link

        def getData(self, url):
                try:
                        dta = urllib2.urlopen(url)
                        json = simplejson.load(dta)
                        return json
                except:
                        logging.info('error while getting link %s reTRYing'  % url)
                	try:
                        	dta = urllib2.urlopen(url)
                        	json = simplejson.load(dta)
                        	return json
                	except:
                        	e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                        	logging.info('error %s %s, while getting link %s'  %( e0, e1, url))
                        	return None

class LinkTractionTask(webapp.RequestHandler):
	def __init__(self):
		config=ConfigParser.ConfigParser()
		config.read(os.path.split(os.path.realpath(__file__))[0]+'/../properties/general.ini')
		self.tw_margin=int(config.get('social', 'tw_margin'))
		self.tw_factor=int(config.get('social', 'tw_factor'))
		self.klout_correction=int(config.get('social', 'klout_correction'))
		self.klout_api_key=config.get('social', 'klout_api_key')
                self.skip_domains=config.get('twit','skip_domain')
	def post(self):

                url = self.request.get('url',None)
                url_hash = LinkUtils.getUrlHash(url)
		user = self.request.get('user', None)
		title = self.request.get('title', None)

		if url is None:
			logging.info('no url detected. skipping...')
			return
                count = 1
                url = urllib2.unquote(url)
                domain = RequestUtils.getDomain(url)
                if not domain or len(domain) == 0:
                        self.response.out.write('not url: %s skipping!\n' %url)
                        return
                if domain in self.skip_domains:
                                logging.info('filering out %s' %url)
                                return
                lu = LinkUtils()
                link = lu.getAllData(url, count)
		logging.info('link overall score: %s' % link.overall_score)
		existingLink = None
		try:
	                existingLink = Links.gql('WHERE url_hash = :1', url_hash).get()
                        if existingLink is None:
	                        existingLink = Links.gql('WHERE url = :1', url).get()
		except BadValueError:
			logging.info('bad value url %s' % url)
		klout_score = UserUtils.getKloutScore(user, self.klout_api_key)
		share_margin = self.tw_margin
		if klout_score is not None:
			link.overall_score = link.overall_score * int(klout_score)
			logging.info('adjusted overall score %s' % link.overall_score)
			share_margin = share_margin * self.klout_correction
			logging.info('adjusting twit margin: %s' % share_margin)
                
		logging.info('link score %s tweet margin %s ( existing %s )' %( link.overall_score, share_margin, existingLink))
		if link.overall_score > share_margin and (existingLink is None or not existingLink.shared):
                        t=Twit()
                        t.generate_content(link, title, '')
                        #skip tweets is text emtpy and for root domains
			if t.text is None or LinkUtils.isRootDomain(link.url):
				logging.info('twit with no body. aborting')
				return
			execute_time=TaskUtil.execution_time()
			logging.info('scheduling tweet for %s' %str(execute_time))
                        mail.send_mail(sender='gbabun@gmail.com', to='bojan@instaright.com', subject='Twit to queue!', html='Twitt: %s <br> score: %s' %( t.text, link.overall_score), body='Twitt: %s <br> score: %s' %(t.text[:500], link.overall_score))
			
                        #taskqueue.add(url='/util/twitter/twit/task', eta=execute_time, queue_name='twit-queue', params={'twit':t.text})
                        taskqueue.add(url='/util/twitter/twit/task', queue_name='twit-queue', params={'twit':t.text})
                        #update article shared status
                        if existingLink is not None:
                                existingLink.shared= True
                                existingLink.put()
                        logging.info('updated link share status')
                else:
                        logging.info('not scheduled for tweeting')
                lh = LinkHandler()
		lh.update_link(url, link)

application = webapp.WSGIApplication(
                                        [
                                                ('/link/add', LinkHandler),
                        			('/link/traction/task',LinkTractionTask),
                                                ],
                                        debug=True)
def main():
        run_wsgi_app(application)


if __name__ == "__main__":
        main()

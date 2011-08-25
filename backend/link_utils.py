import re
import logging
from google.appengine.api import memcache
from models import LinkCategory
from google.appengine.ext.db import NotSavedError

#DO NOT TOUCH!!!!
chars='abcdefghijklmnopqrstuvwxyz'
mapping=range(28)
mapping.reverse()
class EncodeUtils(object):
	def encode(self, n):
		result=0
		for i,b in enumerate(mapping):
			b1 = 1 << i
			b2 = 1 << mapping[i]
			if b1 & n:
				result |= b2
		return result
	def decode(self, n):
		result = 0
		for i,c in enumerate(mapping):
			b1 = 1 << i
			b2 = 1 << mapping[i]
			if n & b2:
				result |= b1
		return result
	def enbase(self, x):
		n = len(chars)
		if x < n:
			return chars[x]
		return self.enbase(x/n) + chars[x%n]
	def debase(self, x):
		n = len(chars)
		result = 0
		for i, c in enumerate(reversed(x)):
			result += chars.index(c) * (n**i)
		return result
			
class LinkUtils(object):
        @classmethod
        def generate_domain_link(cls, domain):
                return "http://www.instaright.com/domain/%s" % domain
        @classmethod
        def generate_instaright_link(cls, url_hash, generated_title, default=None):
                if url_hash is None or generated_title is None:
                        return default
                return "http://www.instaright.com/article/"+url_hash+"/"+generated_title
        @classmethod
        def make_title(cls, title):
                #TODO solve chinese/japan chars ie iemcps
                title = re.sub(r'\W+', '-', unicode(title))
                return title
        @classmethod
        def getLinkCategory(cls, link_model):
                category=''
                logging.info('looking category cache for url hash %s ( %s )' %(link_model.url_hash, link_model.url))
                if link_model is None or link_model.url_hash is None:
                        return category
                mem_key = link_model.url_hash+'_category'
                cached_category=memcache.get(mem_key)
                if cached_category is not None:
                        logging.info('got category from cache %s' %cached_category)
                        return ','.join(cached_category)
                linkCategory=None
                try:
                        linkCategory=LinkCategory.gql('WHERE category != NULL and url_hash = :1 ' , link_model.url_hash).fetch(1000)
                except NotSavedError:
                        logging.info('not saved key for url hash %s' % link_model.url_hash)
                if linkCategory is not None:
                        logging.info('got %s categories for %s' %( len(linkCategory), link_model.url))
                        cats_tag=[ l.category  for l in linkCategory if l.category is not None and len(l.category) > 2 ]
                        category=list(set(cats_tag))
                        logging.info('got category from query %s' %category)
                        memcache.set(mem_key, category)
                return ','.join(category)

        @classmethod
        def getLinkCategoryHTML(cls, link_model):
                category=None
                logging.info('looking category cache for url hash %s ( %s )' %(link_model.url_hash, link_model.url))
                if link_model is None or link_model.url_hash is None:
                        return category
                mem_key = link_model.url_hash+'_category'
                cached_category=memcache.get(mem_key)
                if cached_category is not None:
                        logging.info('got category from cache %s' %cached_category)
                        category=cached_category
                linkCategory=None
                try:
                        linkCategory=LinkCategory.gql('WHERE category != NULL and url_hash = :1 ' , link_model.url_hash).fetch(1000)
                except NotSavedError:
                        logging.info('not saved key for url hash %s' % link_model.url_hash)
                if linkCategory is not None and category is None:
                        logging.info('got %s categories for %s' %( len(linkCategory), link_model.url))
                        cats_tag=[ l.category  for l in linkCategory if l.category is not None and len(l.category) > 2 ]
                        category=list(set(cats_tag))
                        logging.info('got category from query %s' %category)
                        memcache.set(mem_key, category)
                #NOTE: static css , error
                html = [ "<span class=\"text_bubble_cats\"><a href=\"/category/"+c+"\">"+c+"</a></span>" for c in category ]
                return " ".join(html)


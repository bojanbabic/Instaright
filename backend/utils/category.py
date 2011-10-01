import logging
import datetime

from models import CategoryDomains, LinkCategory
class CategoryUtil(object):
        @classmethod
        def processDomainCategories(cls, categories, domain):
                if categories is None or len(categories) == 0:
                        logging.info('missing categories. skipping')
                        return
		cat_dict = eval(categories)
		if len(cat_dict) == 0:
			logging.info('no categories. skipping')
			return
		for cat, cnt in cat_dict.iteritems():
			catDomains=CategoryDomains.gql('WHERE category = :1' , cat).get()
			if catDomains is None:
				logging.info('new category %s , init domain %s' % (cat, domain))
				catDomains = CategoryDomains()
				catDomains.category = cat
				catDomains.domains = domain
				catDomains.put()
			else:
				domainsArray = catDomains.domains.split(',')
				if domain in domainsArray:
					logging.info('category %s already contains domain %s' % ( cat, domain))
				else:
					if domainsArray is None:
						domainsArray = []
					domainsArray.append(domain)
					catDomains.domains = ','.join(domainsArray)
                                        logging.info('updated category %s [ %s ]' % (cat, catDomains.domains))
					catDomains.put()
        @classmethod
        def processLinkCategoriesFromJson(cls, categories, url):
                if categories is None or len(categories) == 0:
                        logging.info('missing categories. skipping')
                        return
		cat_dict = eval(categories)
		if len(cat_dict) == 0:
			logging.info('no categories. skipping') 
			return 
		for cat, cnt in cat_dict.iteritems():
                        existingCategory=LinkCategory.gql('WHERE category = :1 and url = :2' , cat, url).get()
			if existingCategory is None:
				logging.info('new category %s , init url %s' % (cat, url))
				linkCategory = LinkCategory()
				linkCategory.category = cat
				linkCategory.url = url
				linkCategory.put()
			else:
                                logging.info('updated time for category %s [ %s ]' % (cat, existingCategory.url))
                                existingCategory.updated = datetime.datetime.now()
				existingCategory.put()

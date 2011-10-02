import logging
from utils.link import LinkUtils
from utils.category import CategoryUtil

class Twit(object):
        def generate_content(self, link, link_title, prepend=None):
                return self.textNewStyle(link, link_title, prepend)
        def textOldStyle(self,link, prepend_text=''):
                lu=LinkUtils()
                short_link = lu.shortenLink(link.url)
		if short_link is None:
			self.text=None
			return
                self.text = "check out this story: %s " %short_link
                if link.facebook_like is not None and link.facebook_like > 5:
                                self.text+=" #facebooklikes %s" %link.facebook_like
                if link.redditups is not None and link.redditups > 5:#reddit ups %s #delicious save %s #instapaper %s #twitter %s
                                self.text+=" #reddit ups %s" % link.redditups
                if link.delicious_count is not None and link.delicious_count > 5:
                                self.text+=" #delicious saves %s" % link.delicious_count
                if link.instapaper_count is not None and link.instapaper_count > 5:
                                self.text+=" #instaright %s" %link.instapaper_count
                if link.tweets is not None and link.tweets > 5:
                                self.text+=" #twitter %s #RTs" %link.tweets
                top_category=None
                if link.categories is not None and len(link.categories) > 0:
                                logging.info('init cat : %s' % str(link.categories))
                                #dicti = ast.literal_eval(link.categories)
                                dicti = eval(link.categories)
                                if len(dicti) > 0:
                                        import operator
                                        logging.info('categories:'+str(dicti))
                                        sorteddict = sorted(dicti.iteritems(), key=operator.itemgetter(1))
                                        top_category = sorteddict[len(sorteddict)-1]
                if len(self.text) <= 140 - 1 - len(prepend_text):
                                if top_category is not None and top_category[0] not in self.text and len(top_category[0]) + len(self.text) +2 <= 140:
                                        self.text +=" #%s" % unicode(top_category[0])
                                if link.diggs is not None and link.diggs > 4 and 8 + len(self.text) +2 <= 140:
                                        self.text +=" #digg %s" % link.diggs
                self.text += " " + prepend_text
                logging.info('self.text: %s' % self.text)
        def textNewStyle(self,link, title_from_url, prepend_text=None):
                lu=LinkUtils()
                short_link = lu.shortenLink(link.url)
                if short_link is None:
                        logging.info('something is wrong with bitly link from %s ... ' % link.url)
                        self.text=None
                        return
                logging.info('new style title %s' %title_from_url)

                if (link.title is None and title_from_url is None) or (title_from_url is not None and len(title_from_url) < 15):
                        logging.info('title not known going back to old style')
                        return self.textOldStyle(link,prepend_text)
                categories = CategoryUtil.getTwitCategories(link.categories)
                self.text =  Twit.generateTwitText(categories, title_from_url, short_link, prepend_text)

        @classmethod
        def generateTwitText(cls, cats, title, short_link, prepend_text=''):
                title_substr_index=80
                cats_len = 0
                for c in cats:
                        cats_len+= len(c) + 2
                #cats_len=sum(lambda x: len(x) + 2, cats)
                # 5 = len(' ... ')
                if cats_len + len(short_link) + 5 + len(prepend_text) > 60:
                        title_substr_index = 57
                title=title.encode('utf-8')
                ttext=title[0:title_substr_index] +  unicode(' ... ' + short_link ).encode('utf-8')
                cat_count = 4 
                if len(cats) < cat_count:
                        cat_count = len(cats) 
                i = 0
                while(len(ttext) < 140 - len(prepend_text) and i < cat_count):
                        ttext += unicode(" #"+cats[i].decode('utf-8')).encode('utf-8')
                        i = i + 1
                return ttext + unicode(" "+prepend_text.decode('utf-8')).encode('utf-8')
        @classmethod
        def promo_tweet(cls):
                return "Just discovered #instaright #app http://bit.ly/instarightapp - helps you #read #save #discover online content :) via:@instaright"

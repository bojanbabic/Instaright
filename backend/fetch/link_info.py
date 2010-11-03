import sys, urllib2, simplejson, exceptions, os, logging
#TODO create class for all APIes used
#class GenericApi:
#        def __init__:

#class TopsyApi:
#        def getInfo(self):
#print os.environ['INSTAPAPER']
sys.path.append('..')
from utils_min import StatsUtil,Cast
from models import Links
from google.appengine.ext import webapp
from google.appengine.ext import db
from google.appengine.ext.webapp.util import run_wsgi_app
                
class LinkHandler(webapp.RequestHandler):
        def post(self):
                count = self.request.get('count',None)
                url = self.request.get('url',None)
                url = urllib2.unquote(url)
                domain = StatsUtil.getDomain(url)
                if not domain or len(domain) == 0:
                        self.response.out.write('not url: %s skipping!\n' %url)
                        return
                logging.info('url %s' % url)
                logging.info('count %s' % count)
                link = self.getAllData(url, count)
                link.put()
                self.response.out.write('put %s\n' % url)
        def get(self):
                self.response.out.write('get')

        def getAllData(self,url, count):
                topsy_api='http://otter.topsy.com/stats.json?url='+url
                tweet_meme_api='http://api.tweetmeme.com/url_info.json?url='+url
                delicious_api='http://feeds.delicious.com/v2/json/urlinfo/data?url='+url+'&type=json'
                digg_api='http://services.digg.com/1.0/endpoint?method=story.getAll&link='+url+'&type=json'
                reddit_api='http://www.reddit.com/api/info.json?url='+url
                link = Links()
                link.instapaper_count = Cast.toInt(count,0)
                link.url = url
                link.redditups = 0
                link.redditdowns = 0
                link.tweets = 0
                link.diggs = 0
                link.delicious_count = 0

                json = self.getData(topsy_api)
                if json:
                        try:
                                link.influence_score=Cast.toInt(json['response']['influential'],0)
                                link.all_score=Cast.toInt(json['response']['all'],0)
                        except KeyError:
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('key error [[%s, %s]] in %s' %(e0, e1, json))

                json =self.getData(digg_api)
                if json:
                        try:
                                link.diggs =Cast.toInt(json['count'],0)
                        except KeyError:
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('key error [[%s, %s]] in %s' %(e0, e1, json))
                logging.info(json)

                json = self.getData(tweet_meme_api)
                if json and 'story' in json:
                        try:
                                link.tweets=Cast.toInt(json['story']['url_count'],0)
                                link.title=json['story']['title']
                                link.excerpt = db.Text(unicode(json['story']['excerpt']))
                        except KeyError:
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('key error [[%s, %s]] in %s' %(e0, e1, json))

                json =self.getData(delicious_api)
                if json:
                        try:
                                if not link.title:
                                        link.title = json[0]['title']
                                link.categories = db.Text(unicode(simplejson.dumps(json[0]['top_tags'])))
                                link.delicious_count = Cast.toInt(json[0]['total_posts'],0)
                        except KeyError:
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('key error [[%s, %s]] in %s' %(e0, e1, json))

                json = self.getData(reddit_api)
                if json and 'data' in json:
                        try:
                                data = [ x for x in json['data']['children']]
                                top_upped = sorted(data, key=lambda ups: ups['data']['ups'], reverse=True)
                                if top_upped:
                                     link.redditups = Cast.toInt(top_upped[0]['data']['ups'],0)
                                     link.redditdowns = Cast.toInt(top_upped[0]['data']['downs'],0)
                                     link.created = Cast.toInt(top_upped[0]['data']['created'],0)
                        except KeyError:
                                e0, e1 = sys.exc_info()[0],sys.exc_info()[1]
                                logging.info('key error [[%s, %s]] in %s' %(e0, e1, json))

                link.overall_score = link.diggs + link.delicious_count + link.tweets + link.instapaper_count + link.redditups - link.redditdowns
                return link

        def getData(self, url):
                try:
                        dta = urllib2.urlopen(url)
                        json = simplejson.load(dta)
                        return json
                except:
                        sys.stderr.write('error getting link: %s' %url)
                        return None

application = webapp.WSGIApplication(
                                        [
                                                ('/link/add', LinkHandler),
                                                ],
                                        debug=True)
def main():
        run_wsgi_app(application)


if __name__ == "__main__":
        main()

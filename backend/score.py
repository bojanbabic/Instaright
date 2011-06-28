from utils import UserScoreUtility
from google.appengine.api import webapp
from google.appengine.api import memcache
from google.appengine.ext import db

class ScoreUpdateTaskHandler(webapp.RequestHandler):
        def post(self):
                user=self.request.get('user',None)
                if user is None:
                        logging.info('user not defined ... skipping!')
                        return
                ud=UserDetails.gql('WHERE instaright_account = :1' , user).get()
                start_of_week= time.asctime(time.strptime('%s %s 1' %(now.year, now.isocalendar()[1]), '%Y %W %w'))
                score=0
                score_entities = ScoreUsersDaily.gql('WHERE user = :1 and date <= :2 and date >= :3', ud_key, now , start_of_week).fetch(100)
                if scores_entities is not None:
                        scores = [ s.score for s in score_entities if s is not None ]
                        score=sum(scores)

                memcache_key='user_'+user_key+'_score_'+str(start_of_week)
                memcache.set(memcache_key, score)
application = webapp.WSGIApplication(
                [
                        ('/user/score/update/task', ScoreUpdateTaskHandler),
                ],
                debug=True)
def main(self):
        run_wsgi_app(application)

if __name__ == "__main__":
        main()

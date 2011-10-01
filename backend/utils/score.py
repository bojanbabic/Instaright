import logging
import datetime
import os
import ConfigParser
from models import UserDetails, SessionModel, ScoreUsersDaily
from google.appengine.api import memcache
from google.appengine.api.labs import taskqueue

class UserScoreUtility(object):
        @classmethod
        def getCurrentScore(cls, user):
                if user is None:
                        return None
                userDetails = UserDetails.gql('WHERE  instaright_account = :1', user).get()
                if userDetails is None:
                        logging.info('no user with instaright account %s' % user)
                        userDetails = UserDetails.gql('WHERE  instapaper_account = :1', user).get()
                        if userDetails is None:
                                userDetails=UserDetails()
                                userDetails.instapaper_account=user
                        userDetails.instaright_account=user
                        userDetails.put()
                now =datetime.datetime.now().date()
                currentScore=ScoreUsersDaily.gql('WHERE user = :1 and date = :2', userDetails.key(), now).get()
                if currentScore is None:
                        currentScore = ScoreUsersDaily()
                        currentScore.user=userDetails.key()
                        currentScore.date = now
                return currentScore
                
        @classmethod
        def badgeScore(cls, user, badge):
                score=0
                if user is None or badge is None:
                        logging.info('no user no score or no badge no score')
                        return score
                if badge in ['1000','5000','10000']:
                        logging.info(' %s badge not uncluded into score')
                        return score
                logging.info('badge score calc for user %s' %user)
                badge_cache='score_for_badge_'+user+'_'+badge+'_'+str(datetime.datetime.now().date())
                badge_added=memcache.get(badge_cache)
                if badge_added:
                        logging.info('badge already included in scoring. skipping')
                        return score
                #TODO what is this doing here
                #currentScore=UserScoreUtility.getCurrentScore(user)
                config=ConfigParser.ConfigParser()
	        config.read(os.path.split(os.path.realpath(__file__))[0]+'/../properties/score.ini')
                score=int(config.get('badge_point',badge))
                return score

        @classmethod
        def domainScore(cls,user, domain):
                score=0
                if user is None or domain is None:
                                     logging.info('domain score not enpugh data ... skipping')
                                     return score
                logging.info('domain score calc for for user %s' %user)
                config=ConfigParser.ConfigParser()
	        config.read(os.path.split(os.path.realpath(__file__))[0]+'/../properties/score.ini')
                domain_points=int(config.get('domain_points','new_domain'))
                domain_memcache_key='visit_'+user+'_domain_'+domain
                visitedDomain=memcache.get(domain_memcache_key)
                if visitedDomain is None:
                        visitedDomain=SessionModel.gql('WHERE domain = :1 and instaright_account = :2', domain, user).get()
                if visitedDomain is None:
                        logging.info('new domain %s score for %s ' %(domain, user))
                        score=domain_points
                        memcache.set(domain_memcache_key, '1')
                else:
                        logging.info('user %s already visited domain %s ' %(user, domain))
                return score

        @classmethod
        def linkScore(cls,user, link):
                score=0
                if user is None or link is None:
                                     logging.info('link score not enpugh data ... skipping')
                                     return score
                logging.info('link score ...')
                config=ConfigParser.ConfigParser()
	        config.read(os.path.split(os.path.realpath(__file__))[0]+'/../properties/score.ini')
                link_points=int(config.get('link_points','new_link'))
                link_memcache_key='visit_'+user+'_domain_'+link
                visitedLink=memcache.get(link_memcache_key)
                if visitedLink is None:
                        try:
                                visitedLink=SessionModel.gql('WHERE url = :1 and instaright_account = :2', link, user).get()
                        except:
                                logging.info('expection fetching %s' % link)
                if visitedLink is None:
                        logging.info('new link %s score for %s ' %(link, user))
                        score=link_points
                        memcache.set(link_memcache_key, '1')
                else:
                        logging.info('user %s already visited link %s ' %(user, link))
                return score
        @classmethod
        def updateLinkScore(cls,user,link):
                if user is None:
                        logging.info('no user no link score')
                        return
                currentScore=UserScoreUtility.getCurrentScore(user)
                linkPoints=UserScoreUtility.linkScore(user, link)
                logging.info('update score user %s score %s for link %s' %(user, linkPoints, link))
                currentScore.score+=linkPoints
                currentScore.put()
                taskqueue.add(url='/user/score/update/task', queue_name='score-queue', params={'user':user})

        @classmethod
        def updateDomainScore(cls,user,domain):
                if user is None:
                        logging.info('no user no domain score')
                        return
                currentScore=UserScoreUtility.getCurrentScore(user)
                domainPoints=UserScoreUtility.domainScore(user, domain)
                logging.info('update score user %s score %s for domain %s' %(user, domainPoints, domain))
                currentScore.score+=domainPoints
                currentScore.put()
                taskqueue.add(url='/user/score/update/task', queue_name='score-queue', params={'user':user})

        @classmethod
        def updateBadgeScore(cls,user,badge):
                if user is None:
                        logging.info('no user no badge score')
                        return
                currentScore=UserScoreUtility.getCurrentScore(user)
                badgePoints=UserScoreUtility.badgeScore(user, badge)
                logging.info('update score user %s score %s for badge %s' %(user, badgePoints, badge))
                currentScore.score+=badgePoints
                currentScore.put()
                taskqueue.add(url='/user/score/update/task', queue_name='score-queue', params={'user':user})

        @classmethod
        def updateScore(cls, user, domain, link, badge):
                if user is None:
                        logging.info('no user no score')
                        return
                        
                currentScore=UserScoreUtility.getCurrentScore(user)
                linkPoints=UserScoreUtility.linkScore(user, link)
                domainPoints=UserScoreUtility.domainScore(user,domain)
                badgePoints=UserScoreUtility.badgeScore(user, badge)
                currentScore.score+=linkPoints + domainPoints + badgePoints
                currentScore.put()
                #overAllScore=UserScoreUtility.getOverAllScore(user)
                #overAllScore.score += currentScore.score
                #overAllScore.put()

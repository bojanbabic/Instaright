from google.appengine.ext import webapp, db
from google.appengine.ext.webapp.util import run_wsgi_app

from models import Links

class LinkSortHandler(webapp.RequestHandler):
        def get(self):
                order = self.request.get('order',None)
                l = Links()
                self.response.headers["Content-Type"]='text/plain'
                if order and hasattr(l,order): 
                        if order == 'diggs':
                                links = Links.gql('ORDER by diggs desc' ).fetch(100)
                        elif order == 'redditups':
                                links = Links.gql('ORDER by redditups desc' ).fetch(100)
                        elif order == 'all_score':
                                links = Links.gql('ORDER by all_score desc' ).fetch(100)
                        elif order == 'influence_score':
                                links = Links.gql('ORDER by influence_score desc' ).fetch(100)
                        elif order == 'instapaper_count':
                                links = Links.gql('ORDER by instapaper_count desc' ).fetch(100)
                        elif order == 'instaright_count':
                                links = Links.gql('ORDER by instaright_count desc' ).fetch(100)
                        elif order == 'overall_score':
                                links = Links.gql('ORDER by overall_score desc' ).fetch(100)
                        elif order == 'redditdowns':
                                links = Links.gql('ORDER by redditdowns desc' ).fetch(100)
                        elif order == 'tweets':
                                links = Links.gql('ORDER by tweets desc' ).fetch(100)
                        elif order == 'delicious_count':
                                links = Links.gql('ORDER by delicious_count desc' ).fetch(100)
                        else:
                                links = Links.gql('ORDER by overall_score desc').fetch(100)
                        urls = [ l.url+ '\t' + str(getattr(l,order)) for l in links ]
                        self.response.out.write('\n'.join(urls))
                        return
                self.response.out.write('bad request')

def main():
        run_wsgi_app(application)

application=webapp.WSGIApplication(
                [
                        ('/link/stats',LinkSortHandler),
                        ],debug=True
                )

if __name__ == "__main__":
        main()

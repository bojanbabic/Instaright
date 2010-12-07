from google.appengine.ext import db

from models import SessionModel

ss = SessionModel.gql('order by short_url desc').fetch(5000)
print len(ss)
for s in ss:
    print s.short_url
    print s.url
    print s.domain

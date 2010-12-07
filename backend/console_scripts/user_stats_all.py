from google.appengine.ext import db
from models import UserStats
ss = UserStats.all()
print ss.count()
for s in ss:
    print s.date
    print s.count

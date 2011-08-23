from google.appengine.api import memcache
from google.appengine.ext import db
import random

class GeneralCounterShardConfig(db.Model):
        """Tracks the number of shards for each named counter."""
        counter_name = db.StringProperty(required=True)
        num_shards = db.IntegerProperty(required=True, default=20)


class GeneralCounterShardNew(db.Model):
        counter_name = db.StringProperty()
        count = db.IntegerProperty(default=0)


def get_count(name):
        total = memcache.get(name)
        if total is None:
         total = 0
        for counter in GeneralCounterShardNew.all().filter('counter_name = ', name):
         total += counter.count
        return total


def increment(name):
       config = GeneralCounterShardConfig.get_or_insert(name, counter_name=name)
       def txn():
        index = random.randint(0, config.num_shards - 1)
        shard_name = name + str(index)
        counter = GeneralCounterShardNew.get_by_key_name(shard_name)
        if counter is None:
                counter = GeneralCounterShardNew(key_name=shard_name, counter_name=name)
        counter.count += 1
        counter.put()
       db.run_in_transaction(txn)
       # does nothing if the key does not exist

def increase_shards(name, num):
        config = GeneralCounterShardConfig.get_or_insert(name, counter_name=name)
        def txn():
                if config.num_shards < num:
                        config.num_shards = num
                        config.put()
        db.run_in_transaction(txn)


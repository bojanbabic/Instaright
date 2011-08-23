import unittest
import logging
import random
from link_utils import  EncodeUtils
from generic_counter import GeneralCounterShardNew
import generic_counter

class CounterTest(unittest.TestCase):
	def test_incr(self):
                name='url'
                generic_counter.increment(name)
                url_counter_id = generic_counter.get_count(name) 
                non_none = True
                if url_counter_id is None:
                        non_none = False
                self.assertEquals(True, non_none)
                e = EncodeUtils()
                url_encode26 = e.encode(url_counter_id) 
		logging.info('counter %s encoded %s' %( url_counter_id, url_encode26))
        def _test_plain(self):
                index = random.randint(0,19)
                counter=GeneralCounterShard()
                counter.counter_name = "test" + str(index)
                #counter=GeneralCounterShard(counter_name="test", key_name="test"+str(index))
                counter.count = index
                counter.put()
                logging.info("counter %s" % counter.to_xml())
		

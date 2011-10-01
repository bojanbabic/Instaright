import unittest
import logging
from utils.link import  EncodeUtils 
from models import SessionModel

class EncodeTest(unittest.TestCase):
	def test_encode(self):
                e = EncodeUtils()
		encoded = e.encode(1)
		self.assertEquals(encoded, 134217728)
		encoded = e.encode(2)
		self.assertEquals(encoded, 67108864)
		encoded = e.encode(3)
		self.assertEquals(encoded, 201326592)
		encoded = e.encode(4)
		self.assertEquals(encoded, 33554432)
		encoded = e.encode(55)
		self.assertEquals(encoded, 33554432)
        def test_enbase(self): 
                e = EncodeUtils()
                enbased = e.enbase(134217728)
                self.assertEquals(enbased, 'lhskyi')
        def test_debase(self):
                e = EncodeUtils()
                debased = e.debase('lhskyi')
                self.assertEquals(debased,134217728) 
                debased = e.debase('fqwfme')
		self.assertEquals(debased, 67108864)
                debased = e.debase('qyoqkm')
		self.assertEquals(debased, 201326592)
                debased = e.debase('cvlctc')
		self.assertEquals(debased, 33554432)
        def test_decode(self): 
                e = EncodeUtils()
                decoded = e.decode(134217728)
                self.assertEquals(decoded, 1)
        def test_update_encode(self):
                e = EncodeUtils()
                ss = SessionModel.gql('ORDER by url_counter_id desc').fetch(1000)
                test = SessionModel.countAllForUser('gbabun@gmail.com')
                logging.info('count for user  %s' % test)
                logging.info("fetch %s " %len(ss))
                for s in ss:
                        cnt = s.url_counter_id
                        encode26 = e.enbase(cnt)
                        logging.info("e26: before %s after %s" % (s.url_encode26, encode26))
                        s.url_encode26 = encode26
                        #s.put()
		self.assertEquals(True, True)

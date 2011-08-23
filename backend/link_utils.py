import re
chars='abcdefghijklmnopqrstuvwxyz'
mapping=range(28)
mapping.reverse()
class EncodeUtils(object):
	def encode(self, n):
		result=0
		for i,b in enumerate(mapping):
			b1 = 1 << i
			b2 = 1 << mapping[i]
			if b1 & n:
				result |= b2
		return result
	def decode(self, n):
		result = 0
		for i,c in enumerate(mapping):
			b1 = 1 << i
			b2 = 1 << mapping[i]
			if n & b2:
				result |= b1
		return result
	def enbase(self, x):
		n = len(chars)
		if x < n:
			return chars[x]
		return self.enbase(x/n) + chars[x%n]
	def debase(self, x):
		n = len(chars)
		result = 0
		for i, c in enumerate(reversed(x)):
			result += chars.index(c) * (n**i)
		return result
			
class LinkUtils(object):
        @classmethod
        def generate_domain_link(cls, domain):
                return "http://www.instaright.com/domain/%s" % domain
        @classmethod
        def generate_instaright_link(cls, url_hash, generated_title, default=None):
                if url_hash is None or generated_title is None:
                        return default
                return "http://www.instaright.com/article/"+url_hash+"/"+generated_title
        @classmethod
        def make_title(cls, title):
                #TODO solve chinese/japan chars ie iemcps
                title = re.sub(r'\W+', '-', unicode(title))
                return title

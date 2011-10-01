#!/usr/bin/python 
import sys
from utils.handler import RequestUtils

class StatsAnalyzer:
	def __init__(self):
		self.map={}

	def analyze_stats(self):
		file = sys.argv[1]
		self.loadInMemory(file)
		self.findRepeatingLinks()
		

	def loadInMemory(self, file):
		handle = open(file)
		for l in handle:
			url, count = l.split("\t")
			domain = RequestUtils.getDomain(url)
			if domain in self.map:
				current_links = self.map[domain]
			else:
				current_links= []
			current_links.append((url.strip(), count.strip()))
			self.map[domain] = current_links
			
	def findRepeatingLinks(self):

		for domain in self.map:
			for l in self.map[domain]:
				if str("http://"+domain ) == l[0] or str("http://" + domain + "/") == l[0] or str("http://www." + domain ) == l[0] or str("http://www." + domain + "/") == l[0]:
					sys.stderr.write("skipping domain %s , home .... %s" %( domain , l[0]))
					continue
				sub_links = [ lk for lk in self.map[domain] if l[0] in lk[0] and l[0] != lk[0] and not("/" in lk[0][len(l[0])+1:]) ]
				if sub_links:
					sys.stderr.write("\ndomain: %s \n" % domain)
					sys.stderr.write("link %s (%s) appears in:" % (l[0], l[1]))
					sys.stderr.write("\n".join([ s[0]+","+s[1] for s in sub_links]))
					sys.stderr.write("\n")
					links = self.map[domain]
					links.remove(l)
					for s in sub_links:
						links.remove(s)
						l = ( l[0], int(l[1]) + int(s[1]))
					sys.stderr.write("transformed into %s , %s" %(l[0], l[1]))
					links.append(l)
					self.map[domain]=links
	def printMap(self):
		for d in self.map:
			for l in self.map[d]:
				print str(l[1])+"\t"+l[0]





def main():
	sa = StatsAnalyzer()
	sa.analyze_stats()
	sa.printMap()

if __name__ == "__main__":
	main()


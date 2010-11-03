#!/usr/bin/python
import sys, simplejson

class SortData:
        def __init__(self, linkData=None):
                self.dict = []
        def sortBy(self, order):
                print order
                top_dict = sorted(self.dict, key=lambda x: x['info'][order])
                for t in top_dict:
                        print t

        def load_dict(self, file_name):
                f = open(file_name)
                ff = simplejson.load(f)
                self.dict= [ l for l in ff ]
                print len(self.dict)
#                for l in f:
#                        self.dict.append(l)

def main():
        file_name, order = sys.argv[1], sys.argv[2]
        sd = SortData()
        sd.load_dict(file_name)
        sd.sortBy(order)

if __name__ == "__main__":
        main()

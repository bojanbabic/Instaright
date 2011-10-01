import logging
import datetime

class TaskUtil(object):
	@classmethod
	def execution_time(cls):
		
		# best time for tweet 1 PM EEST 4 AM EEST 2 AM EEST 2 PM EEST 9 AM PST( 7 PM EEST)
		(year, month, day, hour, min, sec)=datetime.datetime.now().timetuple()[:6]
		logging.info('calculating tweet execution time. now %s' % str(datetime.datetime.now()))
		ss_1=datetime.datetime(year, month, day, 0, 0, 0)
		ss_2=datetime.datetime(year, month, day, 5, 0, 0)
		ss_3=datetime.datetime(year, month, day, 10, 0, 0)
		ss_4=datetime.datetime(year, month, day, 15, 0, 0)
		ss_5=datetime.datetime(year, month, day, 22, 0, 0)
		now=datetime.datetime.now()
		if now < ss_1:
			return ss_1
		if now < ss_2:
			return ss_2
		if now < ss_3:
			return ss_3
		if now < ss_4:
			return ss_4
		if now < ss_5:
			return ss_5
		else:
			return ss_1

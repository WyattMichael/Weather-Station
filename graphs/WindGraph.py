# Windgraph
# A Schatzie Dog Production (c)
#
# Builds Wind Speed and Gust graph
#
#
#

import sys
import time
import RPi.GPIO as GPIO

import gc
import datetime

import matplotlib
# Force matplotlib to not use any Xwindows backend.
matplotlib.use('Agg')

from matplotlib import pyplot
from matplotlib import dates

import pylab

import MySQLdb as mdb

# Check for user imports
try:
        import conflocal as config
except ImportError:
        import config

def  WindGraph(source,days,delay):

	print("WindGraph source:%s days:%s" % (source,days))
	print("sleeping seconds:", delay)
	time.sleep(delay)
	print("WindGraph running now")


        # blink GPIO LED when it's run
        GPIO.setup(18, GPIO.OUT)
        GPIO.output(18, True)
        time.sleep(0.2)
        GPIO.output(18, False)

	# now we have get the data, stuff it in the graph

	try:
		print("trying database")
    		db = mdb.connect('localhost', 'root', config.MySQL_Password, 'WeatherPi');

    		cursor = db.cursor()

		query = "SELECT TimeStamp, currentWindSpeed,  currentWindGust FROM WeatherData where  now() - interval %i hour < TimeStamp" % (days*24)

		print "query=", query
		cursor.execute(query)
		result = cursor.fetchall()

		t = []
		u = []
		v = []

		fig = pyplot.figure()



		for record in result:
  			t.append(record[0])
  			u.append(record[1])
  			v.append(record[2])

                print ("count of t=",len(t))
		if (len(t) == 0):
			return

		#dts = map(datetime.datetime.fromtimestamp, s)
		#fds = dates.date2num(dts) # converted
		# matplotlib date format object
		hfmt = dates.DateFormatter('%m/%d-%H')


		ax = fig.add_subplot(111)
		ax.xaxis.set_major_locator(dates.HourLocator(interval=6))
		ax.xaxis.set_major_formatter(hfmt)
		pylab.xticks(rotation='vertical')

		pyplot.subplots_adjust(bottom=.3)
		pylab.plot(t, u, color='b',label="Wind Speed (MPH)",linestyle="",marker="*")
		pylab.plot(t, v, color='r',label="Wind Gust (MPH)",linestyle="",marker=".")
		pylab.xlabel("Hours")
		pylab.ylabel("MPH")
		pylab.legend(loc='upper left')
		pylab.axis([min(t), max(t), 0, 40])
		pylab.figtext(.5, .05, ("Wind Speed/Gust(MPH)over last %i Days" % days),fontsize=18,ha='center')

		pylab.grid(True)

		pyplot.setp( ax.xaxis.get_majorticklabels(), rotation=70)
		ax.xaxis.set_major_formatter(dates.DateFormatter('%m/%d-%H'))
		pyplot.show()
		pyplot.savefig("/home/pi/SDL_Pi_GroveWeatherPi/static/WindGraph.png")

	except mdb.Error, e:

    		print "Error %d: %s" % (e.args[0],e.args[1])

	finally:

		cursor.close()
        	db.close()

		del cursor
		del db

		fig.clf()
		pyplot.close()
		pylab.close()
		del t, u, v
		gc.collect()
		print("WindGraph finished now")

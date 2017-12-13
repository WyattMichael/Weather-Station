
#
# quick graph test
# SummerGlen GC Weather Station - A Schatzie Dog production(c)

import sys
import RPi.GPIO as GPIO



GPIO.setmode(GPIO.BCM)


import TemperatureHumidityGraph


TemperatureHumidityGraph.TemperatureHumidityGraph('test', 10, 0)

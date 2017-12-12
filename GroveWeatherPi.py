#
#
# SummerGlen WeatherPi - A Shatzie dog approved project
# Version 2.0 - Now with 100% more Grove Goodness
#
#
#
# imports

import sys
import time
from datetime import datetime
import random
import re
import math
import os
import psutil
import commands

import pclogging


sys.path.append('./SDL_Pi_SSD1306')
sys.path.append('./Adafruit_Python_SSD1306')
sys.path.append('./RTC_SDL_DS3231')
sys.path.append('./Adafruit_Python_BMP')
sys.path.append('./Adafruit_Python_GPIO')
sys.path.append('./SDL_Pi_WeatherRack')
sys.path.append('./SDL_Pi_FRAM')
sys.path.append('./RaspberryPi-AS3935/RPi_AS3935')
sys.path.append('./SDL_Pi_INA3221')
sys.path.append('./SDL_Pi_TCA9545')
sys.path.append('./SDL_Pi_SI1145')
sys.path.append('./graphs')
sys.path.append('./SDL_Pi_HDC1000')


import subprocess
import RPi.GPIO as GPIO
import doAllGraphs
import smbus
from twython import Twython
import struct

import SDL_Pi_HDC1000

# Check for user imports
try:
	import conflocal as config
except ImportError:
	import config

import MySQLdb as mdb

################
# Device Present State Variables
###############

#indicate interrupt has happened from as3936

as3935_Interrupt_Happened = False;

import SDL_Pi_INA3221
import SDL_DS3231
import Adafruit_BMP.BMP280 as BMP280
import SDL_Pi_WeatherRack as SDL_Pi_WeatherRack

import SDL_Pi_FRAM
from RPi_AS3935 import RPi_AS3935

import SDL_Pi_TCA9545

import Adafruit_SSD1306

import Scroll_SSD1306

#Import Light Sensor UV, IR, Visible
try:
	import SDL_Pi_SI1145
	import SI1145Lux
except:
	print "Bad SI1145 Installation"

################
# TCA9545 I2C Mux

#/*=========================================================================
#    I2C ADDRESS/BITS
#    -----------------------------------------------------------------------*/
TCA9545_ADDRESS =                         (0x73)    # 1110011 (A0+A1=VDD)
#/*=========================================================================*/

#/*=========================================================================
#    CONFIG REGISTER (R/W)
#    -----------------------------------------------------------------------*/
TCA9545_REG_CONFIG            =          (0x00)
#    /*---------------------------------------------------------------------*/

TCA9545_CONFIG_BUS0  =                (0x01)  # 1 = enable, 0 = disable
TCA9545_CONFIG_BUS1  =                (0x02)  # 1 = enable, 0 = disable
TCA9545_CONFIG_BUS2  =                (0x04)  # 1 = enable, 0 = disable
TCA9545_CONFIG_BUS3  =                (0x08)  # 1 = enable, 0 = disable

#/*=========================================================================*/

# I2C Mux TCA9545 Detection
tca9545 = SDL_Pi_TCA9545.SDL_Pi_TCA9545(addr=TCA9545_ADDRESS, bus_enable = TCA9545_CONFIG_BUS0)
# turn I2CBus 1 on
tca9545.write_control_register(TCA9545_CONFIG_BUS2)

################
# SunAirPlus Sensors
# the three channels of the INA3221 named for SunAirPlus Solar Power Controller channels (www.switchdoc.com)
LIPO_BATTERY_CHANNEL = 1
SOLAR_CELL_CHANNEL   = 2
OUTPUT_CHANNEL       = 3

# switch to BUS2 -  SunAirPlus is on Bus2
tca9545.write_control_register(TCA9545_CONFIG_BUS2)
sunAirPlus = SDL_Pi_INA3221.SDL_Pi_INA3221(addr=0x40)
busvoltage1 = sunAirPlus.getBusVoltage_V(LIPO_BATTERY_CHANNEL)

SUNAIRLED = 25



################
# turn I2CBus 0 on
tca9545.write_control_register(TCA9545_CONFIG_BUS0)

###############
# HTU21DF Detection

HTU21DFOut = subprocess.check_output(["htu21dflib/htu21dflib","-l"])



###############
#WeatherRack Weather Sensors
#
# GPIO Numbering Mode GPIO.BCM
#
anemometerPin = 26
rainPin = 21

# constants

SDL_MODE_INTERNAL_AD = 0
SDL_MODE_I2C_ADS1015 = 1    # internally, the library checks for ADS1115 or ADS1015 if found

#sample mode means return immediately.  THe wind speed is averaged at sampleTime or when you ask, whichever is longer
SDL_MODE_SAMPLE = 0
#Delay mode means to wait for sampleTime and the average after that time.
SDL_MODE_DELAY = 1

# turn I2CBus 0 on
tca9545.write_control_register(TCA9545_CONFIG_BUS0)

weatherStation = SDL_Pi_WeatherRack.SDL_Pi_WeatherRack(anemometerPin, rainPin, 0,0, SDL_MODE_I2C_ADS1015)
weatherStation.setWindMode(SDL_MODE_SAMPLE, 5.0)
#weatherStation.setWindMode(SDL_MODE_DELAY, 5.0)


###############
# Sunlight SI1145 Sensor Setup
################
# turn I2CBus 3 on
tca9545.write_control_register(TCA9545_CONFIG_BUS3)
#
Sunlight_Sensor = SDL_Pi_SI1145.SDL_Pi_SI1145()
visible = Sunlight_Sensor.readVisible()
#print "visible=", visible
vis = Sunlight_Sensor.readVisible()
IR = Sunlight_Sensor.readIR()
UV = Sunlight_Sensor.readUV()
IR_Lux = SI1145Lux.SI1145_IR_to_Lux(IR)
vis_Lux = SI1145Lux.SI1145_VIS_to_Lux(vis)
uvIndex = UV / 100.0


################
# DS3231/AT24C32 Setup
# turn I2CBus 0 on
tca9545.write_control_register(TCA9545_CONFIG_BUS0)

filename = time.strftime("%Y-%m-%d%H:%M:%SRTCTest") + ".txt"
starttime = datetime.now()
ds3231 = SDL_DS3231.SDL_DS3231(1, 0x68)
ds3231.write_now()
ds3231.read_datetime()
#print "DS3231=\t\t%s" % ds3231.read_datetime()
#print "----------------- "
#print "----------------- "
#print " AT24C32 EEPROM"
#print "----------------- "
#print "writing first 4 addresses with random data"
for x in range(0,4):
    value = random.randint(0,255)
    #print "address = %i writing value=%i" % (x, value)
    ds3231.write_AT24C32_byte(x, value)
    #print "----------------- "
    #print "reading first 4 addresses"
    #for x in range(0,4):
        #print "address = %i value = %i" %(x, ds3231.read_AT24C32_byte(x))
        #print "----------------- "

################
# BMP280 Setup

bmp280 = BMP280.BMP280(busnum=1)

################
# OLED SSD_1306 Detection

#    display = Adafruit_SSD1306.SSD1306_128_64(rst=RST, i2c_address=0x3C)
#    # Initialize library.
#    display.begin()
#    display.clear()
#    display.display()


################

# ad3935 Set up Lightning Detector

# switch to BUS1 - lightning detector is on Bus1
tca9545.write_control_register(TCA9545_CONFIG_BUS1)
time.sleep(0.020)
as3935 = RPi_AS3935(address=0x03, bus=1)

as3935.set_indoors(False)
#print "as3935 present"

# back to BUS1
#tca9545.write_control_register(TCA9545_CONFIG_BUS0)

#i2ccommand = "sudo i2cdetect -y 1"
#output = subprocess.check_output (i2ccommand,shell=True, stderr=subprocess.STDOUT )
#print output
as3935.set_noise_floor(0)
as3935.calibrate(tun_cap=0x0F)
as3935LastInterrupt = 0
as3935LightningCount = 0
as3935LastDistance = 0
as3935LastStatus = ""
as3935Interrupt = False

# back to BUS0
tca9545.write_control_register(TCA9545_CONFIG_BUS0)
time.sleep(0.003)

def process_as3935_interrupt():

    global as3935Interrupt
    global as3935, as3935LastInterrupt, as3935LastDistance, as3935LastStatus

    as3935Interrupt = False

    print "processing Interrupt from as3935"
# turn I2CBus 1 on
    tca9545.write_control_register(TCA9545_CONFIG_BUS1)
    time.sleep(0.020)
    reason = as3935.get_interrupt()

    as3935LastInterrupt = reason

    if reason == 0x00:
	    as3935LastStatus = "Spurious Interrupt"
    elif reason == 0x01:
	    as3935LastStatus = "Noise Floor too low. Adjusting"
        as3935.raise_noise_floor()
    elif reason == 0x04:
	    as3935LastStatus = "Disturber detected - masking"
        as3935.set_mask_disturber(True)
    elif reason == 0x08:
        now = datetime.now().strftime('%H:%M:%S - %m/%d/%Y')
        distance = as3935.get_distance()
        as3935LastStatus = "Lightning Detected "  + str(distance) + "km away. (%s)" % now
		tweet = "DANGER!: "+str(as3935LastStatus)
		twitter = Twython(config.consumer_key, config.consumer_secret, config.access_key, config.access_secret)
		twitter.update_status(status=tweet)
		print("Tweeted: {}".format(tweet))
		pclogging.log(pclogging.INFO, __name__, "Lightning Detected "  + str(distance) + "km away. (%s)" % now)
	print "Last Interrupt = 0x%x:  %s" % (as3935LastInterrupt, as3935LastStatus)
    tca9545.write_control_register(TCA9545_CONFIG_BUS0)
    time.sleep(0.003)

def handle_as3935_interrupt(channel):
    global as3935Interrupt
    print "as3935 Interrupt"
    as3935Interrupt = True
# define Interrupt Pin for AS3935
    as3935pin = 13
    GPIO.setup(as3935pin, GPIO.IN)
#GPIO.setup(as3935pin, GPIO.IN,pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(as3935pin, GPIO.RISING, callback=handle_as3935_interrupt)


##############
# Setup AM2315
# turn I2CBus 0 on
tca9545.write_control_register(TCA9545_CONFIG_BUS0)

###############
# Detect AM2315
from tentacle_pi.AM2315 import AM2315
am2315 = AM2315(0x5c,"/dev/i2c-1")
outsideTemperature, outsideHumidity, crc_check = am2315.sense()
#print "outsideTemperature: %0.1f C" % outsideTemperature
#print "outsideHumidity: %0.1f %%" % outsideHumidity
#print "crc: %i" % crc_check


###############
# Set up FRAM
# turn I2CBus 0 on
tca9545.write_control_register(TCA9545_CONFIG_BUS0)
fram = SDL_Pi_FRAM.SDL_Pi_FRAM(addr = 0x50)
# FRAM Detection


# Main Loop - sleeps 10 seconds
# command from RasPiConnect Execution Code

def completeCommand():

    f = open("/home/pi/SDL_Pi_GroveWeatherPi/state/WeatherCommand.txt", "w")
    f.write("DONE")
    f.close()

def completeCommandWithValue(value):

    f = open("/home/pi/SDL_Pi_GroveWeatherPi/state/WeatherCommand.txt", "w")
    f.write(value)
    f.close()

def processCommand():

    f = open("//home/pi/SDL_Pi_GroveWeatherPi/state/WeatherCommand.txt", "r")
    command = f.read()
    f.close()
    if (command == "") or (command == "DONE"):
# Nothing to do
	return False

# Check for our commands
#pclogging.log(pclogging.INFO, __name__, "Command %s Recieved" % command)
    print "Processing Command: ", command
    if (command == "SAMPLEWEATHER"):
	sampleWeather()
	completeCommand()
	writeWeatherStats()
	return True

    if (command == "SAMPLEBOTH"):
	sampleWeather()
	completeCommand()
	writeWeatherStats()
        sampleSunAirPlus()
	writeSunAirPlusStats()
        return True

    if (command == "SAMPLEBOTHGRAPHS"):
	sampleWeather()
	completeCommand()
	writeWeatherStats()
	sampleSunAirPlus()
	writeSunAirPlusStats()
	doAllGraphs.doAllGraphs()
	return True

	completeCommand()

	return False

# Main Program

def returnPercentLeftInBattery(currentVoltage, maxVolt):
    scaledVolts = currentVoltage / maxVolt
    if (scaledVolts > 1.0):
        scaledVolts = 1.0

    if (scaledVolts > .9686):
        returnPercent = 10*(1-(1.0-scaledVolts)/(1.0-.9686))+90
        return returnPercent

    if (scaledVolts > 0.9374):
        returnPercent = 10*(1-(0.9686-scaledVolts)/(0.9686-0.9374))+80
        return returnPercent

    if (scaledVolts > 0.9063):
        returnPercent = 30*(1-(0.9374-scaledVolts)/(0.9374-0.9063))+50
        return returnPercent

    if (scaledVolts > 0.8749):
        returnPercent = 20*(1-(0.8749-scaledVolts)/(0.9063-0.8749))+11
        return returnPercent

    if (scaledVolts > 0.8437):
        returnPercent = 15*(1-(0.8437-scaledVolts)/(0.8749-0.8437))+1
        return returnPercent

    if (scaledVolts > 0.8126):
        returnPercent = 7*(1-(0.8126-scaledVolts)/(0.8437-0.8126))+2
        return returnPercent

    if (scaledVolts > 0.7812):
        returnPercent = 4*(1-(0.7812-scaledVolts)/(0.8126-0.7812))+1
        return returnPercent

    return 0

# write SunAirPlus stats out to file
def writeSunAirPlusStats():

    f = open("/home/pi/SDL_Pi_GroveWeatherPi/state/SunAirPlusStats.txt", "w")
    f.write(str(batteryVoltage) + '\n')
    f.write(str(batteryCurrent ) + '\n')
    f.write(str(solarVoltage) + '\n')
    f.write(str(solarCurrent ) + '\n')
    f.write(str(loadVoltage ) + '\n')
    f.write(str(loadCurrent) + '\n')
    f.write(str(batteryPower ) + '\n')
    f.write(str(solarPower) + '\n')
    f.write(str(loadPower) + '\n')
    f.write(str(batteryCharge) + '\n')
    f.close()

# write weather stats out to file
def writeWeatherStats():

    f = open("/home/pi/SDL_Pi_GroveWeatherPi/state/WeatherStats.txt", "w")
    f.write(str(totalRain) + '\n')
    f.write(str(as3935LightningCount) + '\n')
    f.write(str(as3935LastInterrupt) + '\n')
    f.write(str(as3935LastDistance) + '\n')
    f.write(str(as3935LastStatus) + '\n')
    f.write(str(currentWindSpeed) + '\n')
    f.write(str(currentWindGust) + '\n')
    f.write(str(totalRain)  + '\n')
    f.write(str(bmp180Temperature)  + '\n')
    f.write(str(bmp180Pressure) + '\n')
    f.write(str(bmp180Altitude) + '\n')
    f.write(str(bmp180SeaLevel)  + '\n')
    f.write(str(outsideTemperature) + '\n')
    f.write(str(outsideHumidity) + '\n')
    f.write(str(currentWindDirection) + '\n')
    f.write(str(currentWindDirectionVoltage) + '\n')
    f.write(str(HTUtemperature) + '\n')
    f.write(str(HTUhumidity) + '\n')
    f.close()



# sample and display
totalRain = 0
def sampleWeather():

    global as3935LightningCount
    global as3935, as3935LastInterrupt, as3935LastDistance, as3935LastStatus
    global currentWindSpeed, currentWindGust, totalRain
    global bmp180Temperature, bmp180Pressure, bmp180Altitude,  bmp180SeaLevel
    global outsideTemperature, outsideHumidity, crc_check
    global currentWindDirection, currentWindDirectionVoltage
    global SunlightVisible, SunlightIR, SunlightUV,  SunlightUVIndex
    global HTUtemperature, HTUhumidity, rain60Minutes

# blink GPIO LED when it's run
    GPIO.setup(SUNAIRLED, GPIO.OUT)
    GPIO.output(SUNAIRLED, True)
    time.sleep(0.2)
    GPIO.output(SUNAIRLED, False)
    print "----------------- "
    print " Weather Sampling"
    print "----------------- "
	#
	# turn I2CBus 0 on
    tca9545.write_control_register(TCA9545_CONFIG_BUS0)
    SDL_INTERRUPT_CLICKS = 1
#Read Wind Speed, Gust, Direction, Voltage, Total Rain
    currentWindSpeed = weatherStation.current_wind_speed()
    currentWindGust = weatherStation.get_wind_gust()
    totalRain = totalRain + weatherStation.get_current_rain_total()/SDL_INTERRUPT_CLICKS
    currentWindDirection = weatherStation.current_wind_direction()
    currentWindDirectionVoltage = weatherStation.current_wind_direction_voltage()

    print "----------------- "

#Read BMP280 Sensor
    bmp180Temperature = bmp280.read_temperature()
    bmp180Pressure = bmp280.read_pressure()/1000
    bmp180Altitude = bmp280.read_altitude()
    bmp180SeaLevel = bmp280.read_sealevel_pressure(config.BMP280_Altitude_Meters)/1000
#Set HTU variables
    HTUtemperature = 0.0
    HTUhumidity = 0.0
#Read HTU21DF (inside temp and humidity) Sensor
# We use a C library for this device as it just doesn't play well with Python and smbus/I2C libraries
    HTU21DFOut = subprocess.check_output(["htu21dflib/htu21dflib","-l"])
    splitstring = HTU21DFOut.split()
    HTUtemperature = float(splitstring[0])
    HTUhumidity = float(splitstring[1])

################
# turn I2CBus 3 on
    tca9545.write_control_register(TCA9545_CONFIG_BUS3)
# Read Sunlight, UV, IR Visible Sensor
    SunlightVisible = SI1145Lux.SI1145_VIS_to_Lux(Sunlight_Sensor.readVisible())
    SunlightIR = SI1145Lux.SI1145_IR_to_Lux(Sunlight_Sensor.readIR())
    SunlightUV = Sunlight_Sensor.readUV()
    SunlightUVIndex = SunlightUV / 100.0
################
# turn I2CBus 0 on
    tca9545.write_control_register(TCA9545_CONFIG_BUS0)
#Set Light variables until we get a sensor installed
#    SunlightVisible = 0
#    SunlightIR = 0
#    SunlightUV = 0
#    SunlightUVIndex = 0.0

    if (as3935LastInterrupt == 0x00):
 	as3935InterruptStatus = "----No Lightning detected---"

    if (as3935LastInterrupt == 0x01):
	as3935InterruptStatus = "Noise Floor: %s" % as3935LastStatus
	as3935LastInterrupt = 0x00

    if (as3935LastInterrupt == 0x04):
	as3935InterruptStatus = "Disturber: %s" % as3935LastStatus
	as3935LastInterrupt = 0x00

    if (as3935LastInterrupt == 0x08):
	as3935InterruptStatus = "Lightning: %s" % as3935LastStatus
	as3935LightningCount += 1
	as3935LastInterrupt = 0x00

# get AM2315 Outside Humidity and Outside Temperature
# turn I2CBus 0 on
    tca9545.write_control_register(TCA9545_CONFIG_BUS0)
    outsideTemperature, outsideHumidity, crc_check = am2315.sense()

def sampleSunAirPlus():

    global batteryVoltage, batteryCurrent, solarVoltage, solarCurrent, loadVoltage, loadCurrent
    global batteryPower, solarPower, loadPower, batteryCharge

# turn I2CBus 2 on
    tca9545.write_control_register(TCA9545_CONFIG_BUS2)
    print "----------------- "
    print " SunAirPlus Sampling"
    print "----------------- "
# blink GPIO LED when it's run
    GPIO.setup(SUNAIRLED, GPIO.OUT)
    GPIO.output(SUNAIRLED, True)
    time.sleep(0.2)
    GPIO.output(SUNAIRLED, False)
    busvoltage1 = sunAirPlus.getBusVoltage_V(LIPO_BATTERY_CHANNEL)
    shuntvoltage1 = sunAirPlus.getShuntVoltage_mV(LIPO_BATTERY_CHANNEL)
# minus is to get the "sense" right.   - means the battery is charging, + that it is discharging
    batteryCurrent = sunAirPlus.getCurrent_mA(LIPO_BATTERY_CHANNEL)
    batteryVoltage = busvoltage1 + (shuntvoltage1 / 1000)
    batteryPower = batteryVoltage * (batteryCurrent/1000)
    busvoltage2 = sunAirPlus.getBusVoltage_V(SOLAR_CELL_CHANNEL)
    shuntvoltage2 = sunAirPlus.getShuntVoltage_mV(SOLAR_CELL_CHANNEL)
    solarCurrent = -sunAirPlus.getCurrent_mA(SOLAR_CELL_CHANNEL)
    solarVoltage = busvoltage2 + (shuntvoltage2 / 1000)
    solarPower = solarVoltage * (solarCurrent/1000)
    busvoltage3 = sunAirPlus.getBusVoltage_V(OUTPUT_CHANNEL)
    shuntvoltage3 = sunAirPlus.getShuntVoltage_mV(OUTPUT_CHANNEL)
    loadCurrent = sunAirPlus.getCurrent_mA(OUTPUT_CHANNEL)
    loadVoltage = busvoltage3
    loadPower = loadVoltage * (loadCurrent/1000)
    batteryCharge = returnPercentLeftInBattery(batteryVoltage, 4.19)

def sampleSystemStats():
    import datetime
# Grab the stats we want.
# Free memory on the Pi
    fmem = psutil.virtual_memory()
# Free Swap on the Pi
    fswap = psutil.swap_memory()
# Free Disk on the Pi
    fdisk = psutil.disk_usage('/')
# CPU Load
    cpuload = psutil.cpu_percent(interval=1.0)
# Last Boot - this is seconds from EPOCH so convert
    lastboot = psutil.boot_time()
# Processes - grab PID list, filter for python, and parse so we know how much memory the Weather code and Raspi Connect are using
# grab PID list
    processcount = psutil.pids()
# Set variables to 0.0
    Weatherpimem = 0.0
    Controlpanmem = 0.0
# Call function to get pid of Weather Station code and then grab the memory used
    wpid = get_weather_pid()
    Weatherpimem = psutil.Process(wpid).memory_percent()
# Call function to get pid of Control Panel process and then grab the memory used
#    cpid = get_controlpan_pid()
#    Controlpanmem = psutil.Process(cpid).memory_percent()
# Grab cputemp from /sys/class/thermal
    temperature = subprocess.check_output(["cat", "/sys/class/thermal/thermal_zone0/temp"])
    cputemp = float(temperature)/1000.0
# Load it into MySQL
    try:
        print("trying database")
        con = mdb.connect('localhost', 'root', config.MySQL_Password, 'WeatherPi');
        cur = con.cursor()
        print "before query"
        query = 'INSERT INTO systemstats(TimeStamp, Freemem, Freeswap, Freedisk, Cputemp, Cpuload, processcount, lastboot, WeatherpiMem, ControlPanMem) VALUES(LOCALTIMESTAMP(), %.2f, %.2f, %.2f, %.2f, %.2f, %s, FROM_UNIXTIME(%i), %.2f, %.2f)' % (100.0 - fmem.percent, 100.0 - fswap.percent, 100.0 - fdisk.percent, cputemp, cpuload, len(processcount), lastboot, Weatherpimem, Controlpanmem)
        print("query=%s" % query)
        cur.execute(query)
        con.commit()

    except mdb.Error, e:

        print "Error %d: %s" % (e.args[0],e.args[1])
        con.rollback()
        #sys.exit(1)

    finally:
        cur.close()
        con.close()
        del cur
        del con

def get_weather_pid():
    name = "python" # want to filter on python processes only
    plist = psutil.pids() 	# load all process pids into plist
    for i in plist: # loop through all pids
	    if str(psutil.Process(i).name()) == name: # We only care about python processes
            p = psutil.Process(i) # Load p var with python process
	        cmdline = p.cmdline() # Load addition information about this python command in var
	        if "New_GroveWeatherPi.py" in cmdline[1]: # check second cmd name for our process
                return i # This is our Weather code pid so give it
    return None

def get_controlpan_pid():
   name = "python" # want to filter on python processes only
   plist = psutil.pids()   # load all process pids into plist
   for i in plist: # loop through all pids
       if str(psutil.Process(i).name()) == name: # We only care about python processes
           p = psutil.Process(i) # Load p var with python process
           cmdline = p.cmdline() # Load addition information about this python command in var
           if "RasPiConnectServer.py" in cmdline[1]: # check second cmd name for our process
               return i # This is our Weather code pid so give it
   return None


def sampleAndDisplay():

    global currentWindSpeed, currentWindGust, totalRain
    global bmp180Temperature, bmp180Pressure, bmp180Altitude,  bmp180SeaLevel
    global outsideTemperature, outsideHumidity, crc_check
    global currentWindDirection, currentWindDirectionVoltage
    global HTUtemperature, HTUhumidity
    global SunlightVisible, SunlightIR, SunlightUV,  SunlightUVIndex
    global totalRain, as3935LightningCount
    global as3935, as3935LastInterrupt, as3935LastDistance, as3935LastStatus

# turn I2CBus 0 on
    tca9545.write_control_register(TCA9545_CONFIG_BUS0)

    print "----------------- "
    print " Local WeatherRack Weather Sensors Sampling"
    print "----------------- "
    currentWindSpeed = weatherStation.current_wind_speed()
    currentWindGust = weatherStation.get_wind_gust()
    totalRain = totalRain + weatherStation.get_current_rain_total()

    print("Rain Total=\t%0.2f in")%(totalRain/25.4)
    print("Rain Last 60 Minutes=\t%0.2f in")%(rain60Minutes/25.4)
    print("Wind Speed=\t%0.2f MPH")%(currentWindSpeed/1.6)
    print("MPH wind_gust=\t%0.2f MPH")%(currentWindGust/1.6)
    print "Wind Direction=\t\t\t %0.2f Degrees" % weatherStation.current_wind_direction()
    print "Wind Direction Voltage=\t\t %0.3f V" % weatherStation.current_wind_direction_voltage()
#Send info to OLED
#    Scroll_SSD1306.addLineOLED(display,  ("Wind Speed=\t%0.2f MPH")%(currentWindSpeed/1.6))
#    Scroll_SSD1306.addLineOLED(display,  ("Rain Total=\t%0.2f in")%(totalRain/25.4))
#    Scroll_SSD1306.addLineOLED(display,  "Wind Dir=%0.2f Degrees" % weatherStation.current_wind_direction())

    print "----------------- "
    print "----------------- "
    print " DS3231 Real Time Clock"
    print "----------------- "

    currenttime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print "Raspberry Pi=\t" + str(currenttime)
#Send info to OLED
#    Scroll_SSD1306.addLineOLED(display,"%s" % ds3231.read_datetime())

    print "DS3231=\t\t%s" % ds3231.read_datetime()
    print "DS3231 Temperature= \t%0.2f C" % ds3231.getTemp()
    print "----------------- "
    print "----------------- "
    print " BMP280 Barometer"
    print "----------------- "
#Display BMP280 data
    print 'Temperature = \t{0:0.2f} C'.format(bmp280.read_temperature())
    print 'Pressure = \t{0:0.2f} KPa'.format(bmp280.read_pressure()/1000)
    print 'Altitude = \t{0:0.2f} m'.format(bmp280.read_altitude())
    print 'Sealevel Pressure = \t{0:0.2f} KPa'.format(bmp280.read_sealevel_pressure(config.BMP280_Altitude_Meters)/1000)
    print "----------------- "
    print "----------------- "

#    print " Sunlight Vi/IR/UV Sensor"
    print " Sunlight Vi/IR/UV Sensor"
    print "----------------- "
################
# turn I2CBus 3 on
    tca9545.write_control_register(TCA9545_CONFIG_BUS3)
    SunlightVisible = SI1145Lux.SI1145_VIS_to_Lux(Sunlight_Sensor.readVisible())
    SunlightIR = SI1145Lux.SI1145_IR_to_Lux(Sunlight_Sensor.readIR())
    SunlightUV = Sunlight_Sensor.readUV()
    SunlightUVIndex = SunlightUV / 100.0
    time.sleep(0.5)
    SunlightVisible = SI1145Lux.SI1145_VIS_to_Lux(Sunlight_Sensor.readVisible())
    SunlightIR = SI1145Lux.SI1145_IR_to_Lux(Sunlight_Sensor.readIR())
    SunlightUV = Sunlight_Sensor.readUV()
    SunlightUVIndex = SunlightUV / 100.0
    print 'Sunlight Visible(Lux): %0.2f ' % SunlightVisible
    print 'Sunlight IR(Lux):      %0.2f ' % SunlightIR
    print 'Sunlight UV Index:     %0.2f ' % SunlightUVIndex
    print "----------------- "
################
# turn I2CBus 0 on
    tca9545.write_control_register(TCA9545_CONFIG_BUS0)
# Initialize HTU21DF variables
    HTUtemperature = 0.0
    HTUhumidity = 0.0
    print "----------------- "
    print " HTU21DF Temp/Hum"
    print "----------------- "
#Read HTU21DF indoor temp and humidity sensor
# We use a C library for this device as it just doesn't play well with Python and smbus/I2C libraries
    HTU21DFOut = subprocess.check_output(["htu21dflib/htu21dflib","-l"])
    splitstring = HTU21DFOut.split()
    HTUtemperature = float(splitstring[0])
    HTUhumidity = float(splitstring[1])
    print "Temperature = \t%0.2f C" % HTUtemperature
    print "Humidity = \t%0.2f %%" % HTUhumidity
#Send data to OLED display
#    Scroll_SSD1306.addLineOLED(display,  "InTemp = \t%0.2f C" % HTUtemperature)
    print "----------------- "
    print "----------------- "
    print " AS3935 Lightning Detector "
    print "----------------- "

    print "Last result from AS3935:"

    if (as3935LastInterrupt == 0x00):
        print "----No Lightning detected---"

    if (as3935LastInterrupt == 0x01):
	print "Noise Floor: %s" % as3935LastStatus
	as3935LastInterrupt = 0x00

    if (as3935LastInterrupt == 0x04):
	print "Disturber: %s" % as3935LastStatus
	as3935LastInterrupt = 0x00

    if (as3935LastInterrupt == 0x08):
	print "Lightning: %s" % as3935LastStatus
#        Scroll_SSD1306.addLineOLED(display, '')
#        Scroll_SSD1306.addLineOLED(display, '---LIGHTNING---')
#        Scroll_SSD1306.addLineOLED(display, '')
	as3935LightningCount += 1
	as3935LastInterrupt = 0x00

    print "Lightning Count = ", as3935LightningCount
    print "----------------- "
# turn I2CBus 0 on
    tca9545.write_control_register(TCA9545_CONFIG_BUS0)
    print "----------------- "
    print " AM2315 Temperature/Humidity Sensor"
    print "----------------- "
#Read AM2315 outside Temp and Humidity Sensor
    outsideTemperature, outsideHumidity, crc_check = am2315.sense()
    print "outsideTemperature: %0.1f C" % outsideTemperature
    print "outsideHumidity: %0.1f %%" % outsideHumidity
    print "crc: %s" % crc_check
    print "----------------- "

# turn I2CBus 2 on
    tca9545.write_control_register(TCA9545_CONFIG_BUS2)

    print "----------------- "
    print "----------------- "
    print "----------------- "
    print "SunAirPlus Currents / Voltage "
    print "----------------- "
    shuntvoltage1 = 0
    busvoltage1   = 0
    current_mA1   = 0
    loadvoltage1  = 0
    busvoltage1 = sunAirPlus.getBusVoltage_V(LIPO_BATTERY_CHANNEL)
    shuntvoltage1 = sunAirPlus.getShuntVoltage_mV(LIPO_BATTERY_CHANNEL)
# minus is to get the "sense" right.   - means the battery is charging, + that it is discharging
    current_mA1 = sunAirPlus.getCurrent_mA(LIPO_BATTERY_CHANNEL)
    loadvoltage1 = busvoltage1  + (shuntvoltage1 / 1000)
    batteryPower = loadvoltage1 * (current_mA1/1000)
#Battery information displayed
    print "LIPO_Battery Bus Voltage: %3.2f V " % busvoltage1
    print "LIPO_Battery Shunt Voltage: %3.2f mV " % shuntvoltage1
    print "LIPO_Battery Load Voltage:  %3.2f V" % loadvoltage1
    print "LIPO_Battery Current 1:  %3.2f mA" % current_mA1
    print "Battery Power 1:  %3.2f W" % batteryPower
    print

    shuntvoltage2 = 0
    busvoltage2 = 0
    current_mA2 = 0
    loadvoltage2 = 0
    busvoltage2 = sunAirPlus.getBusVoltage_V(SOLAR_CELL_CHANNEL)
    shuntvoltage2 = sunAirPlus.getShuntVoltage_mV(SOLAR_CELL_CHANNEL)
    current_mA2 = -sunAirPlus.getCurrent_mA(SOLAR_CELL_CHANNEL)
    loadvoltage2 = busvoltage2  + (shuntvoltage2 / 1000)
    solarPower = loadvoltage2 * (current_mA2/1000)
#Solar Information displayed
    print "Solar Cell Bus Voltage 2:  %3.2f V " % busvoltage2
    print "Solar Cell Shunt Voltage 2: %3.2f mV " % shuntvoltage2
    print "Solar Cell Load Voltage 2:  %3.2f V" % loadvoltage2
    print "Solar Cell Current 2:  %3.2f mA" % current_mA2
    print "Solar Cell Power 2:  %3.2f W" % solarPower
    print

    shuntvoltage3 = 0
    busvoltage3 = 0
    current_mA3 = 0
    loadvoltage3 = 0
    busvoltage3 = sunAirPlus.getBusVoltage_V(OUTPUT_CHANNEL)
    shuntvoltage3 = sunAirPlus.getShuntVoltage_mV(OUTPUT_CHANNEL)
    current_mA3 = sunAirPlus.getCurrent_mA(OUTPUT_CHANNEL)
    loadvoltage3 = busvoltage3
    loadPower = loadvoltage3 * (current_mA3/1000)
#Output Information displayed
    print "Output Bus Voltage 3:  %3.2f V " % busvoltage3
    print "Output Shunt Voltage 3: %3.2f mV " % shuntvoltage3
    print "Output Load Voltage 3:  %3.2f V" % loadvoltage3
    print "Output Current 3:  %3.2f mA" % current_mA3
    print "Output Power 3:  %3.2f W" % loadPower
    print

    print "------------------------------"

def tweetWeather(Whattotweet):
    global as3935LightningCount
    global as3935, as3935LastInterrupt, as3935LastDistance, as3935LastStatus
    global currentWindSpeed, currentWindGust, totalRain
    global bmp180Temperature, bmp180Pressure, bmp180Altitude,  bmp180SeaLevel
    global outsideTemperature, outsideHumidity, crc_check
    global currentWindDirection, currentWindDirectionVoltage
    global SunlightVisible, SunlightIR, SunlightUV,  SunlightUVIndex
    global HTUtemperature, HTUhumidity

# package up date to tweet
    now = datetime.now().strftime("%H:%M:%S")
    tweettime = "SummerGlen GC time is \t" + str(now)
	twitter = Twython(config.consumer_key, config.consumer_secret, config.access_key, config.access_secret)
	if Whattotweet == 'tempandhum':
        temphum = "Current Temp: %0.1f C " % outsideTemperature + "Current Humidity: %0.1f %%" % outsideHumidity
        tweet = str(tweettime)+" "+str(temphum)
        twitter.update_status(status=tweet)
        print("Tweeted: {}".format(tweet))
	elif Whattotweet == 'rain':
	    raintweet = "Rain Total=\t%0.2f in")%(totalRain/25.4 + " " + "Rain Last 60 Minutes=\t%0.2f in")%(rain60Minutes/25.4
		tweet = str(tweettime)+" "+str(raintweet)
        print("Tweeted: {}".format(tweet))
	elif Whattotweet == 'wind':
		if (currentWindDirection == 0):
			winddir = "South"
		elif (currentWindDirection == 22.5):
			winddir = "SSW"
		elif (currentWindDirection == 45):
			winddir = "SW"
		elif (currentWindDirection == 67.5):
			winddir = "WSW"
		elif (currentWindDirection == 90):
			winddir = "West"
		elif (currentWindDirection == 112.5):
			winddir = "WNW"
		elif (currentWindDirection == 135):
			winddir = "NW"
		elif (currentWindDirection == 157.5):
			winddir = "NNW"
		elif (currentWindDirection == 180):
			winddir = "North"
		elif (currentWindDirection == 202.5):
			winddir = "NNE"
		elif (currentWindDirection == 225):
			winddir = "NE"
		elif (currentWindDirection == 247.5):
			winddir = "ENE"
		elif (currentWindDirection == 270):
			winddir = "East"
		elif (currentWindDirection == 292.5):
			winddir = "ESE"
		elif (currentWindDirection == 315):
			winddir = "SE"
		elif (currentWindDirection == 337.5):
			winddir = "SSE"
		windtweet = "Current Wind Speed=\t%0.2f MPH")%(currentWindSpeed/1.6) + " " + "Current Wind Gust=\t%0.2f MPH")%(currentWindGust/1.6) + " " + "Wind out of the\t%s " % winddir
        tweet = str(tweettime)+" "+str(windtweet)
        twitter.update_status(status=tweet)
        print("Tweeted: {}".format(tweet))
    elif Whattotweet == 'thgraph':
	    msg = "SummerGlen GC 10 day Temperature Humidity Graph"
	    with open('/home/pi/SDL_Pi_GroveWeatherPi/RasPiConnectServer/static/TemperatureHumidityGraph.png', 'rb') as image:
	    twitter.update_status_with_media(status=msg, media=image)
	    print("Tweeted: Temp/Hum graph")
	elif Whattotweet == 'windgraph':
		msg = "SummerGlen GC 10 day Wind Speed and Gust Graph"
		with open('/home/pi/SDL_Pi_GroveWeatherPi/RasPiConnectServer/static/WindGraph.png', 'rb') as image:
		twitter.update_status_with_media(status=msg, media=image)
		print("Tweeted: Wind graph")
	elif Whattotweet == 'barograph':
		msg = "SummerGlen GC 10 day Barometric Pressure and Lightning Graph"
		with open('/home/pi/SDL_Pi_GroveWeatherPi/RasPiConnectServer/static/BarometerLightningGraph.png', 'rb') as image:
		twitter.update_status_with_media(status=msg, media=image)
		print("Tweeted: Barometric Pressure graph")

def writeWeatherRecord():
    global as3935LightningCount
    global as3935, as3935LastInterrupt, as3935LastDistance, as3935LastStatus
    global currentWindSpeed, currentWindGust, totalRain
    global bmp180Temperature, bmp180Pressure, bmp180Altitude,  bmp180SeaLevel
    global outsideTemperature, outsideHumidity, crc_check
    global currentWindDirection, currentWindDirectionVoltage
    global SunlightVisible, SunlightIR, SunlightUV,  SunlightUVIndex
    global HTUtemperature, HTUhumidity

# now we have the data, stuff it in the database
    try:
	    print("trying database")
    	con = mdb.connect('localhost', 'root', config.MySQL_Password, 'WeatherPi');
    	cur = con.cursor()
	    print "before query"
	    query = 'INSERT INTO WeatherData(TimeStamp,as3935LightningCount, as3935LastInterrupt, as3935LastDistance, as3935LastStatus, currentWindSpeed, currentWindGust, totalRain,  bmp180Temperature, bmp180Pressure, bmp180Altitude,  bmp180SeaLevel,  outsideTemperature, outsideHumidity, currentWindDirection, currentWindDirectionVoltage, insideTemperature, insideHumidity) VALUES(LOCALTIMESTAMP(), %.3f, %.3f, %.3f, "%s", %.3f, %.3f, %.3f, %i, %.3f, %.3f, %.3f, %.3f, %.3f, %.3f, %.3f, %.3f, %.3f)' % (as3935LightningCount, as3935LastInterrupt, as3935LastDistance, as3935LastStatus, currentWindSpeed, currentWindGust, totalRain,  bmp180Temperature, bmp180Pressure, bmp180Altitude,  bmp180SeaLevel,  outsideTemperature, outsideHumidity, currentWindDirection, currentWindDirectionVoltage, HTUtemperature, HTUhumidity)
	    print("query=%s" % query)
	    cur.execute(query)
# Sunlight Sensor database
	    query = 'INSERT INTO Sunlight(TimeStamp, Visible, IR, UV, UVIndex) VALUES(LOCALTIMESTAMP(), %d, %d, %d, %.3f)' % (SunlightVisible, SunlightIR, SunlightUV, SunlightUVIndex)
	    print("query=%s" % query)
	    cur.execute(query)
	    con.commit()
    except mdb.Error, e:
    	print "Error %d: %s" % (e.args[0],e.args[1])
    	con.rollback()
    	#sys.exit(1)
    finally:
       	cur.close()
        con.close()
	    del cur
	    del con

def writePowerRecord():
# now we have the data, stuff it in the database
    try:
	print("trying database")
        con = mdb.connect('localhost', 'root', config.MySQL_Password, 'WeatherPi');
    	cur = con.cursor()
	    print "before query"
	    query = 'INSERT INTO PowerSystem(TimeStamp, batteryVoltage, batteryCurrent, solarVoltage, solarCurrent, loadVoltage, loadCurrent, batteryPower, solarPower, loadPower, batteryCharge) VALUES (LOCALTIMESTAMP (), %.3f, %.3f, %.3f, %.3f, %.3f, %.3f, %.3f, %.3f, %.3f, %.3f)' % (batteryVoltage, batteryCurrent, solarVoltage, solarCurrent, loadVoltage, loadCurrent, batteryPower, solarPower, loadPower, batteryCharge)
	    print("query=%s" % query)
	    cur.execute(query)
	    con.commit()
    except mdb.Error, e:
       	print "Error %d: %s" % (e.args[0],e.args[1])
        con.rollback()
        #sys.exit(1)
    finally:
        cur.close()
        con.close()
        del cur
	    del con

WATCHDOGTRIGGER = 17

def patTheDog():
	# pat the dog
    print "------Patting The Dog------- "
    GPIO.setup(WATCHDOGTRIGGER, GPIO.OUT)
    GPIO.output(WATCHDOGTRIGGER, False)
    time.sleep(0.2)
    GPIO.output(WATCHDOGTRIGGER, True)
    GPIO.setup(WATCHDOGTRIGGER, GPIO.IN)

def shutdownPi(why):
    pclogging.log(pclogging.INFO, __name__, "Pi Shutting Down: %s" % why)
    sys.stdout.flush()
    time.sleep(10.0)
    os.system("sudo shutdown -h now")

def rebootPi(why):
    pclogging.log(pclogging.INFO, __name__, "Pi Rebooting: %s" % why)
    os.system("sudo shutdown -r now")

def blinkSunAirLED2X(howmany):
    # blink GPIO LED when it's run
    GPIO.setup(SUNAIRLED, GPIO.OUT)
    i = 0
    while (i< howmany):
    	  GPIO.output(SUNAIRLED, True)
    	  time.sleep(0.2)
    	  GPIO.output(SUNAIRLED, False)
    	  time.sleep(0.2)
 	  i = i +1

import urllib2

def checkInternetConnection():
    try:
        urllib2.urlopen("http://www.google.com").close()
    except urllib2.URLError:
        print "Internet Not Connected"
        time.sleep(1)
	    return False
    else:
        print "Internet Connected"
	    return True

WLAN_check_flg = 0

def WLAN_check():
        '''
        This function checks if the WLAN is still up by pinging the router.
        If there is no return, we'll reset the WLAN connection.
        If the resetting of the WLAN does not work, we need to reset the Pi.
        source http://www.raspberrypi.org/forums/viewtopic.php?t=54001&p=413095
        '''
	global WLAN_check_flg

        if (config.enable_WLAN_Detection == True):
          ping_ret = subprocess.call(['ping -c 2 -w 1 -q '+config.PingableRouterAddress+' |grep "1 received" > /dev/null 2> /dev/null'], shell=True)

	  print "checking WLAN:  ping_ret=%i WLAN_check_flg=%i" % (ping_ret, WLAN_check_flg)
	  if ping_ret:
# we lost the WLAN connection.
# did we try a recovery already?
            if (WLAN_check_flg>2):
# we have a serious problem and need to reboot the Pi to recover the WLAN connection
		print "logger WLAN Down, Pi is forcing a reboot"
   		pclogging.log(pclogging.ERROR, __name__, "WLAN Down, Pi is forcing a reboot")
                WLAN_check_flg = 0
		time.sleep(5)
		print "time to Reboot Pi from WLAN_check"
		rebootPi("WLAN Down reboot")
		#print "logger WLAN Down, Pi is forcing a Shutdown"
		#shutdownPi("WLAN Down halt") # halt pi and let the watchdog restart it
        #subprocess.call(['sudo shutdown -r now'], shell=True)
            else:
                # try to recover the connection by resetting the LAN
                #subprocess.call(['logger "WLAN is down, Pi is resetting WLAN connection"'], shell=True)
	        print "WLAN Down, Pi is trying resetting WLAN connection"
	        pclogging.log(pclogging.WARNING, __name__, "WLAN Down, Pi is resetting WLAN connection" )
                WLAN_check_flg = WLAN_check_flg + 1 # try to recover
                subprocess.call(['sudo /sbin/ifdown wlan0 && sleep 10 && sudo /sbin/ifup --force wlan0'], shell=True)
          else:
            WLAN_check_flg = 0
	    print "WLAN is OK"

        else:
	    # enable_WLAN_Detection is off
            WLAN_check_flg = 0
	    print "WLAN Detection is OFF"


#Rain calculations

rainArray = []
for i in range(20):
    rainArray.append(0)

lastRainReading = 0.0

def addRainToArray(plusRain):
    global rainArray
    del rainArray[0]
    rainArray.append(plusRain)
    #print "rainArray=", rainArray

def totalRainArray():
    global rainArray
    total = 0
    for i in range(20):
 	total = total+rainArray[i]
    return total

def updateRain():
    global lastRainReading, rain60Minutes
    addRainToArray(totalRain - lastRainReading)
    rain60Minutes = totalRainArray()
    lastRainReading = totalRain
    print "rain in past 60 minute=",rain60Minutes

def checkForShutdown():
    if (batteryVoltage < 3.5):
	    print "--->>>>Time to Shutdown<<<<---"
	    shutdownPi("low voltage shutdown")

print  ""
print "SummerGlen GC Solar Powered Weather Station version 2.0"
print ""
print "A Schatzie Dog (c) approved project"
print ""
print "Program Started at:"+ time.strftime("%m-%d-%Y %H:%M:%S")
print ""

# Initialize Variables
bmp180Temperature =  0
bmp180Pressure = 0
bmp180Altitude = 0
bmp180SeaLevel = 0
# initialize appropriate weather variables
currentWindDirection = 0
currentWindDirectionVoltage = 0.0
rain60Minutes = 0.0
as3935Interrupt = False
pclogging.log(pclogging.INFO, __name__, "SummerGlen GC WeatherPi version 2.0 started")

#  Main Loop
secondCount = 1
while True:
# process Interrupts from Lightning
    if (as3935Interrupt == True):
	try:
        process_as3935_interrupt()
	except:
	    print "exception - as3935 I2C did not work"

    tca9545.write_control_register(TCA9545_CONFIG_BUS0)
# process commands from RasPiConnect
    print "---------------------------------------- "
    processCommand()
    if ((secondCount % 10) == 0):
# print every 10 seconds
	   sampleAndDisplay()
	   patTheDog()      # reset the WatchDog Timer
	   blinkSunAirLED2X(2)
# every 5 minutes, push data to mysql, update rain total and check for shutdown
    if ((secondCount % (5*60)) == 0):
        sampleSystemStats()
        sampleWeather()
        sampleSunAirPlus()
		updateRain()
	    writeWeatherRecord()
	    writePowerRecord()
        checkForShutdown()
# every 15 minutes, build new graphs
    if ((secondCount % (15*60)) == 0):
        sampleSystemStats()
        sampleWeather()
        sampleSunAirPlus()
	    doAllGraphs.doAllGraphs()
# every 30 minutes, check wifi connections
    if ((secondCount % (30*60)) == 0):
    	WLAN_check()
# Every 2 hours Tweet basic Weather
#    if ((secondCount % (1*60)) == 0):
#        sampleWeather()
#        tweetWeather()
# every 48 hours, reboot
    if ((secondCount % (60*60*48)) == 0):
	   rebootPi("48 hour reboot")
       secondCount = secondCount + 1
	# reset secondCount to prevent overflow forever
    if (secondCount == 1000001):
	    secondCount = 1

    time.sleep(1.0)

#!/usr/bin/python
# SummerGlen GC Weather Station
# A Shatzie dog production (c)
#
# Here is the code that pulls
# data and creates the control panel buttons and graphs
#
#

# system imports
import sys
import subprocess
import os
import time
# RasPiConnectImports
import Config
import Validate
import BuildResponse
from time import localtime, strftime

try:
	import conflocal as config
except ImportError:
	import config

import MySQLdb as mdb

# Send Command to Pi
def sendCommandToWeatherPiAndWait(command):
	status = True
	print "Sending Command: ", command
    f = open("/home/pi/WeatherPi/state/WeatherCommand.txt", "w")
    f.write(command)
    f.close()
	timeout = 20
	commandresponse = ""
	while timeout > 0:
		time.sleep(1.0)
		print "Waiting for Response"
    	f = open("/home/pi/WeatherPi/state/WeatherCommand.txt", "r")
    	commandresponse = f.read()
    	f.close()
		timeout = timeout-1
		if (commandresponse == "DONE"):
			status = True
			print "Response = DONE"
			timeout = 0
		else:
			status = False

	return status

def sendCommandToWeatherPiAndWaitReturningValue(command):
	status = True
	print "Sending Command For Return Value: ", command
    f = open("/home/pi/WeatherPi/state/WeatherCommand.txt", "w")
    f.write(command)
    f.close()
	timeout = 20
	commandresponse = ""
	while timeout > 0:
		time.sleep(1.0)
		print "Waiting for Response"
        f = open("/home/pi/WeatherPi/state/WeatherCommand.txt", "r")
    	commandresponse = f.read()
		value = f.read()
    	f.close()
		timeout = timeout-1
		if (commandresponse == "DONE"):
			status = value
			print "Response = ", value
			timeout = 0
		else:
			status = "TimeOut"

	return status

def sendCommandToWeatherPiAndReturn(command):

	return

def setupSunAirPlusStats():
    global batteryVoltage, batteryCurrent, solarVoltage, solarCurrent, loadVoltage, loadCurrent
    global batteryPower, solarPower, loadPower, batteryCharge
	f = open("/home/pi/WeatherPi/state/SunAirPlusStats.txt", "r")
    batteryVoltage = float(f.readline())
	batteryCurrent = float(f.readline())
	solarVoltage = float(f.readline())
	solarCurrent = float(f.readline())
	loadVoltage = float(f.readline())
	loadCurrent = float(f.readline())
	batteryPower = float(f.readline())
	solarPower = float(f.readline())
	loadPower = float(f.readline())
	batteryCharge = float(f.readline())
    f.close()

def returnBatteryPercentage(voltagenow, maxvoltage):
	scaledv = voltagenow / maxvoltage
	if (scaledv > 1.0):
		scaledv = 1.0
	if (scaledv > .9686):
		returnPercent = 10*(1-(1.0-scaledv)/(1.0-.9686))+90
		return returnPercent
	if (scaledv > 0.9374):
		returnPercent = 10*(1-(0.9686-scaledv)/(0.9686-0.9374))+80
		return returnPercent
	if (scaledv > 0.9063):
		returnPercent = 30*(1-(0.9374-scaledv)/(0.9374-0.9063))+50
		return returnPercent
	if (scaledv > 0.8749):
		returnPercent = 30*(1-(0.8749-scaledv)/(0.9063-0.8749))+20
		return returnPercent
	if (scaledv > 0.8437):
		returnPercent = 17*(1-(0.8437-scaledv)/(0.8749-0.8437))+3
		return returnPercent
   	if (scaledv > 0.8126):
		returnPercent = 1*(1-(0.8126-scaledv)/(0.8437-0.8126))+2
		return returnPercent
	if (scaledv > 0.7812):
		returnPercent = 1*(1-(0.7812-scaledv)/(0.7812-0.8126))+1
		return returnPercent
	return 0

def setupWeatherStats():
    global totalRain, as3935LightningCount
    global as3935LastInterrupt, as3935LastDistance, as3935LastStatus
    global currentWindSpeed, currentWindGust, totalRain
    global  bmp180Temperature, bmp180Pressure, bmp180Altitude,  bmp180SeaLevel
    global outsideTemperature, outsideHumidity
    global currentWindDirection, currentWindDirectionVoltage
	global insideTemperature, insideHumidity
    f = open("/home/pi/WeatherPi/state/WeatherStats.txt", "r")
    totalRain = f.readline()
    as3935LightningCount = float(f.readline())
    as3935LastInterrupt = float(f.readline())
    as3935LastDistance = float(f.readline())
    as3935LastStatus = f.readline()
    currentWindSpeed = float(f.readline())
    currentWindGust = float(f.readline())
    totalRain = float(f.readline())
    bmp180Temperature = float(f.readline())
    bmp180Pressure = float(f.readline())
    bmp180Altitude = float(f.readline())
    bmp180SeaLevel = float(f.readline())
    outsideTemperature = float(f.readline())
    outsideHumidity = float(f.readline())
	currentWindDirection = float(f.readline())
	currentWindDirectionVoltage = float(f.readline())
    insideTemperature = float(f.readline())
    insideHumidity = float(f.readline())
    f.close()


def ExecuteUserObjects(objectType, element):
# Example Objects
# fetch information from XML for use in user elements
    objectServerID = element.find("./OBJECTSERVERID").text
    objectID = element.find("./OBJECTID").text
	objectAction = element.find(".OBJECTACTION").text
	objectName = element.find("./OBJECTNAME").text
    objectFlags = element.find("./OBJECTFLAGS").text
    if (Config.debug()):
    	print("objectServerID = %s" % objectServerID)
	#vakidate request
	validate = Validate.checkForValidate(element)
    if (Config.debug()):
        print "VALIDATE=%s" % validate
# Build the header for the response
	outgoingXMLData = BuildResponse.buildHeader(element)
	
# SS-1 - Server Present
    if (objectServerID == "SS-1"):
        #check for validate request
        # validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
		answ = "2"
	    #answ = ""
		if (Config.debug()):
			print "In local SS-1"
			print("answ = %s" % answ)
		responseData = answ
		print "sampling weather"
		sendCommandToWeatherPiAndWait("SAMPLEBOTH")
# now setup internal variables
		setupWeatherStats()
		setupSunAirPlusStats()
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData

# B-1 - Sample Both and Do All Graphs
    if (objectServerID == "B-1"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
		answ = "OK"
		#answ = ""
		if (Config.debug()):
			print "In local B-1"
			print("answ = %s" % answ)

		print "sampling weather"
		sendCommandToWeatherPiAndWait("SAMPLEBOTHGRAPHS")
# now setup internal variables
		setupWeatherStats()
		setupSunAirPlusStats()
		responseData = "OK"
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData

	# FB-1 - Power Graph Selection Feedback
	if (objectServerID == "FB-1"):

		# Check for Validation
		# Allows RasPiConnect to verify
		if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
        responseData = "XXX"
        if (objectName is None):
            objectName = "XXX"
        lowername = objectName.lower()
		if (lowername == "voltage graph"):
            responseData = "current graph"
            responseData = responseData.title()
            f = open("./local/PowerGraphSelect.txt", "w")
			f.write(lowername)
            f.close()
        elif (lowername == "current graph"):
            responseData = "voltage graph"
            responseData = responseData.title()
            f = open("./local/PowerGraphSelect.txt", "w")
            f.write(lowername)
            f.close()
        else:
# default value
            responseData = "voltage graph"
            responseData = responseData.title()
            f = open("./local/PowerGraphSelect.txt", "w")
            f.write(lowername)
            f.close()
		if (Config.debug()):
            print "In local FB-1"
            print("responseData = %s" % responseData)
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData

	# FB-2 - Graph Selection Feedback
    if (objectServerID == "FB-2"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
		responseData = "XXX"
		if (objectName is None):
			objectName = "XXX"
		lowername = objectName.lower()
		if (lowername == "temp / hum graph"):
			responseData = "baro graph"
			responseData = responseData.title()
            f = open("./local/GraphSelect.txt", "w")
            f.write(lowername)
            f.close()
		elif (lowername == "baro graph"):
			responseData = "wind graph"
			responseData = responseData.title()
            f = open("./local/GraphSelect.txt", "w")
            f.write(lowername)
            f.close()
		elif (lowername == "wind graph"):
			responseData = "temp / hum graph"
			responseData = responseData.title()
            f = open("./local/GraphSelect.txt", "w")
            f.write(lowername)
            f.close()
		else:
			# default value
			responseData = "temp / hum graph"
			responseData = responseData.title()
            f = open("./local/GraphSelect.txt", "w")
            f.write(lowername)
            f.close()
		if (Config.debug()):
			print "In local FB-2"
			print("responseData = %s" % responseData)
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData

# W-3 System Statistics Graph
	if (objectServerID == "W-3"):
# Check for RasPiConnect validation request
		if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
        if (Config.debug()):
            print "In local W-3"
		imageName = "SystemStatsGraph.png"
		responseData = "<html><head>"
        responseData += "<title></title><style>body,html,iframe{margin:0;padding:0;}</style>"
        responseData += "<META HTTP-EQUIV='CACHE-CONTROL' CONTENT='NO-CACHE, MUST-REVALIDATE'>"
        responseData += "<META HTTP-EQUIV='PRAGMA' CONTENT='NO-CACHE'>"
        responseData += "</head>"
        responseData += "<body><img src=\""
        responseData += Config.localURL()
        responseData += "static/"
        import random
        answer = random.randrange(0,100,1)
		responseData += imageName + "?x" + str(answer )
        responseData += "\" type=\"jpg\" width=\"730\" height=\"300\">"
        responseData +="</body>"
        responseData += "</html>"
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData

# W-5 Wind Direction
    if (objectServerID == "W-5"):
# Check for RasPiConnect validation request
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
        if (Config.debug()):
            print "In local W-5"
		imageName = "ESE.png"
        if (currentWindDirection == 0):
			imageName = "South.png"
		elif (currentWindDirection == 22.5):
			imageName = "SSW.png"
		elif (currentWindDirection == 45):
			imageName = "SW.png"
		elif (currentWindDirection == 67.5):
            imageName = "WSW.png"
        elif (currentWindDirection == 90):
            imageName = "West.png"
		elif (currentWindDirection == 112.5):
            imageName = "WNW.png"
        elif (currentWindDirection == 135):
            imageName = "NW.png"
        elif (currentWindDirection == 157.5):
            imageName = "NNW.png"
        elif (currentWindDirection == 180):
            imageName = "North.png"
    	elif (currentWindDirection == 202.5):
            imageName = "NNE.png"
        elif (currentWindDirection == 225):
            imageName = "NE.png"
        elif (currentWindDirection == 247.5):
            imageName = "ENE.png"
        elif (currentWindDirection == 270):
            imageName = "East.png"
        elif (currentWindDirection == 292.5):
            imageName = "ESE.png"
        elif (currentWindDirection == 315):
            imageName = "SE.png"
        elif (currentWindDirection == 337.5):
            imageName = "SSE.png"

        responseData = "<html><head>"
        responseData += "<title></title><style>body,html,iframe{margin:0;padding:0;}</style>"
        responseData += "<META HTTP-EQUIV='CACHE-CONTROL' CONTENT='NO-CACHE, MUST-REVALIDATE'>"
        responseData += "<META HTTP-EQUIV='PRAGMA' CONTENT='NO-CACHE'>"
        responseData += "</head>"
        responseData += "<body><img src=\""
        responseData += Config.localURL()
        responseData += "static/"
        import random
        answer = random.randrange(0,100,1)
        responseData += imageName + "?x" + str(answer )
        responseData += "\" type=\"jpg\" width=\"150\" height=\"140\">"
        responseData +="</body>"
        responseData += "</html>"
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData



	# W-2 - Power Graph View
    if (objectServerID == "W-2"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
        if (Config.debug()):
            print "In local W-2"
        lowername = "voltage graph"
        try:
            f = open("./local/PowerGraphSelect.txt", "r")
            tempString = f.read()
            f.close()
            lowername = tempString
        except IOError as e:
            print "I/O error({0}): {1}".format(e.errno, e.strerror)
		print "lowername=", lowername
		if (lowername == "voltage graph"):
            imageName = "PowerVoltageGraph.png"
        elif (lowername == "current graph"):
			imageName = "PowerCurrentGraph.png"
        else:
            imageName = "PowerVoltageGraph.png"

		responseData = "<html><head>"
        responseData += "<title></title><style>body,html,iframe{margin:0;padding:0;}</style>"
        responseData += "<META HTTP-EQUIV='CACHE-CONTROL' CONTENT='NO-CACHE, MUST-REVALIDATE'>"
        responseData += "<META HTTP-EQUIV='PRAGMA' CONTENT='NO-CACHE'>"
        responseData += "</head>"
        responseData += "<body><img src=\""
        responseData += Config.localURL()
        responseData += "static/"
        import random
        answer = random.randrange(0,100,1)
        responseData += imageName + "?x" + str(answer )
        responseData += "\" type=\"jpg\" width=\"730\" height=\"300\">"
        responseData +="</body>"
        responseData += "</html>"
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData


# W-1 - Temp/Hum, Baro, Wind, Graph View
    if (objectServerID == "W-1"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
		#answ = ""
		if (Config.debug()):
			print "In local W-1"
		lowername = "temp / hum graph"
		try:
      		f = open("./local/GraphSelect.txt", "r")
       		tempString = f.read()
       		f.close()
			lowername = tempString
		except IOError as e:
			print "I/O error({0}): {1}".format(e.errno, e.strerror)
		print "lowername=", lowername
		if (lowername == "baro graph"):
			imageName = "BarometerLightningGraph.png"
		elif (lowername == "temp / hum graph"):
			imageName = "TemperatureHumidityGraph.png"
		elif (lowername == "wind graph"):
			imageName = "WindGraph.png"
		else:
			imageName = "TemperatureHumidityGraph.png"

        responseData = "<html><head>"
        responseData += "<title></title><style>body,html,iframe{margin:0;padding:0;}</style>"
		responseData += "<META HTTP-EQUIV='CACHE-CONTROL' CONTENT='NO-CACHE, MUST-REVALIDATE'>"
		responseData += "<META HTTP-EQUIV='PRAGMA' CONTENT='NO-CACHE'>"
        responseData += "</head>"
        responseData += "<body><img src=\""
        responseData += Config.localURL()
        responseData += "static/"
		import random
		answer = random.randrange(0,100,1)
        responseData += imageName + "?x" + str(answer )
        responseData += "\" type=\"jpg\" width=\"730\" height=\"300\">"
        responseData +="</body>"
        responseData += "</html>"
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData

# W-6 ALL Time Highs and Lows

    if (objectServerID == "W-6"):
#check for validation request
#This allows the RasPiConnect program to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
        try:
            print ("trying database")
            db = mdb.connect('localhost', 'root', config.MySQL_Password, 'Weatherpi');
            cur = db.cursor()
            query = 'SELECT TimeStamp, outsideTemperature FROM WeatherData ORDER BY outsideTemperature ASC LIMIT 1'
            cur.execute(query)
            result = cur.fetchone()
            aoltemptime = result[0]
            aoltemp = result[1]
            query = 'SELECT TimeStamp, outsideTemperature FROM WeatherData ORDER BY outsideTemperature DESC LIMIT 1'
            cur.execute(query)
            result = cur.fetchone()
            aohtemptime = result[0]
            aohtemp = result[1]
            query = 'SELECT TimeStamp, insideTemperature FROM WeatherData ORDER BY insideTemperature ASC LIMIT 1'
            cur.execute(query)
            result = cur.fetchone()
            ailtemptime = result[0]
            ailtemp = result[1]
            query = 'SELECT TimeStamp, insideTemperature FROM WeatherData ORDER BY insideTemperature DESC LIMIT 1'
            cur.execute(query)
            result = cur.fetchone()
            aihtemptime = result[0]
            aihtemp = result[1]
#Humidity
            query = 'SELECT TimeStamp, outsideHumidity FROM WeatherData ORDER BY outsideHumidity ASC LIMIT 1'
            cur.execute(query)
            result = cur.fetchone()
            aolhumtime = result[0]
            aolhum = result[1]
            query = 'SELECT TimeStamp, outsideHumidity FROM WeatherData ORDER BY outsideHumidity DESC LIMIT 1'
            cur.execute(query)
            result = cur.fetchone()
            aohhumtime = result[0]
            aohhum = result[1]
            query = 'SELECT TimeStamp, insideHumidity FROM WeatherData ORDER BY insideHumidity ASC LIMIT 1'
            cur.execute(query)
            result = cur.fetchone()
            ailhumtime = result[0]
            ailhum = result[1]
            query = 'SELECT TimeStamp, insideHumidity FROM WeatherData ORDER BY insideHumidity DESC LIMIT 1'
            cur.execute(query)
            result = cur.fetchone()
            aihhumtime = result[0]
            aihhum = result[1]
#Wind
            query = 'SELECT TimeStamp, currentWindSpeed FROM WeatherData WHERE currentWindSpeed > 0 ORDER BY currentWindSpeed ASC LIMIT 1'
            cur.execute(query)
            result = cur.fetchone()
            aolwindtime = result[0]
            aolwind = result[1]
            query = 'SELECT TimeStamp, currentWindSpeed FROM WeatherData ORDER BY currentWindSpeed DESC LIMIT 1'
            cur.execute(query)
            result = cur.fetchone()
            aohwindtime = result[0]
            aohwind = result[1]
            query = 'SELECT TimeStamp, currentWindGust FROM WeatherData WHERE currentWindgust > 0 ORDER BY currentWindGust ASC LIMIT 1'
            cur.execute(query)
            result = cur.fetchone()
            aolwindgtime = result[0]
            aolwindg = result[1]
            query = 'SELECT TimeStamp, currentWindGust FROM WeatherData ORDER BY currentWindGust DESC LIMIT 1'
            cur.execute(query)
            result = cur.fetchone()
            aohwindgtime = result[0]
            aohwindg = result[1]
#BMP
            query = 'SELECT TimeStamp, bmp180SeaLevel FROM WeatherData ORDER BY bmp180SeaLevel ASC LIMIT 1'
            cur.execute(query)
            result = cur.fetchone()
            aolbmptime = result[0]
            aolbmp = result[1] * 10
            query = 'SELECT TimeStamp, bmp180SeaLevel FROM WeatherData ORDER BY bmp180SeaLevel DESC LIMIT 1'
            cur.execute(query)
            result = cur.fetchone()
            aohbmptime = result[0]
            aohbmp = result[1] * 10
        except mdb.Error, e:
            print "Error %d: %s" % (e.args[0],e.args[1])
        finally:
            print ("finished")
            cur.close()
            db.close()
            del cur
            del db
            responseData = ""
            with open ("./Templates/W-909.html", "r") as myfile:
            responseData += myfile.read().replace('\n', '')
            title = "Alltime High and Lows - SummerGlen GC Ocala, FL"
            responseData = responseData.replace("Vartitle", title)
            # now replace our variables in the template with the actual data
            responseData = responseData.replace("HighOT", str(aohtemp))
            responseData = responseData.replace("HOTTime", str(aohtemptime))
            responseData = responseData.replace("LowOT", str(aoltemp))
            responseData = responseData.replace("LOTTime", str(aoltemptime))
            responseData = responseData.replace("HighIT", str(aihtemp))
            responseData = responseData.replace("HITTime", str(aihtemptime))
            responseData = responseData.replace("LowIT", str(ailtemp))
            responseData = responseData.replace("LITTime", str(ailtemptime))
            responseData = responseData.replace("HighOH", str(aohhum))
            responseData = responseData.replace("HOHTime", str(aohhumtime))
            responseData = responseData.replace("LowOH", str(aolhum))
            responseData = responseData.replace("LOHTime", str(aolhumtime))
            responseData = responseData.replace("HighIH", str(aihhum))
            responseData = responseData.replace("HIHTime", str(aihhumtime))
            responseData = responseData.replace("LowIH", str(ailhum))
            responseData = responseData.replace("LIHTime", str(ailhumtime))
            responseData = responseData.replace("HighBP", str(aohbmp))
            responseData = responseData.replace("HBPTime", str(aohbmptime))
            responseData = responseData.replace("LowBP", str(aolbmp))
            responseData = responseData.replace("LBPTime", str(aolbmptime))
            responseData = responseData.replace("HighWS", str(aohwind))
            responseData = responseData.replace("HWSTime", str(aohwindtime))
            responseData = responseData.replace("LowWS", str(aolwind))
            responseData = responseData.replace("LWSTime", str(aolwindtime))
            responseData = responseData.replace("LowWG", str(aolwindg))
            responseData = responseData.replace("LWGTime", str(aolwindgtime))
            responseData = responseData.replace("HighWG", str(aohwindg))
            responseData = responseData.replace("HWGTime", str(aohwindgtime))
            outgoingXMLData += BuildResponse.buildResponse(responseData)
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData


# AIL-1 - Activity Indicator - LIVE
    if (objectServerID == "AIL-1"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
	    #answ = "NO"
	    answ = "YES"
	    #answ = ""
	    if (Config.debug()):
		    print "In local AIL-1"
		    print("answ = %s" % answ)
        responseData = answ
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData

	# BTL-1 Bubble Table
	if (objectServerID == "BTL-1"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
       	if (validate == "YES"):
           	outgoingXMLData += Validate.buildValidateResponse("YES")
           	outgoingXMLData += BuildResponse.buildFooter()
           	return outgoingXMLData
    	if (Config.debug()):
    		print "In Local BTL-1"
   		time = strftime("%H:%M:%S", localtime())
		responseData =  time+as3935LastStatus+"\n"+"Lighting Count="+str(int(as3935LightningCount))
    	if (Config.debug()):
			print "responseData =", responseData
       	outgoingXMLData += BuildResponse.buildResponse(responseData)
  		outgoingXMLData += BuildResponse.buildFooter()
       	return outgoingXMLData

# BR-1 - Power Left in Battery
    if (objectServerID == "BR-1"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
		answ = str(batteryCharge)
		#answ = ""
		if (Config.debug()):
			print "In local BR-1"
			print("answ = %s" % answ)
		responseData = answ
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData

# LT-5 - Power efficiency
    if (objectServerID == "LT-5"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
		powerefficiency = (loadCurrent*loadVoltage/(batteryCurrent*batteryVoltage+solarCurrent*solarVoltage))*100
		if (powerefficiency < 0.0): #Must be plugged in so add 500mA@5V
			powerefficiency = (loadCurrent*loadVoltage/(batteryCurrent*batteryVoltage+solarCurrent*solarVoltage+5.0*500.0))*100
		pefloat = "%3.1f%%" % powerefficiency
		answ = str(pefloat)
		#answ = ""
		if (Config.debug()):
			print "In local LT-5"
			print("answ = %s%" % answ)
		responseData = answ
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData

# LT-4 - Server Present - Power From Battery
    if (objectServerID == "LT-4"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
		answ = "%0.0f mA/%0.2f W" % (batteryCurrent, batteryPower)
		#answ = ""
		if (Config.debug()):
			print "In local LT-4"
			print("answ = %s" % answ)
		responseData = answ
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData


# LT-2 - Server Present - Power From Solar Cells
    if (objectServerID == "LT-2"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
		answ = "%0.0f mA/%0.2f W" % (solarCurrent, solarPower)
		#answ = ""
		if (Config.debug()):
			print "In local LT-2"
			print("answ = %s" % answ)
		responseData = answ
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData

# LT-3 - Server Present - Power Into Pi
    if (objectServerID == "LT-3"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
		answ = "%0.0f mA/%0.2f W" % (loadCurrent, loadPower)
		#answ = ""
		if (Config.debug()):
			print "In local LT-3"
			print("answ = %s" % answ)
		responseData = answ
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData

# LT-1 Percentage Battery Left
	if (objectServerID == "LT-1"):
#check for validation request
#This allows the RasPiConnect program to verify this object is here
		if (validate == "YES"):
			outgoingXMLData += Validate.buildValidateResponse("YES")
			outgoingXMLData += BuildResponse.buildFooter()
			return outgoingXMLData
# normal response requested
		percent = returnBatteryPercentage(batteryVoltage, 4.10)
		bsize = 6600 #mAh size of battery
		mampleft = bsize *(percent/100)
		answ = "%i%%/~%imAh" % (percent, int(mampleft))
		responseData = answ
		outgoingXMLData += BuildResponse.buildResponse(responseData)
		outgoingXMLData += BuildResponse.buildFooter()
		return outgoingXMLData

# W-4 Highs and Lows
    if (objectServerID == "W-4"):
#check for validation request
#This allows the RasPiConnect program to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
		try:
			print ("trying database")
			db = mdb.connect('localhost', 'root', config.MySQL_Password, 'Weatherpi');
			cur = db.cursor()
			query = 'SELECT TimeStamp, outsideTemperature FROM WeatherData WHERE DATE_ADD(CURDATE( ) , INTERVAL - 4 HOUR) < TIMESTAMP ORDER BY outsideTemperature ASC LIMIT 1'
			cur.execute(query)
			result = cur.fetchone()
			doltemptime = result[0]
			doltemp = result[1]
			query = 'SELECT TimeStamp, outsideTemperature FROM WeatherData WHERE DATE_ADD(CURDATE( ) , INTERVAL - 4 HOUR) < TIMESTAMP ORDER BY outsideTemperature DESC LIMIT 1'
            cur.execute(query)
            result = cur.fetchone()
            dohtemptime = result[0]
            dohtemp = result[1]
			query = 'SELECT TimeStamp, insideTemperature FROM WeatherData WHERE DATE_ADD(CURDATE( ) , INTERVAL - 4 HOUR) < TIMESTAMP ORDER BY insideTemperature ASC LIMIT 1'
            cur.execute(query)
            result = cur.fetchone()
            diltemptime = result[0]
            diltemp = result[1]
			query = 'SELECT TimeStamp, insideTemperature FROM WeatherData WHERE DATE_ADD(CURDATE( ) , INTERVAL - 4 HOUR) < TIMESTAMP ORDER BY insideTemperature DESC LIMIT 1'
            cur.execute(query)
            result = cur.fetchone()
            dihtemptime = result[0]
            dihtemp = result[1]
#Humidity
			query = 'SELECT TimeStamp, outsideHumidity FROM WeatherData WHERE DATE_ADD(CURDATE( ) , INTERVAL - 4 HOUR) < TIMESTAMP ORDER BY outsideHumidity ASC LIMIT 1'
            cur.execute(query)
            result = cur.fetchone()
            dolhumtime = result[0]
            dolhum = result[1]
            query = 'SELECT TimeStamp, outsideHumidity FROM WeatherData WHERE DATE_ADD(CURDATE( ) , INTERVAL - 4 HOUR) < TIMESTAMP ORDER BY outsideHumidity DESC LIMIT 1'
            cur.execute(query)
            result = cur.fetchone()
            dohhumtime = result[0]
            dohhum = result[1]
            query = 'SELECT TimeStamp, insideHumidity FROM WeatherData WHERE DATE_ADD(CURDATE( ) , INTERVAL - 4 HOUR) < TIMESTAMP ORDER BY insideHumidity ASC LIMIT 1'
            cur.execute(query)
            result = cur.fetchone()
            dilhumtime = result[0]
            dilhum = result[1]
            query = 'SELECT TimeStamp, insideHumidity FROM WeatherData WHERE DATE_ADD(CURDATE( ) , INTERVAL - 4 HOUR) < TIMESTAMP ORDER BY insideHumidity DESC LIMIT 1'
            cur.execute(query)
            result = cur.fetchone()
            dihhumtime = result[0]
            dihhum = result[1]
#Wind
			query = 'SELECT TimeStamp, currentWindSpeed FROM WeatherData WHERE DATE_ADD(CURDATE( ) , INTERVAL - 4 HOUR) < TIMESTAMP ORDER BY currentWindSpeed ASC LIMIT 1'
            cur.execute(query)
            result = cur.fetchone()
            dolwindtime = result[0]
            dolwind = result[1]
            query = 'SELECT TimeStamp, currentWindSpeed FROM WeatherData WHERE DATE_ADD(CURDATE( ) , INTERVAL - 4 HOUR) < TIMESTAMP ORDER BY currentWindSpeed DESC LIMIT 1'
            cur.execute(query)
            result = cur.fetchone()
            dohwindtime = result[0]
            dohwind = result[1]
			query = 'SELECT TimeStamp, currentWindGust FROM WeatherData WHERE DATE_ADD(CURDATE( ) , INTERVAL - 4 HOUR) < TIMESTAMP ORDER BY currentWindGust ASC LIMIT 1'
            cur.execute(query)
            result = cur.fetchone()
            dolwindgtime = result[0]
            dolwindg = result[1]
            query = 'SELECT TimeStamp, currentWindGust FROM WeatherData WHERE DATE_ADD(CURDATE( ) , INTERVAL - 4 HOUR) < TIMESTAMP ORDER BY currentWindGust DESC LIMIT 1'
            cur.execute(query)
            result = cur.fetchone()
            dohwindgtime = result[0]
            dohwindg = result[1]
#BMP
			query = 'SELECT TimeStamp, bmp180SeaLevel FROM WeatherData WHERE DATE_ADD(CURDATE( ) , INTERVAL - 4 HOUR) < TIMESTAMP ORDER BY bmp180SeaLevel ASC LIMIT 1'
            cur.execute(query)
            result = cur.fetchone()
            dolbmptime = result[0]
            dolbmp = result[1] * 10
            query = 'SELECT TimeStamp, bmp180SeaLevel FROM WeatherData WHERE DATE_ADD(CURDATE( ) , INTERVAL - 4 HOUR) < TIMESTAMP ORDER BY bmp180SeaLevel DESC LIMIT 1'
            cur.execute(query)
            result = cur.fetchone()
            dohbmptime = result[0]
            dohbmp = result[1] * 10
		except mdb.Error, e:
			print "Error %d: %s" % (e.args[0],e.args[1])
		finally:
			print ("finished")
			cur.close()
			db.close()
			del cur
			del db

        responseData = ""
		with open ("./Templates/W-909.html", "r") as myfile:
			responseData += myfile.read().replace('\n', '')
		title = "Daily High and Lows - SummerGlen GC Ocala, FL"
		responseData = responseData.replace("Vartitle", title)
		# now replace our variables in the template with the actual data
		responseData = responseData.replace("HighOT", str(dohtemp))
		responseData = responseData.replace("HOTTime", str(dohtemptime))
		responseData = responseData.replace("LowOT", str(doltemp))
		responseData = responseData.replace("LOTTime", str(doltemptime))
		responseData = responseData.replace("HighIT", str(dihtemp))
		responseData = responseData.replace("HITTime", str(dihtemptime))
		responseData = responseData.replace("LowIT", str(diltemp))
		responseData = responseData.replace("LITTime", str(diltemptime))
		responseData = responseData.replace("HighOH", str(dohhum))
		responseData = responseData.replace("HOHTime", str(dohhumtime))
		responseData = responseData.replace("LowOH", str(dolhum))
		responseData = responseData.replace("LOHTime", str(dolhumtime))
		responseData = responseData.replace("HighIH", str(dihhum))
		responseData = responseData.replace("HIHTime", str(dihhumtime))
		responseData = responseData.replace("LowIH", str(dilhum))
		responseData = responseData.replace("LIHTime", str(dilhumtime))
		responseData = responseData.replace("HighBP", str(dohbmp))
		responseData = responseData.replace("HBPTime", str(dohbmptime))
		responseData = responseData.replace("LowBP", str(dolbmp))
		responseData = responseData.replace("LBPTime", str(dolbmptime))
		responseData = responseData.replace("HighWS", str(dohwind))
		responseData = responseData.replace("HWSTime", str(dohwindtime))
		responseData = responseData.replace("LowWS", str(dolwind))
		responseData = responseData.replace("LWSTime", str(dolwindtime))
		responseData = responseData.replace("LowWG", str(dolwindg))
        responseData = responseData.replace("LWGTime", str(dolwindgtime))
		responseData = responseData.replace("HighWG", str(dohwindg))
        responseData = responseData.replace("HWGTime", str(dohwindgtime))
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData


# DLU-3 - Wind Speed Text
    if (objectServerID == "DLU-3"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
		answ = "Wind Speed: %0.2f MPH" % currentWindSpeed
		#answ = ""
		if (Config.debug()):
			print "In local DLU-3"
			print("answ = %s" % answ)
		responseData = answ
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData

# DLU-4 - Wind Gust
    if (objectServerID == "DLU-4"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
		answ = "Wind Gust: %0.2f MPH" % currentWindGust
		#answ = ""
		if (Config.debug()):
			print "In local DLU-4"
			print("answ = %s" % answ)
		responseData = answ
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData

# DLU-5 - Outside Temperature
    if (objectServerID == "DLU-5"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
		answ = "Outside Temperature: %0.2f C" % outsideTemperature
		#answ = ""
		if (Config.debug()):
			print "In local DLU-5"
			print("answ = %s" % answ)
		responseData = answ
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData

# DLU-6 - Outside Humidity
    if (objectServerID == "DLU-6"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
		answ = "Outside Humidity: %0.2f %%" % outsideHumidity
		#answ = ""
		if (Config.debug()):
			print "In local DLU-6"
			print("answ = %s" % answ)
		responseData = answ
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData

# DLU-7 - Barometric Pressure
    if (objectServerID == "DLU-7"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
		answ = "Barometric Pressure: %0.2f mbar" % (bmp180SeaLevel * 10)
		#answ = ""
		if (Config.debug()):
			print "In local DLU-7"
			print("answ = %s" % answ)
		responseData = answ
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData

# DLU-8 - Inside Temperature
    if (objectServerID == "DLU-8"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
		if (Config.debug()):
			print "In local DLU-8"
		responseData = "Inside Temperature: %0.2f C" % bmp180Temperature
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData


# DLU-9 - Rain Total
    if (objectServerID == "DLU-9"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
		if (Config.debug()):
			print "In local DLU-9"
		responseData = "Rain Total: %0.2f In" % totalRain
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData

# DLU-10 - Wind Direction
    if (objectServerID == "DLU-10"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
		if (Config.debug()):
			print "In local DLU-10"
		responseData = "Wind Direction: %0.2f deg" % currentWindDirection
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData

# DLU-11 - Inside Humidity
    if (objectServerID == "DLU-11"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
		if (Config.debug()):
			print "In local DLU-11"
		responseData = "Inside Humidity: %0.2f %%" % insideHumidity
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData

# M-4 - Wind Speed
    if (objectServerID == "M-4"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
		#answ = "%0.2f" % currentWindSpeed
        answ = str(currentWindSpeed)
		#answ = ""
		if (Config.debug()):
			print "In local M-4"
			print("answ = %s" % answ)
		responseData = answ
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData

# M-5 - Inside Humidty
    if (objectServerID == "M-5"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
            answ = str(insideHumidity)
            if (Config.debug()):
                print "In local M-5"
                print("answ = %s %%" % answ)
            responseData = answ
            outgoingXMLData += BuildResponse.buildResponse(responseData)
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData

# M-6 - Inside Temperature
    if (objectServerID == "M-6"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
        answ = str(insideTemperature)
        if (Config.debug()):
            print "In local M-6"
            print("answ = %s %%" % answ)
        responseData = answ
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData

# M-7 - Outside Humidty
    if (objectServerID == "M-7"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
        answ = str(outsideHumidity)
        if (Config.debug()):
            print "In local M-7"
            print("answ = %s %%" % answ)
        responseData = answ
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData

# M-8 - Outside Temperature
    if (objectServerID == "M-8"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
            answ = str(outsideTemperature)
            if (Config.debug()):
                print "In local M-8"
                print("answ = %s %%" % answ)
            responseData = answ
            outgoingXMLData += BuildResponse.buildResponse(responseData)
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData

# M-9 - Wind Gusts
    if (objectServerID == "M-9"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
        answ = str(currentWindGust)
        if (Config.debug()):
            print "In local M-9"
            print("answ = %s" % answ)
        responseData = answ
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData

# M-10 - Barometric Pressure
    if (objectServerID == "M-10"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
        barpres = "%0.2f" % (bmp180SeaLevel *10)
		answ = str(barpres)
        if (Config.debug()):
            print "In local M-10"
            print("answ = %s" % answ)
        responseData = answ
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData

# M-1 - Pi Voltage
	if (objectServerID == "M-1"):
# check for validation request
# allows RasPiConnect app verify this object exits
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
        answ = str(loadVoltage)
        if (Config.debug()):
            print "In local M-1"
            print("answ = %s" % answ)
        responseData = answ
        outgoingXMLData += BuildResponse.buildResponse(responseData)
		outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData

# M-2 - Solar Voltage
    if (objectServerID == "M-2"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
		answ = str(solarVoltage)
		#answ = ""
		if (Config.debug()):
			print "In local M-2"
			print("answ = %s" % answ)
		responseData = answ
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData

# M-3 - Battery Voltage
    if (objectServerID == "M-3"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
        if (validate == "YES"):
            outgoingXMLData += Validate.buildValidateResponse("YES")
            outgoingXMLData += BuildResponse.buildFooter()
            return outgoingXMLData
# normal response requested
	    answ = str(batteryVoltage)
	    #answ = ""
	    if (Config.debug()):
		    print "In local M-3"
		    print("answ = %s" % answ)
	    responseData = answ
        outgoingXMLData += BuildResponse.buildResponse(responseData)
        outgoingXMLData += BuildResponse.buildFooter()
        return outgoingXMLData

# SLGL-1 Simple Line Graph - LIVE
	if (objectServerID == "SLGL-1"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
       	if (validate == "YES"):
           	outgoingXMLData += Validate.buildValidateResponse("YES")
           	outgoingXMLData += BuildResponse.buildFooter()
           	return outgoingXMLData
    	if (Config.debug()):
    		print "In Local SLGL-1"
		import random
		#answer = random.randrange(0,100,1)
		answer = "68672.000000^^17457.000000^^16954.000000^^723.000000^^10874.000000^^10367.000000^^59561.000000^^56276.000000^^6379.000000^^40763.000000||"
		responseData = answer
    	if (Config.debug()):
			print "responseData =", responseData
       	outgoingXMLData += BuildResponse.buildResponse(responseData)
  		outgoingXMLData += BuildResponse.buildFooter()
       	return outgoingXMLData

	# SLGL-2 Simple Line Graph - LIVE
	if (objectServerID == "SLGL-2"):
#check for validate request
# validate allows RasPiConnect to verify this object is here
       	if (validate == "YES"):
           	outgoingXMLData += Validate.buildValidateResponse("YES")
           	outgoingXMLData += BuildResponse.buildFooter()
           	return outgoingXMLData
    	if (Config.debug()):
    		print "In Local SLGL-2"
		import random
		#answer = random.randrange(0,100,1)
		answer = "68672.000000^^17457.000000^^16954.000000^^723.000000^^10874.000000^^10367.000000^^59561.000000^^56276.000000^^6379.000000^^40763.000000||"
		responseData = answer
    	if (Config.debug()):
			print "responseData =", responseData
       	outgoingXMLData += BuildResponse.buildResponse(responseData)
  		outgoingXMLData += BuildResponse.buildFooter()
      	return outgoingXMLData
# returning a zero length string tells the server that you have not matched
# the object and server
	return ""

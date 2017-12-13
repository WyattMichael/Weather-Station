#
# Do graph stuff - says Schatzie(c)

import sys
sys.path.append('/home/pi/SDL_Pi_GroveWeatherPi/graphs')

# Check for user imports
try:
        import conflocal as config
except ImportError:
        import config


import TemperatureHumidityGraph 
import PowerCurrentGraph 
import PowerVoltageGraph 
import BarometerLightningGraph
import SystemStatsGraph
import WindGraph 

def doAllGraphs():
    if (config.enable_MySQL_Logging == True):	
        BarometerLightningGraph.BarometerLightningGraph('SGWpi', 10, 0)
        TemperatureHumidityGraph.TemperatureHumidityGraph('SGWpi', 10, 0)
        PowerCurrentGraph.PowerCurrentGraph('SGWpi', 10, 0)
        PowerVoltageGraph.PowerVoltageGraph('SGWpi', 10, 0)
        SystemStatsGraph.SystemStatsGraph('SGWpi', 10, 0)
        WindGraph.WindGraph('SGWpi', 10, 0)



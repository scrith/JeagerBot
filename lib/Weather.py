#!/usr/bin/python
# coding: utf-8

import pytz
import logging
import geocoder
import requests
from sys import exc_info
from traceback import print_tb
from datetime import datetime

# Openweathermap
# API spec https://openweathermap.org/api/one-call-api

# weather object for 
class Weather(object):
    SYNTAX = "\"weather (location) [+hourly] [+forecast|+daily]\""

    #icons array defined at end because it is long
    def __init__(self, geocoder_apikey, forecast_apikey):
        self.Log = logging.getLogger('Main.Weather')
        self.Log.info("Initializing Weather")
        self.gmt_tz = pytz.timezone("GMT")
        self.report_tz = self.gmt_tz
        self.report = []
        self.hourly = False
        self.daily = False
        self.geocoder_apikey = geocoder_apikey
        self.forecast_apikey = forecast_apikey
        self.base_url = "https://api.openweathermap.org/data/2.5/onecall"
    #end __init__
    
    def _get_geocode_(self,location):

        result = geocoder.osm(location)
        if (len(result) == 0):
            self.Log.error("No data returned from geocoder")
            return None
        else:
            return result.raw
    #end _get_geocode_
    
    def _append_hourly_(self,forecast):
        self.Log.debug("Appending hourly forecast")
        # Add on hourly temperature outputs
        try:
            report_timezone = pytz.timezone(forecast['timezone'])
            now_plus_hourly = []
            now_plus_hourly.append("")

            for hour in range(5):
                # Skip the first line
                hour+=1
                local_time = datetime.fromtimestamp(forecast['hourly'][hour]['dt'],report_timezone)

                hourly_time = "%5.5s" %(local_time.strftime("%-I:%p"))
                hourly_temp = "%-5.5s" %("%.0f°C" %(forecast['hourly'][hour]['temp']))
                hourly_type = forecast['hourly'][hour]['weather'][0]['main']
                hourly_desc = forecast['hourly'][hour]['weather'][0]['description']
                
                if (hourly_type == 'Rain') | (hourly_type == 'Snow'):
                    precipitation = forecast['hourly'][hour]['pop']
                    if precipitation != 0:
                        probability = int(precipitation*10)
                        if probability == 0:
                            graph = " "
                            graph = "[%-10.10s]" %(graph * 10)
                        else:
                            graph = "▓" * (probability) + "░" * (10 - probability)
                            graph = "[%-10.10s]" %(graph)
                        hourly_desc = "%s%%%s" %(hourly_type,graph)
                hourly_forecast = " |%s %s %s" %(hourly_time,hourly_temp,hourly_desc)
                now_plus_hourly.append(hourly_forecast)
                
            # end hourly forecast loop
            for i in range(6):
                self.report[i] = self.report[i] + now_plus_hourly[i]
        except Exception:
            self.Log.error("Error adding hourly forecasts")
            typ, value, tb = exc_info()
            self.Log.error(typ)
            self.Log.error(value)
            self.Log.error(tb)
            self.Log.error(print_tb(tb))
            del typ, value, tb
        finally:
            del now_plus_hourly
    # end _append_hourly_

    def _append_daily_(self,forecast):
        try: # add on daily forecasts
            now_plus_daily = []
            now_plus_daily.append("")
            report_timezone = pytz.timezone(forecast['timezone'])

            for day in range(6):
                day += 1 #skip the first day
                local_day = datetime.fromtimestamp(forecast['daily'][day]['dt'],report_timezone)
                display_day = local_day.strftime("%a")
                temp_min = forecast['daily'][day]['temp']['min']
                temp_max = forecast['daily'][day]['temp']['max']
                day_summary = forecast['daily'][day]['weather'][0]['description']

                day_forecast = " | %-3.3s (%.0f°/%.0f°) %s" %(display_day,temp_max,temp_min,day_summary)
                now_plus_daily.append(day_forecast)
            # end daily forecast loop
        except Exception:
            self.Log.error("Error adding daily forecasts")
            typ, value, tb = exc_info()
            self.Log.error(typ)
            self.Log.error(value)
            self.Log.error(tb)
            self.Log.error(print_tb(tb))
            del typ, value, tb
        finally:
            for i in range(6):
                self.report[i] = self.report[i] + now_plus_daily[i]
            del now_plus_daily
    # end _append_daily

    def process_input(self,msg):
        self.Log.debug("Processing input for weather request")
        words = msg.split()
        i = words.index("weather")
        self.hourly = False
        self.daily = False
        if (len(words) >= (i+2)):
            location = " ".join(words[i+1:])
            if (location.find("+") != -1):
                #modifiers found
                words = location.split()
                for word in words:
                    if (word == "+hourly"):
                        self.Log.debug("Found hourly forecast modifier")
                        self.hourly = True
                        location = location.replace("+hourly","")
                    elif (word == "+daily") or (word == "+forecast"):
                        self.Log.debug("Found daily forecast modifier")
                        self.daily = True
                        location = location.replace("+forecast","")
                        location = location.replace("+daily","")
                    elif (word.find("+") != -1):
                        self.Log.debug("Found bad modifier %s" %(word))
                        return ["Unknown modifier \"%s\".  Syntax is %s" %(word, self.SYNTAX)]
            # end modifier check
                
            self.geo = self._get_geocode_(location)
            if self.geo == None:
                return ["Geocoder error, no location returned for query"]
            
            ## input parsing complete, create report
            self.create_report(location)
            return self.report
        
        else: # not enough words in the command
            return ["Empty location. Syntax is %s" %(Weather.SYNTAX)]
    # end process_input


    def create_report(self,location):
        self.Log.debug("Checking weather for '"+location+"'")
        #cardinals = ['N','NE','E','SE','S','SW','W','NW']
        cardinals = [u'↑',u'↗',u'→',u'↘',u'↓',u'↙',u'←',u'↖']
        try:
            # blank out the weather report
            self.report = []
            desc = ""
            temp = ""
            precip = ""
            wind = ""
            viz = ""
            #detect and remove modifiers
            
            lat = float(self.geo['lat'])
            lon = float(self.geo['lon'])
            address = "%s" %(self.geo['display_name'])
            
            geolocation = address+" ("+str(lat)+","+str(lon)+")"
            self.Log.debug("Location returned is %s" %geolocation)
            
            request_url = "%s?lat=%s&lon=%s&appid=%s&units=metric&lan=en" %(self.base_url,str(lat),str(lon),self.forecast_apikey)
            self.Log.debug(request_url)
            forecast = requests.get(request_url).json()
            current = forecast['current']

            icon = current['weather'][0]['icon']
            self.Log.debug("Icon code returned is %s" %icon)
            if (icon in self.icons):
                pict = self.icons[icon]
            else:
                pict = self.icons['unknown']

#            # craft the forecast elements
############ Name of place
            try:
                desc = "\x02%-20.20s\x0f" %(current['weather'][0]['description'],)
            except:
                desc = " "

############ Temperature right now
            try: # temperature (right now)
                temp = current['temp']
                feels_like = current['feels_like']
                temp = "%-20s" %("%.0f°C (feels %.0f°C)" %(temp, feels_like), )
            except AttributeError:
                temp = "%-20s" %(" ",)

############ Precipitation for this hour
            try:
                precipitation = forecast['hourly'][0]['pop']
                if precipitation > 0:
                    if 'Rain' in current:
                        type = "rain"
                        precip = "%-20s" %("%.0f%% chance of %s" %((precipitation * 100), type), )
                    elif 'Snow' in current:
                        type = "snow"
                        precip = "%-20s" %("%.0f%% chance of %s" %((precipitation * 100), type), )
                    else:
                        precip = "No precipitation"
                else:
                    precip = "No precipitation"
            except AttributeError:
                precip = "%-20s" %(" ",)

############ Windspeed and direction right now
            try:
                speed = current['wind_speed']
                bearing = current['wind_deg'] / 45
                compass = cardinals[int(bearing)]
                wind = "%-20s" %("%s %.0fm/s winds" %(compass,speed))
            except AttributeError:
                wind = "%-20s" %(" ",)

############ Visibility right now
            try: # visibility needs failsafe
                visibility = int(current['visibility'])/1000
                if visibility == 10000:
                    viz = "Clear"
                else:
                    viz = "%-20s" %("View %.1f km" %(visibility, ), )
            except AttributeError:
                viz = "%-20s" %(" ",)

############ UV index right now
            try:
                uvindex = int(current['uvi'])
                uvi = "%-20s" %("UV Index %i" %(uvindex, ), )
            except AttributeError:
                uvi = "%-20s" %(" ",)              
            
            # start with the 5 line pictogram for 'currently'
            report_timezone = pytz.timezone(forecast['timezone'])
            local_time = datetime.fromtimestamp(forecast['current']['dt'],report_timezone)

            # append current conditions summary to end of each line
            self.report.append("%s %s" %(local_time.strftime("%-I:%p"),address))
            self.report.append(pict[0]+"| "+desc)
            self.report.append(pict[1]+"| "+temp)
            self.report.append(pict[2]+"| "+uvi)
            self.report.append(pict[3]+"| "+wind)
            self.report.append(pict[4]+"| "+viz)
            
            if (self.hourly): self._append_hourly_(forecast)
            if (self.daily):  self._append_daily_(forecast)

            return self.report
        except Exception:
            self.Log.error("Something has gone very wrong with the weather")
            typ, value, tb = exc_info()
            self.Log.error(typ)
            self.Log.error(value)
            self.Log.error(tb)
            self.Log.error(print_tb(tb))
            del typ, value, tb
            self.report = None
    #end create_report

    icons = { 
        'unknown': [
            "   ______    ",
            "  |_|  | |   ",
            "     __|_|   ",
            "    |_|      ",
            "     o       ",
        ],
        #clear day
        '01d': [
            "    \   /    ",
            "     .~.     ",
            " -- (   ) -- ",
            "     `~´     ",
            "    /   \    ",
        ],
        #clear night
        '01n': [
            "#############",
            "#/‾‾‾\#######",
            "# O   #######",
            "#\___/#######",
            "#############",
        ],
        #few clouds day
        '02d': [
            "  \   /      ",
            "   .~.       ",
            "--(  .--.    ",
            "  .-(    ).  ",
            " (___.__)__) ",
        ],
        #few clouds night
        '02n': [
            "#/‾‾‾\#######",
            "# O  .**%####",
            "#\.-(    )###",
            "#(___.__)__)#",
            "#############" 
        ],
        #scattered clouds day
        '03d': [
            "  .-.        ",
            " (   )--.    ",
            "( .-(    ).  ",
            " (___.__)__) ",
            "             ",
        ],
        #scattered clouds night
        '03n': [
            "###-#########",
            "#(   )--#####",
            "( .-(    )###",
            "#(___.__)__)#",
            "#############",
        ],
        #broken clouds day
        '04d': [
            "    .-.      ",
            "   (   )--.  ",
            "  ( .-(    ).",
            " (___.__)___)",
            "             ",
        ],
        #broken clouds night
        '04n': [
            "#####-#######",
            "###(   )--###",
            "##( .-(    )#",
            "#(___.__)___)",
            "#############",
        ],
        #shower rain
        '09d': [
            "     .--.    ",
            "  .-(    ).  ",
            " (___.__)__) ",
            "  °   °   °  ",
            "  °   °   °  ",
        ],
        #shower rain night
        '09d': [
            "######--#####",
            "###-(    )###",
            "#(___.__)__)#",
            "  °   °   °  ",
            "  °   °   °  ",
        ],
        #rain
        '10d': [
            "     .--.    ",
            "  .-(    ).  ",
            " (___.__)__) ",
            "  ° ° ° ° °  ",
            "  ° ° ° ° °  ",
        ],
        #rain
        '10n': [
            "######--#####",
            "###-(    )###",
            "#(___.__)__)#",
            "  ° ° ° ° °  ",
            "  ° ° ° ° °  ",
        ],
        #thunderstorm
        '11d': [
            "     .--.    ",
            "  .-(    ).  ",
            " (___.__)__) ",
            "  ° //°// °  ",
            "  °/  °/  °  ",
        ],
        #thunderstorm
        '11n': [
            "######--#####",
            "###-(    )###",
            "#(___.__)__)#",
            "  ° //°// °  ",
            "  °/  °/  °  ",
        ],
        #snow
        '13d': [
            "     .--.    ",
            "  .-(    ).  ",
            " (___.__)__) ",
            "   ❄  ❄  ❄   ",
            "   ❄  ❄  ❄   ",
        ],
        #snow
        '13n': [
            "######--#####",
            "###-(    )###",
            "#(___.__)__)#",
            "   ❄  ❄  ❄   ",
            "   ❄  ❄  ❄   ",
        ],
        #atmosphere
        '50d': [
            "---._..--.__.",
            "::.-. _..--.:",
            ":(...)--....)",
            "(:.-(::::).-:",
            ";(;;;.;;);;);"
        ],
        '50n': [
            "---._..--.__.",
            "::.-. _..--.:",
            ":(...)--....)",
            "(:.-(::::).-:",
            ";(;;;.;;);;);"
        ],
        #old icons
        'sleet': [
            "     .--.    ",
            "  .-(    ).  ",
            " (___.__)__) ",
            "  ° ❄ ° ❄ °  ",
            "  ❄ ° ❄ ° ❄  ",
        ],
        'wind': [
            "             ",
            "'-.,_,.='``'-",
            ".,_,.-'``'-.,",
            "_,.-'``'-.,_,",
            "             ",
        ]
    }#icon dict

# end Weather


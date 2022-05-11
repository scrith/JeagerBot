#!/usr/bin/python
# coding: utf-8

import sys
import json
import time
import timeit
import logging
import threading
from sys import exc_info
from sys import exit
from traceback import print_tb

sys.path.append("./lib/")
from Weather import Weather
from Jaeger import Jaeger
from Dictionary import Dictionary
from Errors import *

####################################################
#               Build object classes               #
####################################################
start_time = timeit.default_timer()
GipsyDanger = Jaeger()

Server = GipsyDanger.get_IRC_Connection()
MP = GipsyDanger.get_MessageParser()
KDB = GipsyDanger.get_KarmaDatabase()
Config = GipsyDanger.get_Config()

Weather = Weather( 
    Config.get("Weather","geocoder_apikey"),
    Config.get("Weather","forecast_apikey")
    )

Dictionary = Dictionary()

Log = logging.getLogger("Main.Listener")

operator_name = GipsyDanger.get_pilot()
jaeger_name = GipsyDanger.get_name()
with open(Config.get("Common", "help_file")) as data_file:    
    usage_help = json.load(data_file)

execution_time = timeit.default_timer() - start_time
Log.info("Jaeger startup in %.3f seconds" %(execution_time))
####################################################
#                 helper functions                 #
####################################################
def get_help():
    Log.debug("Accessing help")
    words = MP.body.split()
    help_output = []
    i = words.index("help")
    if (len(words) >= (i+2)): #cardinal
        help_topic = words[i+1] #ordinal
        Log.debug("checking for help topic %s" %(help_topic))
        if (help_topic in usage_help):
            help_output = usage_help[help_topic]
        else:
            help_output = ["Unknown topic"]
    else:
        Log.debug("No help topic supplied")
        help_topic = None
        topics = []
        help_output.append("No topic supplied. Use format of %s help [topic].  Available topics are:" %(jaeger_name))
        for key,value in usage_help.items():
            topics.append(key)
        help_output.append(", ".join(topics))

    return help_output
####################################################
# Watch IRC chat for key values and run functions  #
####################################################    
handshake=0
while handshake == 0:
    chunk=Server.receive(4096)
    if chunk.find("End of /MOTD command") != -1:
        handshake = 1
del handshake
running=True
while running:
    try:
        chunk = Server.receive(8192)
        chunks = chunk.splitlines()
        for message in chunks:
            start_time = timeit.default_timer()
            MP.parse(message)
            
            if (MP.failed == True): 
                raise JaegerMessageParseError("JaegerMessageParseError","failure")
            
            Server.set_audience(MP.get_response_channel())
            
            if (MP.command.find("PING") != -1):  Server.pong(MP.body)### Keep bot ONLINE
            
            operator = (MP.nick == operator_name)
        
            if (MP.action == "PRIVMSG"):
                # only bother going through PRIVMSG here
                if (MP.private or MP.direct):
                    if (MP.karma):  threading.Thread(KDB.process_karma(MP,Server)).start()
                    Log.debug("Message is private or directed")
                    Log.debug(MP.body)
                    if (MP.body.startswith(">>")):
                        Log.debug("Message begins with command character")
                        Server.set_audience(MP.get_response_channel())
                        if (operator):
                            Log.debug("Command message from pilot confirmed, sending to processing")
                            # Handle the restart command here for now
                            if (MP.body == ">>reboot"):
                                running = False
                                continue
                            # Handle all the rest of the commands inside the bot class
                            GipsyDanger.process_pilot_command()
                        else:
                            Log.debug("Command message is not from pilot, rejecting")
                            Server.set_audience(MP.nick)
                            Server.send_message("Only the Jaeger pilot may issue commands. Please contact %s" %(GipsyDanger.get_pilot()))
                    elif (MP.body.find("help"    )!=-1):  Server.send_blurb(get_help())
                    elif (MP.body.find("status"  )!=-1):  threading.Thread(target=GipsyDanger.status ).start()
                    elif (MP.body.find("channels")!=-1):  threading.Thread(target=GipsyDanger.list_connected_channels ).start()
                    elif (MP.body.find("botsnack")!=-1):  threading.Thread(target=GipsyDanger.bot_snack ).start()
                    elif (MP.body.find("score"   )!=-1):  threading.Thread(target=GipsyDanger.score ).start()
                    elif (MP.body.find("rank"    )!=-1):  threading.Thread(target=GipsyDanger.rank ).start()
                    elif (MP.body.find("search"  )!=-1):  threading.Thread(target=GipsyDanger.search ).start()
                    elif (MP.body.find("top"     )!=-1):  threading.Thread(target=GipsyDanger.top ).start()
                    elif (MP.body.find("bottom"  )!=-1):  threading.Thread(target=GipsyDanger.bottom ).start()
                    elif (MP.body.find(" versus ")!=-1):  threading.Thread(target=GipsyDanger.versus ).start()
                    elif (MP.body.find(" vs "    )!=-1):  threading.Thread(target=GipsyDanger.versus ).start()
                    elif (MP.body.find("define"  )!=-1):  Server.send_blurb(Dictionary.process_input(MP.body))
                    elif (MP.body.find("weather" )!=-1):  Server.send_blurb(Weather.process_input(MP.body))
                    else:
                        Log.debug("Message unmatched")
                        if MP.karma == False:
                            if (len(MP.body.split()) > 5):
                                GipsyDanger.shrug("hmm.")
                            else:
                                GipsyDanger.shrug()
                # if private|direct
            # if PRIVMSG
            execution_time = timeit.default_timer() - start_time
            Log.debug("Loop execution time %.3f" %(execution_time))
        # for loop
    except JaegerMessageParseError:
        Log.error("Messaging parsing failed on [[%s]]" %(message))
        #running = true;
    except:
        Log.error("Exception caught during main listener loop")
        typ, value, tb = exc_info()
        Log.error(typ)
        Log.error(value)
        Log.error(print_tb(tb))
        del typ, value, tb, message

# while

Server.close()
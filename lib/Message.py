#!/usr/bin/python
# coding: utf-8

import logging
import re
from Errors import *

class MessageParser(object):
    def __init__(self,jaeger_name):
        self.Log = logging.getLogger("Main.Message")
        self.Log.debug("Creating MessageParser object")
        self.name = jaeger_name
    #end __init__

    def _set_karma_recipients_(self):
        self.karmatargets = []
        # split the message into words
        words = self.body.split()
        # scan each word for karma modifiers
        for w in words:
            # if an empty modifier is present skip it
            if len(w) > 2 and (w.endswith("++") or w.endswith("--")):
                self.karmatargets.append(w)
        # if there are valid targets set flag
        if len(self.karmatargets) > 0:

            self.Log.debug("Found %i recipients" %(len(self.karmatargets)))
            self.karma=True
        else:
            self.karma=False
    #end _set_karma_recipients_
    def _set_response_channel_(self):
        if (self.audience.find("#") != -1):
            self.response_channel = self.audience
        elif (self.action == "JOIN"):
            self.response_channel = self.body
            self.body = ""
        else:
            self.response_channel = self.nick
        self.Log.debug("Setting response channel to %s" %(self.response_channel))
    # end _set_response_channel_
    def _post_process_(self):
        self.Log.debug("Post processing of message")
        if (self.body.find("++") != -1) or (self.body.find("--") != -1):
            self.Log.debug("Karma modifiers found, sending to post-processing")
            self._set_karma_recipients_()
        ## Commands are expected to be prefixed with the botname unless talking directly to bot
        ## also we totally ignore any messages from the bot itself
        self.private = (self.audience == self.name)
        self.direct = (self.body.startswith(self.name))
            
        if (self.direct):
            self.body = self.body.replace(self.name,"",1)
            self.body = self.body.lstrip(":,-").strip()
    # end _post_process_
    
    def _reset_values_(self):
        self.command=""
        self.response_code=""
        self.response_args=[]
        self.user=""
        self.nick=""
        self.location=""
        self.address=""
        self.action=""
        self.audience=""
        self.body=""
        self.karma=False
        self.response_channel=""
        self.private=False
        self.direct=False
        self.failed=False
        self.server_response=False
        self.karmatargets = []

    def _dump_values_(self):
        log_message = "raw=%s\n\
command=%s\n\
response_code=%s\n\
response_args=%s\n\
user=%s\n\
nick=%s\n\
location=%s\n\
address=%s\n\
action=%s\n\
audience=%s\n\
body=%s" %(self.raw,\
           self.command,\
           self.response_code,\
           ",".join(self.response_args),\
           self.user,\
           self.nick,\
           self.location,\
           self.address,\
           self.action,\
           self.audience,\
           self.body)
        self.Log.debug(log_message)
    
    def parse_server(self, parsed):
        if (len(parsed) >= 1): part1 = parsed[0]
        if (len(parsed) >= 2): part2 = parsed[1]
        if (len(parsed) >= 3):
            part3 = ":".join(parsed[2:]) # message body with spaces
            self.body = part3

        part2a = part2.split()
        if (len(part2a) >= 1):
            self.response_code = part2a[1]
        if (len(part2a) > 2):
            self.response_args = part2a[2:]
        self.server_response = True
        return
        # numeric codes listed https://www.alien.net.au/irc/irc2numerics.html

    def parse(self, text):
        self.Log.debug(text.replace("\n",""))
        self._reset_values_()
        self.raw = text

        try:
            #command arg1 arg2 :arg3 with spaces :arg4 with spaces :arg5
            #:phillip!phillip@ovpn-117-76.phx2.redhat.com PRIVMSG GipsyD :#join #foundry2
            parsed = re.split(" *:",text)
            # part1 = command arg1 arg2
            # part2 = nick!location@ip action target
            # part3 = message body
            # part4 = (ignored)
            if (len(parsed) == 0):
                self._reset_values_()
                self.failed = True
                return

            ## PART 1 - SERVER COMMANDS
            if (len(parsed) >= 1):
                part1 = parsed[0] #command arg1 arg2
                if (part1.find(" ") != -1):
                    part1a = part1.split()
                    self.command = part1a[0]
                    if (len(part1a) > 1):
                        self.command_args = " ".join(part1a[1:])
                else:
                    self.command = part1

            ## PART 2 - ACTION IDENTITY
            if (len(parsed) >= 2):
                part2 = parsed[1]
                if (part2.find(" ") != -1):
                    part2a = part2.split()
                    #nick!location@ip , action , target
                    #server , int , [args]
                    if (len(part2a) >= 1):
                        self.user = part2a[0]
                        if (self.user.find("!") != -1):
                            part2ab = self.user.split("!")
                            self.nick = part2ab[0]
                            self.location = part2ab[1]
                            if (self.location.find("@") != -1):
                                part2c = self.location.split("@")
                                self.address = part2c[-1]
                        else:
                            self._reset_values_()
                            self.parse_server(parsed)
                            self._dump_values_()
                            return
                            
                    if (len(part2a) >= 2):
                        self.action = part2a[1]
                    if (len(part2a) >= 3):
                        self.audience = part2a[2]
                
            ## PART 3 - MESSAGE BODY
            if (len(parsed) >= 3):
                part3 = ":".join(parsed[2:]) # message body with spaces
                self.body = part3
                
            ## PART 4 - (IGNORED)
             
            self._set_response_channel_()
    
            if (self.nick == self.name): #never post-process bot responses
                self._reset_values_()
                return
            else:
                self._post_process_()

            ## TRACE level logging
            self._dump_values_()

        except:
            self._reset_values_()
            self.failed = True
            return

    #end parse
    
    def get_response_channel(self):
        return self.response_channel

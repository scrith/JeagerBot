#!/usr/bin/python
# coding: utf-8
import time
import socket
import logging
from sys import exc_info
from traceback import print_tb
from Errors import *

class IRC_Connection(object):
    
    def __init__(self,server,port,botnick,botname):
        port = int(port)
        self.Log = logging.getLogger('Main.IRC')
        self.irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.irc.connect((server, port))
        op = "USER "+ botnick +" "+ botnick +" "+ botnick +" :"+botname+"\n"
        self.irc.send(str.encode(op))
        op = "NICK "+ botnick +"\n"
        self.irc.send(str.encode(op))
        self.Log.info(u'Connected to '+server+u' as '+botnick)
        self.activity = ""
    # __init__
    
    def _send_(self, action, message):
        try:
            activity = "%s %s :%s\n" %(action,self.audience,message)
            self.Log.debug("Sending message: %s" %(activity.replace("\n","")))
            self.irc.send(str.encode(activity))
            # always include a short sleep after each send to prevent flood blocking
            time.sleep(.25)
            return True
        except:
            self.Log.error("Error sending message '%s'" %(message))
            typ, value, tb = exc_info()
            self.Log.error(typ)
            self.Log.error(value)
            self.Log.error(tb)
            self.Log.error(print_tb(tb))
            del typ, value, tb
            return False
    #end _send_

    def close(self):
        self.irc.close()

    def set_audience(self,response_channel):
        self.audience = response_channel

    def join(self,channel):
        op = "JOIN %s\n" %(channel)
        self.irc.send(str.encode(op))
        self.Log.info(u'Joining %s channel' %(channel))

    def leave(self,channel):
        op = "PART %s\n" %(channel)
        self.irc.send(str.encode(op))
        self.Log.info(u'Leaving %s channel' %(channel))

    def receive(self,size):
        chunk = ""
        more = True
        i=0
        while (more):
            # This loop should catch those large quick blocks of data from the server
            # and pass them along without incorrect breaks in the datastream
            chunk = chunk + self.irc.recv(size).decode('utf8')
            if chunk.endswith("\n"):
                more = False
            else:
                self.Log.warning("Fetch size %s too small for received data, fetching more." %(size))
                i=+1
                if (i > 10):
                    more=False
                    self.Log.error("Fetch attempted 10 times sequentially, failing.")
                    chunk=""
                
        return chunk
    
    def pong(self,body):
        self.set_audience("")
        self._send_("PONG",body)
    
    def notify(self,audience,message):
        self.set_audience(audience)
        self._send_(u'NOTICE',message)

    def send_action(self,action):
        action = chr(1)+"ACTION "+action+chr(1)
        self._send_(u'PRIVMSG',action)

    def send_message(self,message):
        self._send_(u'PRIVMSG',message)

    def send_blurb(self,blurb):
        if (blurb != None):
            for line in blurb:
                self.send_message(line)
                time.sleep(.1)
        else:
            self.send_message("Something went wrong")
## class IRC_Connection
#!/usr/bin/python
# coding: utf-8

import time
import socket
import string
import random
import logging
import logging.handlers

class Minions(object):
    def __init__(self):
        self.Log = logging.getLogger("Minion")
        self.Log.info("Hatching Minions")
        self.server = "irc.devel.redhat.com"
        self.port = 6667
        self.wordlist = open("resources/words").read().splitlines()
        self.tickles = string.ascii_lowercase

    def rally(self,audience,command):
        self.Log.debug("stirring up crows")
        handshake = 0
        nick = ""
        giggle = ""
        random.seed(time.time())
        for i in range(3):
            random_char = random.choice(self.tickles)
            giggle = giggle + random_char
        while len(nick) < 4:
            nick = random.choice(self.wordlist)
        if random.random() > .7:
            nick = nick + "|" +giggle
        else:
            nick = nick + "-" + giggle
        self.Log.debug("nick=",nick)
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection.connect((self.server, self.port))
        connection.send(("USER "+ nick +" "+ nick +" "+ nick +" :Banana!\n").encode("utf8"))
        connection.send(("NICK "+ nick +"\n").encode("utf8"))
        while handshake == 0:
            text=connection.recv(1024).decode("utf8")
            if text.find("End of /MOTD command") != -1:
                handshake = 1
            if text.find("PING") != -1:
                connection.send(("PONG "+text.split()[1]+"\r\n").encode("utf8"))
        op = ("JOIN %s\n" %(audience)).encode("utf8")
        connection.send(op)
        msg=("PRIVMSG "+audience+" :"+command+"\n").encode("utf8")
        connection.send(msg)
        connection.close()

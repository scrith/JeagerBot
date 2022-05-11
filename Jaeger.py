#!/usr/bin/python
# coding: utf-8

import json
import time
import random
import logging.handlers
import configparser
import random
import threading
import sqlite3
from _sqlite3 import OperationalError

from sys import argv
from IRC import IRC_Connection
from Message import MessageParser
from Minions import Minions
from Karma import KarmaDatabase
from Errors import *

class Jaeger(object):
    VERSION = "5.0.1"
    CONFIG = "./Jaeger.cfg"
    
    def __init__(self):
        self.Config = configparser.ConfigParser(interpolation=None)
        self.Config.read(self.CONFIG)
        config_section="Production" # Default to the production configs
        if len(argv) > 1:
            args = argv[1:]
            if args[0] == "dev":
                config_section = "Development"
        # finished setting config section
        self.Log = logging.getLogger("Main")
        self.log_level = self.Config.get(config_section, "log_level")
        self.Log.setLevel(self.log_level)
        fh = logging.handlers.RotatingFileHandler(self.Config.get("Common","log_file"), maxBytes=(1024*1024*50), backupCount=5, encoding='utf8')
        formatter = logging.Formatter("%(asctime)s[%(name)-12s]%(levelname)s: %(message)s", "%m-%d-%y %H:%M:%S")
        fh.setFormatter(formatter)
        self.Log.addHandler(fh)
        self.Log.info("Initializing Jaeger")
        self.Log.debug("Configuration Profile set to %s" %(config_section))
        
        self.Log.debug("Reading config properties")
        self.name = self.Config.get(config_section, "jaeger_name")
        self.pilot = self.Config.get(config_section, "operator_name")
        self.irc_server = self.Config.get("Common", "irc_server")
        self.irc_port = self.Config.get("Common", "irc_port")

        self.Log.debug("Creating additional objects")
        self.Server = IRC_Connection(self.irc_server, self.irc_port, self.name, "JaegerBot v%s" %(self.VERSION))
        self.MP = MessageParser(self.name)
        self.KDB = KarmaDatabase(self.name, self.pilot)
        self.Minion = Minions()

        self.Log.debug("Pulling in json response objects")
        with open(self.Config.get("Common","botsnack_response_file")) as data_file:
            data = json.load(data_file)
            self.botsnack_responses = data["responses"] 

        self.Log.info("JaegerBot v%s online." %(self.VERSION))
        self.Server.notify(self.pilot, "%s v%s Online" %(self.name,self.VERSION))
        self.boot_time = time.time()
        del config_section, fh, formatter, data

        self.Log.info("Initializing Channels database")
        # open database
        self.db = sqlite3.connect("resources/channels.db", check_same_thread=False)
        self.cursor = self.db.cursor()
        # initalize database
        try:
            self.cursor.execute("SELECT COUNT(*) FROM channels")
            self.Log.info("%i channels saved" %(self.cursor.fetchone()[0]))
        except OperationalError:
            # Assuming no database on exception
            self.__create_database__()

        self.Log.info("Joining previously connected channels")
        #join previously connected channels
        try:
            for row in self.cursor.execute("SELECT * FROM channels"):
                channel = row[0]
                self.Server.join(channel)
        except OperationalError:
            # Assuming no database on exception
            self.__create_database__()
    #end __init__

    def __create_database__(self):
        # code for creating a new blank database
        self.Log.debug("Creating new database")
        # then the channel list
        self.cursor.execute("CREATE TABLE channels (name)")
        self.cursor.execute("INSERT INTO channels VALUES ('#foundry')")
        # commit the changes
        self.db.commit()
        pass
    #end __create_database__

    def _suppress_(self):
        self.Log.debug("Calling for suppression")
        self.MP.body = self.MP.body.replace(">>suppress","",1)
        self.Server.set_audience(self.MP.nick)
        words = self.MP.body.split()
        if (len(words) >= 2): #one is cardinal and one is ordinal
            recipient = words[0]
            reply = " ".join(words[1:])
            state = self.KDB.suppress(self.MP.nick, recipient, reply)
            if state:
                self.Server.set_audience(self.MP.get_response_channel())
                self.Server.send_message("Successfully suppressed "+recipient)
            else:
                self.Server.set_audience(self.MP.get_response_channel())
                self.Server.send_message("Unknown failure!")
        else:
            self.Server.set_audience(self.MP.get_response_channel())
            self.Server.send_message("syntax is '>>suppress [nick] [reason for suppression]'")
    # end _suppress_
    def _unsuppress_(self):
        self.Log.debug("Calling for suppression removal")
        words = self.MP.body.split()
        i = words.index(">>unsuppress")
        if (len(words) > (i+1)):
            recipient = words[1]
            requestor = self.MP.nick
            if (self.KDB.unsuppress(requestor, recipient)):
                self.Server.send_message("Removal of %s succeeded" %(recipient))
            else:
                self.Server.send_message("Failed to remove %s" %(recipient))
        else:
            self.Server.send_message("syntax is >>unsuppress [nick]")
    # end _unsuppress_
    def _list_suppressed_(self):
        self.Log.debug("Pilot requesting suppressed nicks")
        suppressed = self.KDB.get_suppressed() #returns list of tuples
        namelist = []
        #suppressed is a list
        for entry in suppressed:
            #entry is a tuple
            nick,msg = entry
            namelist.append(nick)
        response = ", ".join(namelist)
        self.Server.send_message("Discarding karma from: %s" %(response))
    # end _list_suppressed_
    def _join_(self):
        #GipsyDanger >>join #foundry2
        self.Log.debug("Pilot requesting join of channel")
        words = self.MP.body.split()
        #['>>join', '#foundry2']
        i = words.index(">>join")
        #should be 0
        #channel name should be 1
        if (len(words) > (i+1)):
            # should only get here when there are 2+ words
            channel = words[i+1].lower()
            # get the word after >>join
            t = (channel,)
            self.cursor.execute("SELECT * FROM channels WHERE name = ?",t)
            check = self.cursor.fetchone()
            if check == None:
                self.cursor.execute("INSERT INTO channels VALUES (?)", t)
                # commit the changes
                self.db.commit()
                # join the channel
                self.Server.join(channel)
            else:
                self.shrug("I think I'm already connected to that channel")
        else:
            self.Server.set_audience(self.MP.get_response_channel())
            self.Server.send_message("Please specify a channel to join")
    # end _join_

    def _leave_(self):
        #GipsyDanger >>join #foundry2
        self.Log.debug("Pilot requesting join of channel")
        words = self.MP.body.split()
        #['>>leave', '#foundry2']
        i = words.index(">>leave")
        #should be 0
        #channel name should be 1
        if (len(words) > (i+1)):
            # should only get here when there are 2+ words
            channel = words[i+1]
            # get the word after >>leave
            t = (channel,)
            self.cursor.execute("SELECT * FROM channels WHERE name = ?", t)
            check = self.cursor.fetchone()
            if check == None:
                # nothing in channel database
                self.shrug("I don't think I am connected to that channel.")
            else:
                # entry found
                self.cursor.execute("DELETE FROM channels WHERE name = ?", t)
                self.db.commit()
                self.Server.leave(channel)
        else:
            self.Server.set_audience(self.MP.get_response_channel())
            self.Server.send_message("Please specify a channel to leave")
    # end _leave_
    def _boost_(self):
        # GipsyDanger >>boost bojangles 2
        self.Log.debug("Charging karma boost")
        words = self.MP.body.split()
        if (len(words) == (3)):
            target = words[1]
            power = int(words[2])
            if (len(target) < 2):
                self.Server.set_audience(self.MP.get_response_channel())
                self.shrug("Need at least 2 characters")
                return 
            if (power > 10):
                self.Server.send_message("! Overheat")
                power = 10
            elif (power <= 0):
                self.Server.send_message("! Collapse")
                return
            command = target + "++"
            channel = self.MP.get_response_channel()
            self.Log.debug("channel %s, command %s, power %i" %(channel,command,power))
            for poke in range(power):
                threading.Thread(target=self.Minion.rally, args=[channel,command] ).start()
                time.sleep(random.random())
        else:
            self.shrug()
            return
    # end _boost_

    def _smash_(self):
        # GipsyDanger >>smash bojangles 2
        self.Log.debug("Charging karma smash")
        words = self.MP.body.split()
        if (len(words) == (3)):
            target = words[1]
            power = int(words[2])
            if (len(target) < 2):
                self.Server.set_audience(self.MP.get_response_channel())
                self.shrug("Need at least 2 characters")
                return 
            if (power >= 10):
                self.Server.send_message("! Overheat")
                power = 10
            elif (power <= 0):
                self.Server.send_message("! Collapse")
                return
            command = target + "--"
            channel = self.MP.get_response_channel()
            self.Log.debug("channel %s, command %s, power %i" %(channel,command,power))
            for poke in range(power):
                threading.Thread(target=self.Minion.rally, args=[channel,command] ).start()
                time.sleep(2+random.random())
        else:
            self.shrug()
            return
    # end _boost_

    def get_IRC_Connection(self): return self.Server
    def get_KarmaDatabase(self):  return self.KDB
    def get_MessageParser(self):  return self.MP
    def get_Config(self):         return self.Config
    def get_pilot(self):          return self.pilot
    def get_name(self):           return self.name

    def process_pilot_command(self):
        self.Log.debug("Processing pilot command input %s" %(self.MP.body))
        if   (self.MP.body.startswith(">>suppress")):    self._suppress_()
        elif (self.MP.body.startswith(">>discarded")):   self._list_suppressed_()
        elif (self.MP.body.startswith(">>unsuppress")):  self._unsuppress_()
        elif (self.MP.body.startswith(">>join")):        self._join_()
        elif (self.MP.body.startswith(">>leave")):       self._leave_()
        elif (self.MP.body.startswith(">>savechannels")):self._save_channels_()
        elif (self.MP.body.startswith(">>boost")):       self._boost_()
        elif (self.MP.body.startswith(">>smash")):       self._smash_()
        else: self.shrug(); return False
    # end process_pilot_command
    def status(self):
        online_time = time.ctime(self.boot_time)
        nice,naughty,ratelimit = self.KDB.karma_status()
        status_message = "JaegerBot v%s online since %s. Keeping %s karma, ignoring %s, tracking %s ratelimits" \
            %(self.VERSION,online_time,nice, naughty, ratelimit)
        self.Server.set_audience(self.MP.get_response_channel())
        self.Server.send_message(status_message)
    # end _status_
    def list_connected_channels(self):
        list = []
        self.Log.debug("Pilot requesting channel presence")
        try:
            for row in self.cursor.execute("SELECT * FROM channels"):
                channel = row[0]
                list.append(channel)
            list.sort()
            channel_list = ", ".join(list)
            self.Server.send_message("Connected to: %s" %(channel_list))
        except OperationalError:
            return

    # end _list_connected_channels_
    def shrug(self,reason=""):
        self.Server.set_audience(self.MP.get_response_channel())
        self.Server.send_message("¯\_(ツ)_/¯ %s" %(reason))
    def bot_snack(self): ## Random response
        self.Log.debug("Responding to a bot snack")
        snack_response = random.choice(self.botsnack_responses)
        response_type = snack_response['type']
        response_value = snack_response['value']
        if response_type == 'msg':
            self.Server.set_audience(self.MP.get_response_channel())
            self.Server.send_message(response_value)
        elif response_type == 'act':
            if response_value.find("@USER") != -1:
                response_value = response_value.replace("@USER",self.MP.nick)
            self.Server.set_audience(self.MP.get_response_channel())
            self.Server.send_action(response_value)
        del snack_response, response_type, response_value
    #end bot_snack
    def score(self):
        self.Log.debug("Checking score from message:\n%s" %(self.MP.body))
        words = self.MP.body.split()
        i = words.index("score")
        if len(words) >= (i+2): #one is cardinal and one is ordinal
            inquiry = words[i+1]
            points = self.KDB.get_score(inquiry)
            if points == None:
                points = "None!"
            self.Server.set_audience(self.MP.get_response_channel())
            self.Server.send_message("%s: %s" %(inquiry,points))
        else:
            self.shrug("Who do you want to rank?")
    # end score
    def rank(self):
        self.Log.debug("Checking rank from message:\n%s" %(self.MP.body))
        words = self.MP.body.split()
        i = words.index("rank")
        if len(words) >= (i+2): #one is cardinal and one is ordinal
            inquiry = words[i+1]
            position = self.KDB.get_rank(inquiry)
            if position == 0:
                self.Server.set_audience(self.MP.get_response_channel())
                self.shrug("Who knows (no karma record)")
            else:
                self.Server.set_audience(self.MP.get_response_channel())
                self.Server.send_message("%s: #%s" %(inquiry, position))
        else:
            self.shrug("Who do you want to rank?")
    # end rank
    def versus(self):
        self.Log.debug("Matching up karma scores")
        self.MP.body = self.MP.body.replace(" vs "," versus ")
        words = self.MP.body.split()
        i = words.index("versus")
        if (len(words) >= (i+2) and (i>=1)): #one is cardinal and one is ordinal
            A = words[i-1]
            B = words[i+1]
            A_score = self.KDB.get_score(A)
            B_score = self.KDB.get_score(B)
            if (A_score == None) and (B_score == None):
                self.shrug("Never heard of them.")
                return True
            elif (A_score == None): #B wins
                winner = B
                topscore = B_score
                bottomscore = 0
            elif (B_score == None): #A wins
                winner = A
                topscore = A_score
                bottomscore = 0
            elif (A_score > B_score): #A wins
                winner = A
                topscore = A_score
                bottomscore = B_score
            elif (B_score > A_score): #B wins
                winner = B
                topscore = B_score
                bottomscore = A_score
            elif (A_score == B_score): #tie
                self.Server.send_message("All tied up at %i" %(A_score)) #tie
                return True
            self.Server.set_audience(self.MP.get_response_channel())
            self.Server.send_message("%s wins! %i to %i" %(winner, topscore, bottomscore))
    # end versus
    def top(self):
        self.Log.debug("Top scores")
        leaders = self.KDB.top_karma(5)
        top_scores = []
        i = 1
        for record in leaders:
            top_scores.append("#%i %s (%i)" %(i, record[0], record[1]))
            i+=1
        self.Server.set_audience(self.MP.get_response_channel())
        self.Server.send_blurb(top_scores)
        del leaders, top_scores, i
    # end top
    def bottom(self):
        self.Log.debug("Bottom scores")
        results = self.KDB.bottom_karma(5)
        laggers = results[0][::-1]
        bottom_scores = []
        i = results[1] - len(laggers)
        for record in laggers:
            i+=1
            bottom_scores.append("#%i %s (%i)" %(i, record[0], record[1]))
        self.Server.set_audience(self.MP.get_response_channel())
        self.Server.send_blurb(bottom_scores)
        del results, laggers, bottom_scores, i
    # end bottom
    def search(self):
        self.Log.debug("Searching for karma")
        words = self.MP.body.split()
        i = words.index("search")
        if (len(words) >= (i+2)):
            keyword = words[i+1]
            if (len(keyword) < 3):
                self.Server.set_audience(self.MP.get_response_channel())
                self.shrug("Need at least 3 characters")
                return 
            search_phrase = "%" + keyword + "%"
            results = self.KDB.search_karma(search_phrase)
            if (len(results) > 6): # don't spam the channel
                self.Server.set_audience(self.MP.nick)
                self.Server.send_message("%s: Large result set, sending privately" %(self.MP.nick))
            if (len(results) == 0):
                self.shrug("Couldn't find anything")
            else:
                for record in results:
                    name = record[0]
                    points = record[1]
                    self.Server.set_audience(self.MP.get_response_channel())
                    self.Server.send_message("%s (%i)" %(name, points))
    # end search


# end Jaeger class
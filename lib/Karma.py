#!/usr/bin/python
# coding: utf-8
import sys
import json
import time
import random
import sqlite3
import logging
from _sqlite3 import OperationalError
from sys import exc_info
from traceback import print_tb

class KarmaDatabase(object):
        
    def __init__(self,jaeger,pilot):
        self.Log = logging.getLogger("Main.Karma")
        self.Log.info("Initializing KarmaDatabase object")
        # set variables
        self.ratelimit = 600 # 10 minutes 

        self.jaeger_name = jaeger
        self.pilot_name = pilot
        # open database
        self.db = sqlite3.connect("resources/karma.db", check_same_thread=False)
        self.cursor = self.db.cursor()
        # initalize database
        try:
            self.cursor.execute("SELECT COUNT(*) FROM scores")
            self.Log.info("%i score records available" %(self.cursor.fetchone()[0]))

            self.cursor.execute("SELECT COUNT(*) FROM actions")
            self.Log.info("%i actions logged" %(self.cursor.fetchone()[0]))

            self.cursor.execute("SELECT COUNT(*) FROM disallowed")
            self.Log.info("%i recipients disallowed" %(self.cursor.fetchone()[0]))
        except OperationalError:
            # Assuming no database on exception
            self.__create_database__()
        self.nextclean = 0
        self._clean_actions_table_()
    #end __init__
    
    def __create_database__(self):
        # code for creating a new blank database
        self.Log.debug("Creating new database")
        # Next the action log
        self.cursor.execute("CREATE TABLE actions (user_nick, user_location, recipient, time_allowed)")
        # Then the disallowed table
        self.cursor.execute("CREATE TABLE disallowed (name, message)")
        self.cursor.execute("INSERT INTO disallowed VALUES ('trump','Sometimes things are better left unsaid.')")
        # do the scores table last so that everything else gets created
        self.cursor.execute("CREATE TABLE scores (name, points)")
        t = [(self.jaeger_name.lower(),0)]
        self.cursor.executemany("INSERT INTO scores VALUES (?,?)",t)
        if len(sys.argv) > 1:
            args = sys.argv[1:]
            if args[0] == "dev":
                t = [("whale",9),
                     ("kitten",19),
                     ("bunny",29),
                     ("1up",99),
                     ("2up",199),
                     ("1down",-99),
                     ("2down",-199),
                     ("tux",499),
                     ("pane",-499),
                     ("shadow",999),
                     ("double",1999),
                     ("facepalm",-999)]
                self.cursor.executemany("INSERT INTO scores VALUES (?,?)",t)
        # commit the changes
        self.db.commit()
        pass
    #end __create_database__
    
    def _have_control_authority_(self,nick):
        self.Log.debug("Checking if user has authority")
        # a security check for operator actions
        if nick.lower() == self.pilot_name.lower():
            # return true as passing condition
            return True
        else:
            # return false for other users
            return False
    #end _have_control_authority_ 
    
    def _is_suppressed_(self,recipient):
        self.Log.debug("Checking for suppression of %s" %(recipient))
        # silently discard polarizing entries
        t = (recipient.lower(),)
        self.cursor.execute("SELECT * FROM disallowed WHERE name = ?",t)
        result = self.cursor.fetchone()
        if result == None:
            # return false as passing condition
            return (False,None)
        else:
            # return true for disallowed action
            self.Log.info("%s karma discarded" %(recipient))
            return (True,result[1])
    #end _is_suppressed_
    
    def get_suppressed(self):
        self.Log.debug("Pulling suppressed entries")
        # silently discard polarizing entries
        self.cursor.execute("SELECT * FROM disallowed")
        result = self.cursor.fetchall()
        return result
    #end _get_suppressed_
    
    def _clean_actions_table_(self):
        now = time.time()
        if now > self.nextclean:
            self.Log.info("Cleaning old entries from action table")
            # TABLE actions (user_nick, user_location, recipient, time_allowed)")
            now = int(time.time())
            t = (now,)
            self.cursor.execute("DELETE FROM actions WHERE time_allowed < ?",t)
            self.db.commit()
            if (self.cursor.rowcount > 0):
                self.Log.debug("%i rows deleted" %(self.cursor.rowcount))
            # schedule the next run
            self.nextclean = time.time() + (self.ratelimit)
        del now
        return False
    #end _clean_actions_table
    
    def _is_over_ratelimit_(self,nick,location,recipient):
        self._clean_actions_table_()
        # TABLE actions (user_nick, user_location, recipient, time_allowed)")
        self.Log.debug("Checking %s request from %s against ratelimit for %s" %(nick, location, recipient))
        # check nick and location for ratelimit on karma entry
        t = (recipient.lower(), nick.lower(), location, time.time())
        self.cursor.execute("SELECT COUNT(*) FROM actions WHERE recipient = ? AND (user_nick = ? OR user_location = ?) AND time_allowed > ?",t)
        # checking both the user nick and location for abuse
        count  = self.cursor.fetchone()[0]
        if count == 0:
            # return false as passing condition
            return (0,0)
        else:
            # also check the user"s overall speed
            t = (nick.lower(), location, time.time())
            self.cursor.execute("SELECT COUNT(*) FROM actions WHERE (user_nick = ? OR user_location = ?) AND time_allowed > ?",t)
            count = self.cursor.fetchone()
            self.Log.debug("count = %i, ratelimite = %i" %(int(count[0]),self.ratelimit))
            if int(count[0]) > self.ratelimit:
                # averaging more than 1 karma per second
                return (-1,0)
            else:
                # return true if user is abusing karma
                return (1,0)
    #end _check_ratelimit_ 
    
    def _fetch_(self,recipient):
        self.Log.debug("Fetching record %s" %(recipient))
        # query for entry in database
        t = (recipient.lower(),)
        self.cursor.execute("SELECT * FROM scores WHERE name = ?",t)
        return self.cursor.fetchone()
        # return a tuple of the record or None 
    #end _fetch_

    def _insert_(self,recipient):
        self.Log.info("Creating new record for %s" %(recipient))
        t = (recipient.lower(),)
        self.cursor.execute("INSERT INTO scores VALUES (?,0)",t)
        # commit the changes
        self.db.commit()
    #end _insert_
    
    def _remove_(self,recipient):
        self.Log.debug("Removing record for %s" %(recipient))
        # delete an entry in the database
        # for use when karma reaches 0
        # or when something is suppressed
        try:
            t=(recipient.lower(),)
            self.cursor.execute("DELETE FROM scores WHERE name = ?",t)
            self.db.commit()
            return True
        except:
            return False
    #end _remove_
    
    def _log_action_(self,nick,location,recipient):
        # tweak the rate limit by +- 30 seconds for anti-spam scheduling
        antispamscheduler = random.randint(-30,30)
        self.Log.debug("Logging action: %s,%s,%s with ratelimit %i and random modifier %i" %(nick, location, recipient, self.ratelimit, antispamscheduler))
        # TABLE actions (user_nick, user_location, recipient, time_allowed)")
        t = (nick.lower(),location,recipient.lower(),int(time.time()+self.ratelimit+antispamscheduler))
        # save the time when they are next able to take the action
        self.cursor.execute("INSERT INTO actions VALUES (?,?,?,?)",t)
        self.db.commit()
    #end _log_action_

    def unsuppress(self,requestor,recipient):
        self.Log.debug("Trying to remove suppression of %s" %(recipient))
        if (self._have_control_authority_(requestor)):
            if (self._is_suppressed_(recipient)[0]):
                t = (recipient.lower(),)
                self.cursor.execute("DELETE FROM disallowed WHERE name = ?",t)
                self.db.commit()
                return True
            else:
                return False
        else:
            return False
    #end unsuppress
    
    def suppress(self,requestor,recipient,autoreply):
        self.Log.debug("Adding suppression of %s with autoreply:'%s'" %(recipient,autoreply))
        # check _have_control_authority_
        if (self._have_control_authority_(requestor)):
            if (self._is_suppressed_(recipient)[0]): # an entry already exists
                return True
            else:
                # add new nick to suppression list
                t = (recipient.lower(),autoreply)
                self.cursor.execute("INSERT INTO disallowed VALUES (?,?)",t)
                self.db.commit()
                # call _remove_
                self._remove_(recipient)
                return True
        else: # 
            return False
    #end suppress

    def search_karma(self,keyword):
        self.Log.debug("Searching karma for %s" %(keyword))
        t = (keyword,)
        self.cursor.execute("SELECT * FROM scores WHERE name LIKE ? ORDER BY points DESC",t)
        return self.cursor.fetchall()
    #end search_karma

    def get_score(self,recipient):
        self.Log.debug("Checking score of %s" %(recipient))
        result = self._fetch_(recipient)
        if result == None:
            return None
        else:
            return result[1]
    #end get_score
    
    def get_rank(self,recipient):
        self.Log.debug("Fetching rank of %s" %(recipient))
        t = (recipient.lower(),)
        self.cursor.execute("SELECT COUNT(1) FROM scores WHERE points >= (SELECT points FROM scores WHERE name = ?)",t)
        rank = self.cursor.fetchone()
        if rank == None:
            return 0;
        else:
            return rank[0]
    #end get_rank

    def top_karma(self,limit=5):
        self.Log.debug("Pulling top %i karma scores" %(limit))
        t = (limit,)
        self.cursor.execute("SELECT * FROM scores ORDER BY points DESC LIMIT ?",t)
        top_scores = self.cursor.fetchall()
        return top_scores
    #end top_karma

    def bottom_karma(self,limit=5):
        self.Log.debug("Pulling bottom %i karma scores" %(limit))
        t = (limit,)
        self.cursor.execute("SELECT * FROM scores ORDER BY points ASC LIMIT ?",t)
        scorelist = self.cursor.fetchall()
        self.cursor.execute("SELECT COUNT(*) FROM scores")
        last_place = self.cursor.fetchone()[0] 
        return (scorelist,last_place)
    #end top_karma
    
    def karma_up(self,recipient):
        self.Log.debug("Incrementing %s" %(recipient))
        result = self._fetch_(recipient)
        if result == None:
            self._insert_(recipient)
            result = self._fetch_(recipient)
        # increment karma points
        newkarma = result[1] + 1
        t = (newkarma, result[0])
        self.cursor.execute("UPDATE scores SET points = ? WHERE name = ?", t )
        self.db.commit()
        # save action for future ratelimit check
        # return new karma
        return newkarma
    #end karma_up
    
    def karma_down(self,recipient):
        self.Log.debug("Decrementing %s" %(recipient))
        result = self._fetch_(recipient)
        if result == None:
            self._insert_(recipient)
            result = self._fetch_(recipient)
        # decrement karma points
        newkarma = result[1] - 1
        t = (newkarma, result[0])
        self.cursor.execute("UPDATE scores SET points = ? WHERE name = ?", t )
        self.db.commit()
        # save action for future ratelimit check
        # return new karma
        return newkarma
    #end karma_down
    
    def karma_status(self):
        self.Log.debug("Collecting karma stats")
        self.cursor.execute("SELECT COUNT(*) FROM scores")
        total_karma_records = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT COUNT(*) FROM disallowed")
        total_ignored_records = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT COUNT(*) FROM actions")
        ratelimit_tracked = self.cursor.fetchone()[0]
        return (total_karma_records, total_ignored_records, ratelimit_tracked)
    #end karma_status
    
    def process_karma(self,MessageObject,ServerConnection):
        try:
            # extract user and recipients
            user_nick = MessageObject.nick
            user_loc = MessageObject.address
            recipient_list = MessageObject.karmatargets
            primary_audience = MessageObject.get_response_channel()
            ServerConnection.set_audience(primary_audience)
            if (user_nick == self.jaeger_name):
                # ignore own messages
                return True
            self.Log.debug("Processing karma from user message")
            # figure out where to send status replies to
            if (len(recipient_list) > 5):
                # send large updates privately
                ServerConnection.send_message("%s karma blast, GO!" %(MessageObject.nick))
                primary_audience = MessageObject.nick
            elif (MessageObject.audience == self.jaeger_name):
                # send direct karma privately
                primary_audience = MessageObject.nick
            else:
                # otherwise use the parsed audience
                primary_audience = MessageObject.get_response_channel()
    
            # loop through recipients
            for recipient in recipient_list:
                ServerConnection.set_audience(primary_audience)
                # Check polarity
                if recipient.endswith("++"):
                    positive = True
                elif recipient.endswith("--"):
                    positive = False
                # Strip modifiers
                recipient = recipient.rstrip("+-")
                
                self.Log.info("%s sent karma to %s" %(user_nick, recipient))
                if (user_nick.lower() == recipient.lower()) or (user_nick.lower().startswith(recipient.lower())):
                    self.Log.info("forcing self karma to --")
                    # self ++ karma not allowed
                    # reverse polarity to --
                    positive = False
                
                # check for disallowed
                disallowed = self._is_suppressed_(recipient)
                if disallowed[0]:
                    ServerConnection.send_message("%s karma discarded: %s" %(recipient, disallowed[1]))
                    continue
                
                # check _is_over_ratelimit_
                speedcheck = self._is_over_ratelimit_(user_nick, user_loc, recipient)
                if speedcheck[0] == 1:
                    # over rate limit for this nick
                    ServerConnection.set_audience(user_nick)
                    ServerConnection.send_message("Please wait longer before sending karma to %s" %(recipient))
                elif speedcheck[0] == -1:
                    # over rate limit overall
                    ServerConnection.set_audience(user_nick)
                    ServerConnection.send_message("Karma is good, but Spam belongs on a sandwich.  Please slow down.")
                    break
                elif speedcheck[0] == 0:
                    # if user is not over rate limit then proceeed
                    self._log_action_(user_nick, user_loc, recipient)
                    if positive:
                        newscore = self.karma_up(recipient)
                    else:
                        newscore = self.karma_down(recipient)
                    # check resulting score
                    if newscore == 0:
                        ServerConnection.send_message("Zero karma remaining. Erasing %s" %(recipient))
                        self._remove_(recipient)
                    else:
                        rank = self.get_rank(recipient)
                        ServerConnection.send_message("\x1F%s\x0F's karma is \x02%i\x0F (%i)" %(recipient,newscore,rank))
                        self._check_for_stamps_(newscore, recipient, MessageObject.audience, ServerConnection)
                            
        except:
            self.Log.error("Karma processing failed")
            typ, value, tb = exc_info()
            self.Log.error(typ)
            self.Log.error(value)
            self.Log.error(tb)
            self.Log.error(print_tb(tb))
            del typ, value, tb

    #end process_karma
    
    def _check_for_stamps_(self,score,recipient,audience,ServerConnection):
        if (audience == self.jaeger_name):
            # ignore stamps for karma given privately
            return False
        
        self.Log.debug("Checking for stamps on score %i" %(score))
        stamp_file = ""
        with open("resources/stamplist.json") as data_file:    
            stamplist = json.load(data_file)
        milestones = stamplist['==']
        positive_intervals = stamplist['%+']
        negative_intervals = stamplist['%-']

        ### Stamp Selector
        score_key = "%i" %(score)
        if (score_key in milestones):
            stamp_file = milestones[score_key]
        elif (score > 0):
            for value in positive_intervals.keys():
                if (score % int(value) == 0):
                    stamp_file = positive_intervals[value]
                    continue
        elif (score < 0):
            for value in negative_intervals.keys():
                if (score % int(value) == 0):
                    stamp_file = negative_intervals[value]
                    continue
        else:
            return False
 
        ### Stamp send
        if (len(stamp_file) > 0):
            with open(stamp_file, 'r') as data_file:
                stamp = data_file.read().splitlines()
                ServerConnection.set_audience(audience)
                ServerConnection.send_message("%s has earned a stamp!" %(recipient))
                ServerConnection.send_blurb(stamp)
                # also send karma stamps to the reciever
                # TODO not sure how to do this yet recipient may just be an idea, not a user
        else:
            return False
    #end _check_for_stamps_
    
## class Karma
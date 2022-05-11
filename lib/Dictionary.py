#!/usr/bin/python
# coding: utf-8

import logging
import requests

# Openweathermap
# API spec https://api.dictionaryapi.dev/api/v2/entries/en/

# dictionary object for 
class Dictionary(object):
    SYNTAX = "\"define [word]\""

    #icons array defined at end because it is long
    def __init__(self):
        self.Log = logging.getLogger('Main.Dictionary')
        self.Log.info("Initializing Dictionary")
        self.base_url = "https://api.dictionaryapi.dev/api/v2/entries/en/"
    #end __init__

    def process_input(self, msg):
        print(msg)
        self.Log.debug("Processing input for dictionary lookup")
        words = msg.split()
        i = words.index("define")
        if (len(words) >= 2):
            word = words[i+1]
            ## input parsing complete, create report
            return self.create_report(word)
        else: # not enough words in the command
            return ["No word provided. Syntax is %s" %(Dictionary.SYNTAX)]
    # end process_input

    def create_report(self,word):
        request_url = "%s%s" %(self.base_url,word)
        self.Log.debug(request_url)
        resultset = requests.get(request_url).json()
        self.Log.debug(resultset)
        if len(resultset) > 0:

            number_of_entries = len(resultset)
            # limit output
            if number_of_entries > 4: number_of_entries = 4

            individual_definitions = []
            # one line for each one

            for entry in range(number_of_entries):

                for meaning in resultset[entry]["meanings"]:
                    part_of_speech = meaning["partOfSpeech"]
                    meaning_line = []
                    for definition in meaning["definitions"]:
                        meaning_line.append(definition["definition"])

                    meaning_line = " ; ".join(meaning_line)
                    meaning_line = "(%s) %s" %(part_of_speech,meaning_line)
                # end for meanings
                
                definition_line = "\x02%s\x0f %s" %(word, meaning_line)
                individual_definitions.append(definition_line)
            # end of for number_of_entries
            
            return individual_definitions
        else:
            return ""    
    # end create_report
# end Dictionary


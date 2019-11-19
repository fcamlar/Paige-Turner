# Copyright 2019 Amazon.com, Inc. or its affiliates.  All Rights Reserved.
# 
# You may not use this file except in compliance with the terms and conditions 
# set forth in the accompanying LICENSE.TXT file.
#
# THESE MATERIALS ARE PROVIDED ON AN "AS IS" BASIS. AMAZON SPECIFICALLY DISCLAIMS, WITH 
# RESPECT TO THESE MATERIALS, ALL WARRANTIES, EXPRESS, IMPLIED, OR STATUTORY, INCLUDING 
# THE IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.

import time
import logging
import json
from enum import Enum
from agt import AlexaGadget
import tempfile
import pexpect
import threading

from ev3dev2.led import Leds
from ev3dev2.sound import Sound
from ev3dev2.motor import OUTPUT_A, OUTPUT_D, SpeedPercent, LargeMotor

# Set the logging level to INFO to see messages from AlexaGadget
logging.basicConfig(level=logging.INFO)

class EventName(Enum):
    """
    The list of custom event name sent from this gadget
    """
    READ = "Read"


class MindstormsGadget(AlexaGadget):
    """
    A Mindstorms gadget that can perform bi-directional interaction with an Alexa skill.
    """

    def __init__(self):
        """
        Performs Alexa Gadget initialization routines and ev3dev resource allocation.
        """
        super().__init__()

        # Motors for the page turning.
        self.page_starter = LargeMotor(OUTPUT_A)
        self.page_turner = LargeMotor(OUTPUT_D)

        self.sound = Sound()
        self.leds = Leds()
        
        self._read_cmd = False

        # Start thread for sending Alexa messages
        threading.Thread(target=self._send_msg_thread, daemon=True).start()

    def on_connected(self, device_addr):
        """
        Gadget connected to the paired Echo device.
        :param device_addr: the address of the device we connected to
        """
        self.leds.set_color("LEFT", "GREEN")
        self.leds.set_color("RIGHT", "GREEN")
        print("{} connected to Echo device".format(self.friendly_name))

    def on_disconnected(self, device_addr):
        """
        Gadget disconnected from the paired Echo device.
        :param device_addr: the address of the device we disconnected from
        """
        self.leds.set_color("LEFT", "BLACK")
        self.leds.set_color("RIGHT", "BLACK")
        print("{} disconnected from Echo device".format(self.friendly_name))

    def _send_event(self, name: EventName, payload):
        """
        Sends a custom event to trigger a sentry action.
        :param name: the name of the custom event
        :param payload: the sentry JSON payload
        """
        self.send_custom_event('Custom.Mindstorms.Gadget', name.value, payload)

    def _send_msg_thread(self):
        """
        Waits until a read command is sent from the Alexa device and then reads
        a page out of the book.
        """
        count = 0
        while True:
            if self._read_cmd:
                # Read text from the picture
                text = self._get_text_from_image()

                clean_text = text.replace('\n', ' ').replace('\r', ' ')
                #.replace("'", " ").replace('"', ' ').replace('\\u2022', ' ')
                sentences = self._split_into_word_sets(json.dumps(clean_text))

                for sentence in sentences:
                    sentence = sentence.replace('\\u2022', ' ').replace('\\u00a9', ' ')
                    print(sentence)
                    self._send_event(EventName.READ, {'text': sentence})
                    time.sleep(8)
                
                self._read_cmd = False
            # Wait
            time.sleep(1)

    def _ssh(self, host, cmd, user, password, timeout=30, bg_run=False):                                                                                                 
        """SSH'es to a host using the supplied credentials and executes a command.                                                                                                 
        Throws an exception if the command doesn't return 0.                                                                                                                       
        bgrun: run command in the background"""                                                                                                                                    

        fname = tempfile.mktemp()                                                                                                                                                  
        fout = open(fname, 'wb')                                                                                                                                                    

        options = '-q -oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null -oPubkeyAuthentication=no'                                                                         
        if bg_run:                                                                                                                                                         
            options += ' -f'                                                                                                                                                       
        ssh_cmd = 'ssh %s@%s %s "%s"' % (user, host, options, cmd)                                                                                                              
        child = pexpect.spawn(ssh_cmd, timeout=timeout)                                                                                                                            
        child.expect(['password: '])                                                                                                                                                                                                                                                                                               
        child.sendline(password)                                                                                                                                                                                                                                                                                                     
        child.expect(pexpect.EOF)
        stdout = child.before                                                                                                                                        
        child.close()                                                                                                                                                                                                                                                                                                                                                                                                                                                                       

        return stdout.decode("utf-8") 

    def _get_text_from_image(self):
        """Enter the correct credentials here"""
        host = '192.168.50.31'
        cd = 'python3 gocr.py'
        user = 'parallels'
        psw = 'password'

        text = self._ssh(host, cd, user, psw, timeout=30, bg_run=False)

        return text


    def _chunk_word_array(self, words, n):
        """Yield successive n-sized chunks from l."""
        for i in range(0, len(words), n):
            yield words[i:i + n]

    def _combine_word_array(self, words):
        """Combine the words into sentences."""
        sentences = []
        for word_group in words:
            sentences.append(' '.join(word_group))
        
        return sentences

    def _split_into_word_sets(self, text):
        """Split into words"""
        words = text.split()
        num_words = len(words)
        groups = self._chunk_word_array(words, 120)
        sentences = self._combine_word_array(groups)

        return sentences
        

    def on_custom_mindstorms_gadget_control(self, directive):
        """
        Handles the Custom.Mindstorms.Gadget control directive.
        :param directive: the custom directive with the matching namespace and name
        """
        try:
            payload = json.loads(directive.payload.decode("utf-8"))
            print("Control payload: {}".format(payload))
            control_type = payload["type"]
            if control_type == "turn":

                # Scrunch the page and turn the page.
                self.page_starter.on_for_rotations(SpeedPercent(20), -0.47)
                self.page_turner.on_for_rotations(SpeedPercent(30), 1)

            if control_type == "read":
                # Set variable so the read thread will send messages.
                self._read_cmd = True

        except KeyError:
            print("Missing expected parameters: {}".format(directive))
    

if __name__ == '__main__':
    # Startup sequence
    gadget = MindstormsGadget()
    gadget.sound.play_song((('C4', 'e'), ('D4', 'e'), ('E5', 'q')))
    gadget.leds.set_color("LEFT", "GREEN")
    gadget.leds.set_color("RIGHT", "GREEN")

    # Gadget main entry point
    gadget.main()

    # Shutdown sequence
    gadget.sound.play_song((('E5', 'e'), ('C4', 'e')))
    gadget.leds.set_color("LEFT", "BLACK")
    gadget.leds.set_color("RIGHT", "BLACK")

# The MIT License (MIT)	
# 
# Copyright (c) 2016 Ethan Ward
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from os.path import dirname, join
import subprocess
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

__author__ = 'eward'

LOGGER = getLogger(__name__)


class PianobarSkill(MycroftSkill):

    def __init__(self):
        super(PianobarSkill, self).__init__(name="PianobarSkill")
        self.process = None

    def initialize(self):
        self.load_data_files(dirname(__file__))

        play_pandora_intent = IntentBuilder("PlayPandoraIntent").\
            require("PlayKeyword").require("PandoraKeyword").build()
        self.register_intent(play_pandora_intent,
                             self.handle_play_pandora_intent)

        next_song_intent = IntentBuilder("PandoraNextIntent"). \
            require("NextKeyword").build()
        self.register_intent(next_song_intent, self.handle_next_song_intent)

        pause_song_intent = IntentBuilder("PandoraPauseIntent"). \
            require("PauseKeyword").build()
        self.register_intent(pause_song_intent, self.handle_pause_song_intent)

        resume_song_intent = IntentBuilder("PandoraResumeIntent"). \
            require("ResumeKeyword").build()
        self.register_intent(resume_song_intent, self.handle_resume_song_intent)

    def handle_play_pandora_intent(self, message):
        self.process = subprocess.Popen(["pianobar"], stdin = subprocess.PIPE)

    def handle_next_song_intent(self, message):
        if self.process is not None:
            self.process.stdin.write("n")
        else:
            self.speak("Pandora is not playing")

    def handle_pause_song_intent(self, message):
        if self.process is not None:
            self.process.stdin.write("S")
        else:
            self.speak("Pandora is not playing")

    def handle_resume_song_intent(self, message):
        if self.process is not None:
            self.process.stdin.write("P")
        else:
            self.speak("Pandora is not playing")

    def stop(self):
        if self.process:  
            self.process.terminate()
            self.process.wait()


def create_skill():
    return PianobarSkill()

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
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from os import makedirs
from os.path import dirname, join, exists, expanduser
import subprocess
import json
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger

__author__ = 'eward, MichaelNguyen'

LOGGER = getLogger(__name__)


class PianobarSkill(MycroftSkill):

    def __init__(self):
        super(PianobarSkill, self).__init__(name="PianobarSkill")
        self.process = None
        self.stations = {}
        self.is_setup = False
        self.pianobar_path = expanduser('~/.config/pianobar')

    def initialize(self):
        self.load_data_files(dirname(__file__))
        self._setup()
        # self.load_data_files(dirname(__file__))
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
        self.register_intent(resume_song_intent,
                             self.handle_resume_song_intent)

        list_stations_intent = IntentBuilder("PandoraListStationIntent"). \
            require("QueryKeyword").require("StationKeyword").build()
        self.register_intent(list_stations_intent,
                             self.handle_list_stations_intent)

    def _setup(self):
        if self.settings["email"] != "" or self.settings["password"] != "":
            self.is_setup = True

        if self.is_setup is True:
            if not exists(self.pianobar_path):
                makedirs(self.pianobar_path)

            config_path = join(self.pianobar_path, 'config')

            with open(config_path, 'w+') as f:

                # grabs the tls_key needed
                tls_key = subprocess.check_output(
                    "openssl s_client -connect tuner.pandora.com:443 \
                    < /dev/null 2> /dev/null | openssl x509 -noout \
                    -fingerprint | tr -d ':' | cut -d'=' -f2",
                    shell=True)

                config = 'audio_quality = medium\n' + \
                         'tls_fingerprint = {}\n' + \
                         'user = {}\n' + \
                         'password = {}\n' + \
                         'event_command = {}'

                f.write(config.format(tls_key,
                                      self.settings["email"],
                                      self.settings["password"],
                                      self._dir + '/event_command.py'))

    def _load_current_info(self):
        info_path = join(self.pianobar_path, 'info')

        if not exists(info_path):
            makedirs(info_path)

        with open(info_path, 'r') as f:
            info = json.load(f)

        self.settings["title"] = info["title"]
        self.settings["station_name"] = info["stationName"]
        self.settings["station_count"] = int(info["stationCount"])
        self.settings["stations"] = []

        for index in self.settings["station_count"]:
            station = "station" + str(index)
            self.settings["stations"].append((info[station], index))

    def handle_play_pandora_intent(self, message):
        if self.is_setup is True:
            self.process = subprocess.Popen(["pianobar"],
                                            stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE)
            self.process.stdin.write("0\n")
        else:
            self.speak("Please go to home.mycroft.ai to register pandora")

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

    def handle_list_stations_intent(self, message):
        LOGGER.info(message.__dict__)

        path = join(self.pianobar_path, "nowplaying")
        with open(path, 'r') as f:
            data = json.load(f)

        station_count = int(data["stationCount"])

        list_station_dialog = "subsribed pandora stations are. "

        for num in range(station_count):
            station = "station" + str(num)
            self.stations[str(num)] = data[station]
            list_station_dialog += (data[station] + ". . ")

        self.speak(list_station_dialog)

    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.wait()


def create_skill():
    return PianobarSkill()

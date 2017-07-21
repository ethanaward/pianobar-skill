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

import sys
import subprocess
import json
import time
from os import makedirs, remove, listdir, path
from os.path import dirname, join, exists, expanduser, isfile, abspath
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger
from threading import Timer
from mycroft.util import wait_while_speaking
from fuzzywuzzy import process as fuzz_process

__author__ = 'eward, MichaelNguyen'

LOGGER = getLogger(__name__)


class PianobarSkill(MycroftSkill):
    def __init__(self):
        super(PianobarSkill, self).__init__(name="PianobarSkill")
        self.process = None
        self.is_setup = False
        self.piano_bar_state = None
        self.vocabs = []
        self.terminate_timer = None
        self.volume_state = 0
        self.pianobar_path = expanduser('~/.config/pianobar')

    def initialize(self):
        self.load_data_files(dirname(__file__))
        self._setup()
        self._check_for_pianobar_event()

        def handle_pause(message):
            return self._check_before(
                        self.pause_song, message)

        def handle_next(message):
            return self._check_before(
                        self.next_song, message)

        def handle_resume(message):
            return self._check_before(
                        self.resume_song, message)

        def handle_list(message):
            return self._check_before(
                        self.list_stations, message)

        def handle_change(message):
            return self._check_before(
                        self.change_station, message)

        play_pandora_intent = IntentBuilder("PlayPandoraIntent"). \
            require("PlayKeyword").require("PandoraKeyword").build()
        self.register_intent(play_pandora_intent,
                             self.play_pandora)

        next_song_intent = IntentBuilder("PandoraNextIntent"). \
            require("NextKeyword").build()
        self.register_intent(next_song_intent, handle_next)

        pause_song_intent = IntentBuilder("PandoraPauseIntent"). \
            require("PauseKeyword").build()
        self.register_intent(pause_song_intent, handle_pause)

        resume_song_intent = IntentBuilder("PandoraResumeIntent"). \
            require("ResumeKeyword").build()
        self.register_intent(resume_song_intent, handle_resume)

        list_stations_intent = IntentBuilder("PandoraListStationIntent"). \
            require("QueryKeyword").require("StationKeyword").build()
        self.register_intent(list_stations_intent, handle_list)

        change_stations_intent = IntentBuilder("PandoraChangeStationIntent"). \
            require("ChangeKeyword").require("StationKeyword").build()
        self.register_intent(change_stations_intent, handle_change)

    def _setup(self):
        """
            Necessary functions to setup skill
        """
        self._configure_pianobar()
        self._load_vocab_files()
        self.emitter.on("recognizer_loop:record_begin", self._pause)
        self.emitter.on("recognizer_loop:audio_output_end", self._play)

    def _check_before(self, func, message):
        """
            Check if pianobar process is running before running other functions
        """
        if self.process is not None:
            func(message)
        else:
            self.speak("Pandora is not playing")

    def _pause(self, event=None):
        if self.process is not None:
            self.pause_song()

    def _play(self, event=None):
        if self.process is not None:
            self.resume_song()

    def _configure_pianobar(self):
        """
            Initiates pianobar configurations.
            ie account info, tls key, audio quality
        """
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

    def _load_vocab_files(self):
        """
            load vocabs into self
        """
        vocab_dir = join(dirname(__file__), 'vocab', self.lang)
        if path.exists(vocab_dir):
            for vocab_type in listdir(vocab_dir):
                if vocab_type.endswith(".voc"):
                    with open(join(vocab_dir, vocab_type), 'r') as voc_file:
                        for line in voc_file:
                            parts = line.strip().split("|")
                            vocab = parts[0]
                            self.vocabs.append(vocab)

        else:
            LOGGER.error('No vocab loaded, ' + vocab_dir + ' does not exist')

    def _check_for_pianobar_event(self):
        """
            Check for events triggered by pianobar
        """
        info_ready_path = join(self.pianobar_path, 'info_ready')
        if isfile(info_ready_path):
            self._load_current_info()
            try:
                remove(info_ready_path)
            except Exception as e:
                LOGGER.error(e)
            time.sleep(0.1)
            self.enclosure.mouth_text(self.settings["title"])

        Timer(1, self._check_for_pianobar_event).start()

    def _load_current_info(self):
        """
            loads information emit by pianobar
        """
        info_path = join(self.pianobar_path, 'info')

        if not exists(info_path):
            makedirs(info_path)

        with open(info_path, 'r') as f:
            info = json.load(f)

        self.settings["title"] = info["title"]
        self.settings["station_name"] = info["stationName"]
        self.settings["station_count"] = int(info["stationCount"])
        self.settings["stations"] = []
        LOGGER.info(self.settings["station_count"])
        for index in range(self.settings["station_count"]):
            station = "station" + str(index)
            self.settings["stations"].append((info[station], index))

        LOGGER.info(self.settings["stations"])
        self.settings.store()

    def play_pandora(self, message=None):
        if self.is_setup is True:
            # kill any pianobar instance that exists
            subprocess.call("pkill pianobar", shell=True)

            self.speak("playing pandora")
            wait_while_speaking()

            self.process = subprocess.Popen(["pianobar"],
                                            stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE)

            self.process.stdin.write("0\n")
            self.piano_bar_state = "play"
        else:
            self.speak("Please go to home.mycroft.ai to register pandora")

    def next_song(self, message=None):
            self.process.stdin.write("n")
            self.piano_bar_state = "play"

    def pause_song(self, message=None):
            self.process.stdin.write("S")
            self.piano_bar_state = "paused"

    def resume_song(self, message=None):
            self.process.stdin.write("P")
            self.piano_bar_state = "play"

    def change_station(self, message=None):
        utterance = message.data["utterance"]
        station_to_play = None
        LOGGER.info(self.vocabs)
        LOGGER.info(utterance)
        for vocab in self.vocabs:
            utterance = utterance.replace(vocab, '')

        # strip out any other non important words
        utterance.replace("to", "")
        utterance = utterance.lstrip()
        LOGGER.info(utterance)
        stations = [station[0] for station in self.settings["stations"]]
        probabilities = fuzz_process.extract(utterance, stations)
        LOGGER.info(probabilities)

        if int(probabilities[0][1]) > 50:
            station_number = None
            for station in self.settings["stations"]:
                if station[0] == probabilities[0][0]:
                    self.pause_song()
                    self.speak("changing station to{}".
                               format(station[0]))

                    wait_while_speaking()

                    self.process.stdin.write("s")
                    station_number = str(station[1]) + "\n"
                    self.process.stdin.write(station_number)
                    self.piano_bar_state = "play"
        else:
            self.pause_song()
            self.speak("you are currently not subscribed to that station")
            wait_while_speaking()
            self.resume_song()

    def list_stations(self, message=None):
        self.pause_song()
        time_pause = 4
        list_station_dialog = "subscribed pandora stations are. ."
        for station in self.settings["stations"]:
            list_station_dialog += "{} . ".format(station[0])
            time_pause += 2

        self.speak(list_station_dialog)
        # TODO: explore why this does not work
        # wait_while_speaking()

        time.sleep(time_pause)
        self.play_song()

    def terminate_process(self):
        LOGGER.info(self.piano_bar_state)
        if self.piano_bar_state is "stop":
            self.process.terminate()
            LOGGER.info("Pianobar Skill is terminated")
            self.process.wait()
            self.process = None

            # kill any pianobar instance that exists
            subprocess.call("pkill pianobar", shell=True)

    def stop(self):
        if self.process:
            self.pause_song()

            LOGGER.info("Pianobar Skill will terminate in an hour " +
                        "if no pianobar commands are given")

            try:
                self.terminate_timer.cancel()
            except Exception as e:
                LOGGER.info(e)

            self.piano_bar_state = "stop"
            self.terminate_timer = Timer(3600, self.terminate_process)
            self.terminate_timer.daemon = True
            self.terminate_timer.start()


def create_skill():
    return PianobarSkill()

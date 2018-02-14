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
from os.path import dirname, join, exists, expanduser, isfile, abspath, isdir
import shutil
from adapt.intent import IntentBuilder
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import LOG
from threading import Timer
from mycroft.util import wait_while_speaking
from fuzzywuzzy import fuzz, process as fuzz_process

__author__ = 'eward, MichaelNguyen'


# TODO: handle for bad email and password
# TODO: change timer to use base class timer
class PianobarSkill(MycroftSkill):
    def __init__(self):
        super(PianobarSkill, self).__init__(name="PianobarSkill")
        self.process = None
        self.piano_bar_state = None
        self.current_station = None
        self._is_setup = False
        self.vocabs = []
        self.pianobar_path = expanduser('~/.config/pianobar')
        self._pianobar_initated = False

    def initialize(self):
        self.load_data_files(dirname(__file__))
        self._setup()
        self._check_for_pianobar_event()

    def _register_all_intents(self):
        """ Intents should only be registered once settings are inputed
            to avoid conflicts with other music skills
        """
        def handle_pause(message=None):
            return self._check_before(
                lambda: self.pause_song(message))

        def handle_next_song(message=None):
            return self._check_before(
                lambda: self.next_song(message))

        def handle_next_station(message=None):
            return self._check_before(
                lambda: self.next_station(message))

        def handle_resume(message=None):
            return self._check_before(
                lambda: self.resume_song(message))

        def handle_list(message=None):
            return self._check_before(
                lambda: self.list_stations(message))

        play_pandora_intent = IntentBuilder("PlayPandoraIntent"). \
            require("PlayKeyword").require("PandoraKeyword").build()
        self.register_intent(play_pandora_intent, self.play_pandora)

        next_song_intent = IntentBuilder("PandoraNextIntent"). \
            require("NextKeyword").require("SongKeyword").build()
        self.register_intent(next_song_intent, handle_next_song)

        next_station_intent = IntentBuilder("PandoraNextStationIntent"). \
            require("NextKeyword").require("StationKeyword").build()
        self.register_intent(next_station_intent, handle_next_station)

        pause_song_intent = IntentBuilder("PandoraPauseIntent"). \
            require("PauseKeyword").build()
        self.register_intent(pause_song_intent, handle_pause)

        resume_song_intent = IntentBuilder("PandoraResumeIntent"). \
            require("ResumeKeyword").build()
        self.register_intent(resume_song_intent, handle_resume)

        list_stations_intent = IntentBuilder("PandoraListStationIntent"). \
            require("QueryKeyword").require("StationKeyword").build()
        self.register_intent(list_stations_intent, handle_list)

        play_stations_intent = IntentBuilder("PandoraChangeStationIntent"). \
            require("ChangeKeyword").require("StationKeyword").build()
        self.register_intent(play_stations_intent, self.play_station)

    def _setup(self):
        """
            Necessary functions to setup skill
        """
        self._poll_for_setup()
        self._load_vocab_files()

    def _check_before(self, func):
        """
            Check if pianobar process is running before running func
        """
        if self.process is not None:
            func()
        else:
            self.speak("Pandora is not playing")

    def _poll_for_setup(self):
        email = self.settings.get("email", "")
        password = self.settings.get("password", "")
        try:
            if email and password:
                self._is_setup = True
                self._register_all_intents()
                self._configure_pianobar()
            else:
                t = Timer(2, self._poll_for_setup)
                t.start()
        except Exception as e:
            LOG.error(e)

    def _configure_pianobar(self):
        """
            Initiates pianobar configurations.
            ie account info, tls key, audio quality
        """
        if self._is_setup:
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
            libao_path = expanduser('~/.libao')
            platform = self.config_core['enclosure'].get('platform')
            if platform == 'picroft' or platform == 'mycroft_mark_1':
                if not isfile(libao_path):
                    with open(libao_path, 'w') as f:
                        f.write('dev=0\ndefault_driver=pulse')
                    self.speak("pianobar is configured. please " +
                               "reboot to activate pandora")

            self._init_pianobar()

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
            LOG.error('No vocab loaded, ' + vocab_dir + ' does not exist')

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
                LOG.error(e)
            time.sleep(0.1)
            if self._pianobar_initated:
                self.enclosure.mouth_text(self.settings["title"])
        t = Timer(2, self._check_for_pianobar_event)
        t.start()

    def _init_pianobar(self):
        try:
            LOG.info("INIT PIANOBAR")
            subprocess.call("pkill pianobar", shell=True)
            self.process = subprocess.Popen(["pianobar"],
                                            stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE)
            time.sleep(3)
            self.process.stdin.write("0\n")
            self.process.stdin.write("S")
            time.sleep(0.5)
            self.process.kill()
            self.process = None
        except:
            self.speak_dialog('wrong.credentials')

    def _load_current_info(self):
        """
            loads information emit by pianobar
        """
        info_path = join(self.pianobar_path, 'info')

        # this is a hack to remove the info_path
        # if it's a directory. An earlier version
        # of code may sometimes create info_path as
        # a directory instead of a file path
        # date: 02-18
        if isdir(info_path):
            shutil.rmtree(info_path)

        if not exists(info_path):
            with open(info_path, 'w+'):
                pass

        with open(info_path, 'r') as f:
            info = json.load(f)

        self.settings["title"] = info["title"]
        self.settings["station_name"] = info["stationName"]
        LOG.info(self.settings['station_name'])
        self.settings["station_count"] = int(info["stationCount"])
        self.settings["stations"] = []
        for index in range(self.settings["station_count"]):
            station = "station" + str(index)
            self.settings["stations"].append(
                (info[station].replace("Radio", ""), index))

        LOG.info(self.settings["stations"])
        self.settings.store()

    def _start_pianobar(self):
        try:
            subprocess.call("pkill pianobar", shell=True)
            # start pandora
            self.process = subprocess.Popen(["pianobar"],
                                            stdin=subprocess.PIPE,
                                            stdout=subprocess.PIPE)
            self.current_station = "0"
            self.process.stdin.write("0\n")
            self.pause_song()
            time.sleep(2)
            self._load_current_info()
        except:
            self.speak_dialog('wrong.credentials')

    def _get_station(self, utterance):
        """
            parse the utterance for station names
            and return station with highest probability
        """
        try:
            common_words = [" to ", " on ", " pandora", " play"]
            for vocab in self.vocabs:
                utterance = utterance.replace(vocab, "")

            # strip out other non important words
            for words in common_words:
                utterance = utterance.replace(words, "")

            utterance.lstrip()
            stations = [station[0] for station in self.settings["stations"]]
            probabilities = fuzz_process.extractOne(
                utterance, stations, scorer=fuzz.ratio)
            LOG.info(probabilities)
            if probabilities[1] > 70:
                station = probabilities[0]
                return station
            else:
                return None
        except Exception as e:
            LOG.info(e)
            return None

    def play_last_stationed(self):
        return self.settings.get("last_played")

    def _play_station(self, station, speak=True):
        if speak:
            self.speak("playing {} ".format(station))
            wait_while_speaking()
        for channels in self.settings["stations"]:
            if station == channels[0]:
                wait_while_speaking()
                self.process.stdin.write("s")
                self.current_station = str(channels[1])
                station_number = str(channels[1]) + "\n"
                self.process.stdin.write(station_number)
                self.piano_bar_state = "play"
                self.settings["last_played"] = channels

    def play_pandora(self, message=None):
        if self._is_setup:
            self._start_pianobar()
            station = self._get_station(message.data["utterance"])
            LOG.info(station)
            if station is not None:
                self._play_station(station)
            else:
                last_played = self.settings.get("last_played")
                if last_played:
                    self.speak_dialog(
                        "play.last.station",
                        data={"station": last_played[0]})
                    self.pause_song()
                    self._play_station(last_played[0], speak=False)
                else:
                    self.speak("playing pandora")
                    wait_while_speaking()
                    self._play_station(
                        self.settings["stations"][0][0], speak=False)
        else:
            self.speak("Please go to home.mycroft.ai to register pandora")

    def next_song(self, message=None):
        self.process.stdin.write("n")
        self.piano_bar_state = "play"

    def next_station(self, message=None):
        station_count = self.settings["station_count"]
        current_station = int(self.current_station)
        new_station = current_station + 1
        if new_station < station_count:
            new_station = self.settings["stations"][new_station][0]
            self.pause_song()
            self._play_station(new_station)
        else:
            new_station = 0
            new_station = self.settings["stations"][new_station][0]
            self.pause_song()
            self._play_station(new_station)

    def pause_song(self, message=None):
        self.process.stdin.write("S")
        self.piano_bar_state = "paused"

    def resume_song(self, message=None):
        self.process.stdin.write("P")
        self.piano_bar_state = "play"

    def play_station(self, message=None):
        if self._is_setup:
            utterance = message.data["utterance"]
            station = self._get_station(utterance)

            # pause if pianobar is already active
            if self.process is not None:
                self.pause_song()

            if station is not None:
                # if self.process is None:
                self._start_pianobar()

                self._play_station(station)
            else:
                self.speak("you are currently not subscribed to that station")
                time.sleep(6)
                if self.process is not None and self.piano_bar_state != "stop":
                    self.resume_song()
        else:
            self.speak("Please go to home.mycroft.ai to register pandora")

    # TODO: use converse for this
    def list_stations(self, message=None):
        self.pause_song()

        time_pause = 5
        if len(self.settings["stations"]) >= 4:
            list_station_dialog = "subscribed pandora stations are "
        else:
            list_station_dialog = "subscribed pandora stations are "

        for station in self.settings["stations"][:4]:
            list_station_dialog += "{} . ".format(station[0])
            time_pause += 3

        self.speak(list_station_dialog)
        wait_while_speaking()

        time.sleep(time_pause)
        self.resume_song()

    def stop(self):
        if self.process:
            self.pause_song()


def create_skill():
    return PianobarSkill()

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

import json
import requests
import shutil
import subprocess
import time
from os import makedirs, remove, listdir, path
from os.path import dirname, join, exists, expanduser, isfile, abspath, isdir

from fuzzywuzzy import fuzz, process as fuzz_process
from json_database import JsonStorage

from adapt.intent import IntentBuilder
from mycroft import intent_handler
from mycroft.audio import wait_while_speaking
from mycroft.messagebus.message import Message
from mycroft.skills.common_play_skill import CommonPlaySkill, CPSMatchLevel


HOMEPAGE_URL = "https://www.pandora.com"
LOGIN_URL = "https://www.pandora.com/api/v1/auth/login"


def get_pandora_login_token():
    """A login token must be fetched from the website before logging in"""
    r = requests.get(HOMEPAGE_URL)
    cookies = r.headers["Set-Cookie"]
    token = cookies.split("csrftoken=")[-1].split(";")[0]
    return token


def get_pandora_user_info(username, password):
    """Return pandora user info directly from the website"""
    token = get_pandora_login_token()
    headers = {"Cookie": "csrftoken=" + token, "X-CsrfToken": token}
    data = {"username": username, "password": password}
    r = requests.post(LOGIN_URL, json=data, headers=headers)
    return r.json() if r.status_code == 200 else None


class PianobarSkill(CommonPlaySkill):
    def __init__(self):
        super().__init__(name="PianobarSkill")
        self.process = None
        self.piano_bar_state = None  # 'playing', 'paused', 'autopause'
        self.current_station = None
        self._is_setup = False
        self.vocabs = []  # keep a list of vocabulary words
        self.pianobar_path = expanduser("~/.config/pianobar")
        self._pianobar_initated = False
        self.debug_mode = False
        self.idle_count = 0
        play_info_file = join(self.file_system.path, "play-info.json")
        self.play_info = JsonStorage(play_info_file)

        subprocess.call(["killall", "-9", "pianobar"])

    def initialize(self):
        self._load_vocab_files()

        # Initialize settings values
        self.settings["email"] = self.settings.get("email","")
        self.settings["password"] = self.settings.get("password","")
        self.play_info["song_artist"] = ""
        self.play_info["song_title"] = ""
        self.play_info["song_album"] = ""
        self.play_info["station_name"] = ""
        self.play_info["station_count"] = 0
        self.play_info["stations"] = []
        self.play_info["last_played"] = None
        self.play_info["first_init"] = True  # True = first run ever
        self.play_info.store()

        # Check and then monitor for credential changes
        self.settings_change_callback = self.on_websettings_changed
        self.on_websettings_changed()
        self.add_event("mycroft.stop", self.stop)

    def CPS_match_query_phrase(self, phrase):
        if not self._is_setup:
            if self.voc_match(phrase, "Pandora"):
                # User is most likely trying to use Pandora, e.g.
                # "play pandora" or "play John Denver using Pandora"
                return ("pandora", CPSMatchLevel.GENERIC)

        result = self._extract_station(phrase)
        if result:
            # User spoke one of their station's names, e.g.
            # "Play summertime love"
            match_level = CPSMatchLevel.TITLE

            if self.voc_match(phrase, "Pandora"):
                # User included pandora explicitly, e.g.
                # "Play summertime love using Pandora"
                match_level = CPSMatchLevel.MULTI_KEY

            station = result[0]
            return (station, match_level, {"station": station})
        elif self.voc_match(phrase, "Pandora"):
            # User has setup Pandora on their account and said Pandora,
            # so is likely trying to start Pandora, e.g.
            # "play pandora" or "play some music on pandora"
            return ("pandora", CPSMatchLevel.MULTI_KEY)

    def CPS_start(self, phrase, data):
        # Use the "latest news" intent handler
        station = None
        if data:
            station = data.get("station")

        # Launch player
        self.play_pandora(station)

    ######################################################################
    # 'Auto ducking' - pause playback when Mycroft wakes

    def handle_listener_started(self, message):
        if self.piano_bar_state == "playing":
            self.handle_pause()
            self.piano_bar_state = "autopause"

            # Start idle check
            self.idle_count = 0
            self.cancel_scheduled_event("IdleCheck")
            self.schedule_repeating_event(
                self.check_for_idle, None, 1, name="IdleCheck"
            )

    def check_for_idle(self):
        if not self.piano_bar_state == "autopause":
            self.cancel_scheduled_event("IdleCheck")
            return

        if self.enclosure.display_manager.get_active() == "":
            # No activity, start to fall asleep
            self.idle_count += 1

            if self.idle_count >= 2:
                # Resume playback after 2 seconds of being idle
                self.cancel_scheduled_event("IdleCheck")
                self.handle_resume_song()
        else:
            self.idle_count = 0

    ######################################################################

    def _register_all_intents(self):
        """Intents should only be registered once settings are inputed
        to avoid conflicts with other music skills
        """
        next_station_intent = (
            IntentBuilder("PandoraNextStationIntent")
            .require("Next")
            .require("Station")
            .build()
        )
        self.register_intent(next_station_intent, self.handle_next_station)

        list_stations_intent = (
            IntentBuilder("PandoraListStationIntent")
            .optionally("Pandora")
            .require("Query")
            .require("Station")
            .build()
        )
        self.register_intent(list_stations_intent, self.handle_list)

        play_stations_intent = (
            IntentBuilder("PandoraChangeStationIntent")
            .require("Change")
            .require("Station")
            .build()
        )
        self.register_intent(play_stations_intent, self.play_station)

        # Messages from the skill-playback-control / common Audio service
        self.add_event("mycroft.audio.service.pause", self.handle_pause)
        self.add_event("mycroft.audio.service.resume", self.handle_resume_song)
        self.add_event("mycroft.audio.service.next", self.handle_next_song)

    def on_websettings_changed(self):
        if not self._is_setup:
            email = self.settings.get("email", "")
            password = self.settings.get("password", "")
            try:
                if email and password:
                    self._configure_pianobar()
                    self._init_pianobar()
                    self._register_all_intents()
                    self._is_setup = True
            except Exception as e:
                self.log.error("websettings_changed():threw %s" % (e,))
        self._configure_pianobar()

    def _configure_pianobar(self):
        # Initialize the Pianobar configuration file
        if not exists(self.pianobar_path):
            makedirs(self.pianobar_path)

        config_path = join(self.pianobar_path, "config")
        with open(config_path, "w+") as f:

            # grabs the tls_key needed
            tls_key = subprocess.check_output(
                "openssl s_client -connect tuner.pandora.com:443 \
                < /dev/null 2> /dev/null | openssl x509 -noout \
                -fingerprint | tr -d ':' | cut -d'=' -f2",
                shell=True,
            )

            config = (
                "audio_quality = medium\n"
                + "tls_fingerprint = {}\n"
                + "user = {}\n"
                + "password = {}\n"
                + "event_command = {}"
            )

            f.write(
                config.format(
                    tls_key,
                    self.settings["email"],
                    self.settings["password"],
                    self.root_dir + "/event_command.py",
                )
            )

        # Raspbian requires adjustments to audio output to use PulseAudio
        platform = self.config_core["enclosure"].get("platform")
        if platform == "picroft" or platform == "mycroft_mark_1":
            libao_path = expanduser("~/.libao")
            if not isfile(libao_path):
                with open(libao_path, "w") as f:
                    f.write("dev=0\ndefault_driver=pulse")
                self.speak_dialog("configured.please.reboot")
                wait_while_speaking()
                self.emitter.emit(Message("system.reboot"))

    def _load_vocab_files(self):
        # Keep a list of all the vocabulary words for this skill.  Later
        # these words will be removed from utterances as part of the station
        # name.
        vocab_dir = join(dirname(__file__), "vocab", self.lang)
        if path.exists(vocab_dir):
            for vocab_type in listdir(vocab_dir):
                if vocab_type.endswith(".voc"):
                    with open(join(vocab_dir, vocab_type), "r") as voc_file:
                        for line in voc_file:
                            parts = line.strip().split("|")
                            vocab = parts[0]
                            self.vocabs.append(vocab)
        else:
            self.log.error("No vocab loaded, " + vocab_dir + " does not exist")

    def start_monitor(self):
        # Clear any existing event
        self.stop_monitor()

        # Schedule a new one every second to monitor/update display
        self.schedule_repeating_event(
            self._poll_for_pianobar_update, None, 1, name="MonitorPianobar"
        )
        self.add_event("recognizer_loop:record_begin", self.handle_listener_started)

    def stop_monitor(self):
        # Clear any existing event
        self.cancel_scheduled_event("MonitorPianobar")

    def _poll_for_pianobar_update(self, message):
        # Checks once a second for feedback from Pianobar

        # 'info_ready' file is created by the event_command.py
        # script when Pianobar sends new track information.
        info_ready_path = join(self.pianobar_path, "info_ready")
        if isfile(info_ready_path):
            self._load_current_info()
            try:
                remove(info_ready_path)
            except Exception as e:
                self.log.debug("Recoverable exception handled %s" % (e,))

            # Update the "Now Playing song"
            self.log.info("State: " + str(self.piano_bar_state))
            if self.piano_bar_state == "playing":
                self.enclosure.mouth_text(
                    self.play_info["song_artist"] + ": " + self.play_info["song_title"]
                )

    def cmd(self, cmd_str):
        try:
            self.process.stdin.write(cmd_str.encode())
            self.process.stdin.flush()
        except Exception as e:
            self.log.debug("Recoverable exception handled %s" % (e,))

    def troubleshoot_auth_error(self):
        user_info = get_pandora_user_info(
            self.settings["email"], self.settings["password"]
        )
        if user_info:
            if user_info.get("stationCount") == 0:
                self.speak_dialog("no.stations")
            else:
                self.speak_dialog("pandora.error")
        else:
            self.speak_dialog("wrong.credentials")

    def _init_pianobar(self):
        if self.play_info.get("first_init") is False:
            return

        # Run this exactly one time to prepare pianobar for usage
        # by Mycroft.
        try:
            subprocess.call(["killall", "-9", "pianobar"])
            self.process = subprocess.Popen(
                ["pianobar"], stdin=subprocess.PIPE, stdout=subprocess.PIPE
            )
            time.sleep(3)
            self.cmd("0\n")
            self.cmd("S")
            time.sleep(0.5)
            self.process.kill()
            self.play_info["first_init"] = False
            self._load_current_info()
        except Exception as e:
            self.log.warning("Failed to connect to Pandora: %s" % (e,))
            self.troubleshoot_auth_error()

        self.process = None

    def _load_current_info(self):
        # Load the 'info' file created by Pianobar when changing tracks
        info_path = join(self.pianobar_path, "info")

        # this is a hack to remove the info_path
        # if it's a directory. An earlier version
        # of code may sometimes create info_path as
        # a directory instead of a file path
        # date: 02-18
        if isdir(info_path):
            shutil.rmtree(info_path)

        try:
            with open(info_path, "r") as f:
                info = json.load(f)
        except:
            info = {}

        # Save the song info for later display
        self.play_info["song_artist"] = info.get("artist", "")
        self.play_info["song_title"] = info.get("title", "")
        self.play_info["song_album"] = info.get("album", "")

        self.play_info["station_name"] = info.get("stationName", "")
        if self.debug_mode:
            self.log.info("Station name: " + str(self.play_info["station_name"]))
        self.play_info["station_count"] = int(info.get("stationCount", 0))
        self.play_info["stations"] = []
        for index in range(self.play_info["station_count"]):
            station = "station" + str(index)
            self.play_info["stations"].append(
                (info[station].replace("Radio", ""), index)
            )
        if self.debug_mode:
            self.log.info("Stations: " + str(self.play_info["stations"]))
        self.play_info.store()

    def _process_valid(self):
        if self.process and self.process.poll() == None:
            return True  # process is running
        else:
            return False

    def _launch_pianobar_process(self):
        # if we have a process let's 
        # try to use it to quit gracefully
        if self.process:
            self.cmd("q\n")
        else:
            subprocess.call(["killall", "-9", "pianobar"])
        time.sleep(1)

        try:
            # start pandora
            if self.debug_mode:
                self.process = subprocess.Popen(["pianobar"], stdin=subprocess.PIPE)
            else:
                self.process = subprocess.Popen(
                    ["pianobar"], stdin=subprocess.PIPE, stdout=subprocess.PIPE
                )
            self.current_station = "0"
            self.cmd("0\n")
            self.handle_pause()
            time.sleep(2)
            if self._process_valid():
                self._load_current_info()
                self.log.info("Pianobar process initialized")
                return
        except Exception:
            self.log.warning("Failed to connect to Pandora")

        self.troubleshoot_auth_error()
        self.process = None

    def _extract_station(self, utterance):
        """
        parse the utterance for station names
        and return station with highest probability

        Args:
            utterance (str): search term

        Returns:
            (station->str, conf->float): Tupple with the station name and
                                            match confidence, or None
        """
        try:
            # Strip out verbal command words.  For example,
            # "play tom waits on pandora" becomes "tom waits"

            for vocab in self.vocabs:
                utterance = utterance.replace(vocab, "")
            utterance = " ".join(utterance.split())  # eliminate extra spaces

            stations = [station[0] for station in self.play_info["stations"]]
            probabilities = fuzz_process.extractOne(
                utterance, stations, scorer=fuzz.ratio
            )
            if self.debug_mode:
                self.log.info("Probabilities: " + str(probabilities))
            if probabilities[1] > 70:
                station = probabilities[0]
                return (station, probabilities[1])
            else:
                return None
        except Exception as e:
            self.log.info(e)
            return None

    def _play_station(self, station, dialog=None):
        self.log.info("Starting: " + str(station))
        self._launch_pianobar_process()

        if not self.process:
            return

        if dialog:
            self.speak_dialog(dialog, {"station": station})
        else:
            if station:
                self.speak_dialog("playing.station", {"station": station})

        self.enclosure.mouth_think()
        if station:
            for channel in self.play_info.get("stations"):
                if station == channel[0]:
                    self.cmd("s")
                    self.current_station = str(channel[1])
                    station_number = str(channel[1]) + "\n"
                    self.cmd(station_number)
                    self.piano_bar_state = "playing"
                    self.play_info["last_played"] = channel
                    self.start_monitor()
        else:
            time.sleep(2)  # wait for pianobar to loading
            if self.debug_mode:
                self.log.info(self.play_info.get("stations"))
            # try catch block because some systems
            # may not load pianobar info in time
            try:
                channel = self.play_info.get("stations")[0]
                if self.debug_mode:
                    self.log.info(channel)
                if channel:
                    self.speak_dialog("playing.station", {"station": channel[0]})
                    station_number = str(channel[1]) + "\n"
                    if self.debug_mode:
                        self.log.info(station_number)
                    self.cmd(station_number)
                    self.play_info["last_played"] = channel
                else:
                    raise ValueError
            except Exception as e:
                self.log.info(e)
                self.speak_dialog("playing.station", {"station": "pandora"})
                self.current_station = "0"
                self.cmd("0\n")
            self.handle_resume_song()
            self.piano_bar_state = "playing"
            self.start_monitor()

    def play_pandora(self, station):
        if self._is_setup:
            # Examine the whole utterance to see if the user requested a
            # station by name
            if self.debug_mode:
                self.log.info("Station request:" + str(station))

            dialog = None
            if not station:
                last_played = self.play_info.get("last_played")
                if last_played:
                    station = last_played[0]
                    dialog = "resuming.last.station"
                else:
                    # default to the first station in the list
                    if self.play_info.get("stations"):
                        station = self.play_info["stations"][0][0]

            # Play specified station
            self._play_station(station, dialog)
        else:
            # Lead user to setup for Pandora
            self.speak_dialog("please.register.pandora")

    def handle_next_song(self, message=None):
        if self.process and self.piano_bar_state == "playing":
            self.enclosure.mouth_think()
            self.cmd("n")
            self.piano_bar_state = "playing"
            self.start_monitor()

    def handle_next_station(self, message=None):
        if self.process and self.play_info.get("stations"):
            new_station = int(self.current_station) + 1
            if new_station >= int(self.play_info.get("station_count", 0)):
                new_station = 0
            new_station = self.play_info["stations"][new_station][0]
            self._play_station(new_station)

    def handle_pause(self, message=None):
        if self.process:
            self.cmd("S")
            self.process.stdin.flush()
            self.piano_bar_state = "paused"
            self.stop_monitor()

    def handle_resume_song(self, message=None):
        if self.process:
            self.cmd("P")
            self.piano_bar_state = "playing"
            self.start_monitor()

    def play_station(self, message=None):
        if self._is_setup:
            # Examine the whole utterance to see if the user requested a
            # station by name
            station = self._extract_station(message.data["utterance"])

            if station is not None:
                self._play_station(station[0])
            else:
                self.speak_dialog("no.matching.station")
        else:
            # Lead user to setup for Pandora
            self.speak_dialog("please.register.pandora")

    def handle_list(self, message=None):
        is_playing = self.piano_bar_state == "playing"
        if is_playing:
            self.handle_pause()

        # build the list of stations
        l = []
        for station in self.play_info.get("stations"):
            l.append(station[0])  # [0] = name
        if len(l) == 0:
            self.speak_dialog("no.stations")
            return

        # read the list
        if len(l) > 1:
            list = ", ".join(l[:-1]) + " " + self.translate("and") + " " + l[-1]
        else:
            list = str(l)
        self.speak_dialog("subscribed.to.stations", {"stations": list})

        if is_playing:
            wait_while_speaking()
            self.handle_resume_song()

    def stop(self):
        return self.shutdown()
        if self.piano_bar_state and not self.piano_bar_state == "paused":
            self.handle_pause()
            self.enclosure.mouth_reset()
            return True

    @intent_handler(IntentBuilder("").require("Pandora").require("Debug").require("On"))
    def debug_on_intent(self, message=None):
        if not self.debug_mode:
            self.debug_mode = True
            self.speak_dialog("entering.debug.mode")

    @intent_handler(
        IntentBuilder("").require("Pandora").require("Debug").require("Off")
    )
    def debug_off_intent(self, message=None):
        if self.debug_mode:
            self.debug_mode = False
            self.speak_dialog("leaving.debug.mode")

    def shutdown(self):
        self.stop_monitor()

        # Clean up before shutting down the skill
        if self.piano_bar_state == "playing":
            self.enclosure.mouth_reset()

        if self.process:
            self.cmd("q")

        self.play_info.store()

        super(PianobarSkill, self).shutdown()

    def converse(self, utterances, lang="en-us"):
        self.cmd("P")    # always resume playing
        if self.process and self.piano_bar_state == "playing":
            # consume all utterances while playing
            # will need to hard match on commands here
            # if necessary because of old core design.
            return True
        return False

def create_skill():
    return PianobarSkill()

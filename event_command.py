#!/usr/bin/env python

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

import os
import sys
import json
import shutil
from os.path import expanduser, join, abspath, isdir
from threading import Thread
"""
    This module is used as a callback for pianobar events. pianobar
    emits different events and calls this module for every event.
    The events can be captured in event variable.
"""

__author__ = 'MichaelNguyen'

path = os.environ.get('XDG_CONFIG_HOME')
if not path:
    path = expanduser("~/.config")
else:
    path = expanduser(path)

now_playing = join(path, 'pianobar', 'info')

info = sys.stdin.readlines()
event = sys.argv[1]

if event == 'songstart':
    song_dict = {}
    for item in info:
        item = item.split("=")
        song_dict[item[0]] = item[1].rstrip()

    # this is a hack to remove the info_path
    # if it's a directory. An earlier version
    # of code may sometimes create info_path as
    # a directory instead of a file path
    # date: 02-18
    if isdir(now_playing):
        shutil.rmtree(now_playing)

    with open(now_playing, 'w') as f:
        json.dump(song_dict, f)

    # HACKY! This creates a file to notify the pianobar skill
    # to load the information
    pianobar_path = join(expanduser('~/.config/pianobar'), 'info_ready')
    with open(pianobar_path, 'w+') as f:
        pass
# elif event == "userlogin":
#     with open("./settings.json", "w") as f:
#         settings = json.load(f)
#         settings["info"] = str(info)
#         json.dump(settings, f)

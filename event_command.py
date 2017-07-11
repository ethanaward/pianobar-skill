#!/usr/bin/env python

import os
import sys
from os.path import expanduser, join
import json

path = os.environ.get('XDG_CONFIG_HOME')
if not path:
    path = expanduser("~/.config")
else:
    path = expanduser(path)

now_playing = join(path, 'pianobar', 'info')

info = sys.stdin.readlines()
cmd = sys.argv[1]

if cmd == 'songstart':
    song_dict = {}
    for item in info:
        item = item.split("=")
        song_dict[item[0]] = item[1].rstrip()

    with open(now_playing, 'w') as f:
        json.dump(song_dict, f)

#!/bin/bash

found_exe() {
    hash "$1" 2>/dev/null
}

if found_exe apt-get; then
    apt-get install pianobar -y
fi

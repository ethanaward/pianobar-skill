#!/bin/bash

# The requirements.sh is an advanced mechanism an should rarely be needed.
# Be aware that it won't run with root permissions and 'sudo' won't work
# in most cases.

# detect distribution using lsb_release (may be replaced parsing /etc/*release)
dist=$(lsb_release -ds)

found_exe() {
    hash "$1" 2>/dev/null
}

# setting dependencies and package manager in relation to the distribution
if found_exe pkcon; then
    # pkcon is a high-level front end for many package manager technologies,
    # prefer this if it exists.
    pm="pkcon"
else
    priv="sudo"
    dependencies=( pianobar )

    if [ "$dist"  == "\"Arch Linux\""  ]; then
        pm="pacman -S"
    elif [[ "$dist" =~  "Ubuntu" ]] || [[ "$dist" =~ "Debian" ]] ||[[ "$dist" =~ "Raspbian" ]]; then
        pm="apt install"
    elif [[ "$dist" =~ "SUSE" ]]; then
        pm="zypper install"
    fi
fi

# installing dependencies
if [ ! -z "$pm" ]; then
   for dep in "${dependencies[@]}"
   do
        $priv $pm $dep
   done
fi


if found_exe pianobar; then
    exit 0
else
    echo "Could not find pianobar! Please install with your package manager. ($dist)"
    exit 1
fi

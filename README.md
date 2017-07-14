# Requirements

This skill should work with Mycroft version 0.8.18 +
To use the Pandora ( Pianobar ) skill you'll first need to install Pianobar and configure it to work with your account.  In the future we plan to allow configuration through home.mycroft.ai.

First install pianobar

```
sudo su
apt-get update
apt-get -y install pianobar
```

create a settings.json file. In the file add 

```
{
    "email": [YOUR PANDORA EMAIL LOGIN HERE],
    "password:" [YOUR PANDORA PASSWORD HERE]
}
```

Once adding settings.json, the skill should reload from the mycroft MSM. If not, restart the skills service.

On Mark 1 and Picroft
```
sudo service mycroft-skills restart
```

On Desktop

```
./mycroft.sh start
```

Now say "Hey Mycroft....play pandora"

## Features

1. Play Pandora 
                
       example "Hey Mycroft... play pandora"

2. Pause 
    
       example "Hey Mycroft... pause"

3. Resume
    
       example "Hey Mycroft... resume song"

4. Next Song
    
       example "Hey Mycroft... next song"

5. List Stations
    
       example "Hey Mycroft... list stations"


More to come as this project is under active development. 

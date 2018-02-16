# Requirements

This skill should work with Mycroft version 0.9.1 +

To use the Pandora ( Pianobar ) skill you'll first need to install Pianobar and configure it to work with your account.

#### Skill installation
You can install via voice, MSM or git clone this project into the mycroft skills directory usually found in /opt/mycroft/skills


##### Voice
This will install the pip requirements for you.

```
"Hey mycroft... install pandora"
```

##### MSM
This will install the pip requirements for you. 

```
msm install pandora
```

##### Manually (git clone)

```
git clone https://github.com/ethanaward/pianobar-skill.git
```
NOTE* If you take this route, you will need to change the permissions on the Mark 1 or Picroft to Mycroft.

```
sudo chown mycroft *
```

```
cd pianobar-skill
```

Install the skill requirements from the requirements.txt

```
pip install -r requirements.txt
```

#### Install pianobar package

##### New mycroft images
Mycroft core version 0.9.10 and up does not require you to install pianobar manually.

##### Old mycroft images and ubunutu

```
bash requirements.sh
```

or

```
apt-get update
apt-get -y install pianobar
```

For picroft and mark 1 the skill should automatically set the appropriate drivers. For desktop in my experiences it doesn't need it. If you want to double check and do it manually do these steps:

```
echo default_driver=pulse > ~/.libao
echo dev=0 >> ~/.libao
```

#### Setting up Pandora Account
Go to home.mycroft.ai to input your pandora credentials

Now say "Hey Mycroft....play pandora"

## Features

1. Play Pandora 
                
       example "Hey Mycroft... play pandora" or "Hey Mycroft, play Today's Hits Radio on pandora"

2. Pause 
    
       example "Hey Mycroft... pause"

3. Resume
    
       example "Hey Mycroft... resume song"

4. Next Song
    
       example "Hey Mycroft... next song"

5. List Stations
    
       example "Hey Mycroft... list stations"

6. Change Stations
    
       example "Hey Mycroft... change station to Today's Top Hits on pandora"

7. Next Station
       
       example "Hey Mycroft... next station"

8. Debug mode

       example "Hey Mycroft... turn on/off debug mode"

More to come as this project is under active development. 

## Mycroft Pulse Audio Configuration
Sometimes when you are listening to pandora, you want pandora to pause and resume automatically, when you are interacting with mycroft. Mycroft has an Audio service that can do that but currently is not turned on by default. You can find out how to do it here https://github.com/MycroftAI/mycroft-core/wiki/Audio-Service#pulse-audio-features

## Troubleshooting
Debug mode will allow pianobar to write to the mycroft-cli. There you can see a little bit more detail on what pianobar is doing under the hood.

#### Song is not playing
* You may be in paused mode after invoking 'play pandora'. Simply say 'resume pandora'
* Sometimes pandora will deny access to their streaming service. This can be resolve by just waiting for some time. I've
  notice if i have multiple devices playing pandora at once. To see if this is your issue, turn on debug mode, 
  and you should see this message after invoking pandora 'Error: Access denied. Try again later.'

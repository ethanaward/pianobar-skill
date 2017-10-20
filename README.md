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
If you are using the new mark 1 and picroft images, as of 10/19/2017, you should be able to just do a skill installation 
and msm would automatically install pianobar using polkit. 

#### Old mycroft images and ubunutu

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
If you are on 0.9.1 you can leverage the Web skill settings feature. Go to home.mycroft.ai and go to the skills tab to input your credentials. If you do not have that image, you can manually create the settings.json file and input your information.

```
vim settings.json
```

create a json structure that looks like this

```
{
    "email": "YOUR PANDORA EMAIL LOGIN HERE",
    "password": "YOUR PANDORA PASSWORD HERE"
}
```

Once editing settings.json, the skill should reload from the mycroft MSM. If not, restart the skills service.

On Mark 1 and Picroft
```
sudo service mycroft-skills restart
```

On Desktop for 0.9.1+

```
./start-mycroft.sh debug
```

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


More to come as this project is under active development. 

## Mycroft Pulse Audio Configuration
Sometimes when you are listening to pandora, you want pandora to pause and resume automatically, when you are interacting with mycroft. Mycroft has an Audio service that can do that but currently is not turned on by default. You can find out how to do it here https://github.com/MycroftAI/mycroft-core/wiki/Audio-Service#pulse-audio-features

# Requirements

To use the Pandora ( Pianobar ) skill you'll first need to install Pianobar and configure it to work with your account.  In the future we plan to allow configuration through home.mycroft.ai.

First install pianobar

```
sudo su
apt-get update
apt-get -y install pianobar
```
Now you need to set Pianobar to use the appropriate drivers.  Edit the file '/etc/libao.conf' :

```
echo default_driver=pulse > /etc/libao.conf
echo dev=0 >> /etc/libao.conf
```
Create the config file for Pianobar.  You'll want to do this under the account that will be using the software.  On our Mark I devices this is the user "mycroft"

```
sudo su
su mycroft
mkdir /home/mycroft/.config/pianobar
touch /home/mycroft/.config/pianobar/config
```

The Pianobar version that is built into Raspbian is out of date and has a bad TLS key.  You'll want to specify a key, the account name and password.  You'll also want to set the audio quality and start station, usern and password.

```
echo audio_quality = medium > /home/mycroft/.config/pianobar/config
echo tls_fingerprint = FC2E6AF49FC63AEDAD1078DC22D1185B809E7534 >> /home/mycroft/.config/pianobar/config
echo user = [USER EMAIL HERE] >> /home/mycroft/.config/pianobar/config
echo password = [PANDORA PASSWORD HERE] >> /home/mycroft/.config/pianobar/config
```
Now you should be able to play Pandora from the command line.

```
pianobar
```

Ctrl + C will exit.

Once you've been able to start Pianobar from the command line you should be able to have Mycroft start it by saying "Hey, Mycroft....play pandora"

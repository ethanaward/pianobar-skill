# Requirements

In order to use this on the Pi, you will need the following file in `/etc/libao.conf`:

```
default_driver=pulse
dev=0
```

Additionally, you will need a config file in the `.config/pianobar/config` file of whichever user is running the pianobar process - note that for the apt installation of Mycroft, this will be the mycroft user, not your normal user!

# sonos-yamaha-monitor

*SONOS Connect & Yamaha Receiver Monitor* automatically turns on/off Yamaha Receiver(s) when SONOS Connect starts/stop playing.

It will set the proper INPUT, VOLUME level and SOUNDPRG (sound program).  The application is fully-functional
and, through configuration, will support one mor more SONOS Connect and Yamaha receiver relationships.  It also provides volume safeguarding for when the receiver is used with other variable output devices (so you don't blow speakers when switching to a different INPUT), as well as the ability to not "take over" an input that is already in use (for example, with a Television or DVR INPUT).

That said, it is a work in progress and there area few more non-critical things to do.

## Prerequisites

* pew
* soco
* rxv
* python-pushover
* supervisor

## How to install

```
apt-get install supervisor
pip install pew soco rxv python-pushover
pew new sonos-yamaha-monitor
pip install -r requirements.txt
sudo cp supervisord-conf.d/* /etc/supervisor/conf.d/.
sudo mkdir /var/log/sonos-yamaha-monitor
mkdir ~/.sonos-yamaha-monitor
cp configs/*.yml ~/.sonos-yamaha-monitor
sudo service supervisor restart
```

## Example log

```
2016-03-14 21:31:48,438 INFO initializing SonosYamahaMonitor [__init__ 72]
2016-03-14 21:31:48,446 INFO configuration ~/.sonos-yamaha-monitor/family-room.yml [find_cfg 99]
2016-03-14 21:31:48,446 INFO {'notifications': {'pushover': {'app': 'XXXXXXXXXXXXXXXXXXXXXXXXXX', 'enabled': True, 'user': 'XXXXXXXXXXXXXXXXXXXXXXX'}}, 'sonos': {'event_port': 1400, 'ip': '10.0.10.152', 'player_name': 'Family Room', 'uid': 'RINCON_B8E9379ABC8601400'}, 'yamaha': {'volume': -20.0, 'ctrl_url': 'http://10.0.10.41:80/YamahaRemoteControl/ctrl', 'soundprg': 'Straight', 'input': 'AUDIO', 'off_volume': -80.0, 'friendly_name': 'Family Room', 'model_name': 'HTR-4065'}} [__init__ 89]
2016-03-14 21:31:48,488 INFO Family Room (HTR-4065) Power=False, Input=AUDIO, Volume=-80.0 [monitor 220]
2016-03-14 21:31:48,489 INFO Family Room SONOS Subscribing to events [_subscription 126]
2016-03-14 21:31:48,512 INFO Family Room SONOS: PAUSED_PLAYBACK [_status 198]
2016-03-14 21:31:48,441 INFO initializing SonosYamahaMonitor [__init__ 72]
2016-03-14 21:31:48,448 INFO configuration ~/.sonos-yamaha-monitor/master-bedroom.yml [find_cfg 99]
2016-03-14 21:31:48,449 INFO {'notifications': {'pushover': {'app': 'XXXXXXXXXXXXXXXXXXXXXXXXXX', 'enabled': True, 'user': 'XXXXXXXXXXXXXXXXXXXXXXX'}}, 'sonos': {'event_port': 1401, 'ip': '10.0.10.160', 'player_name': 'Master Bedroom', 'uid': 'RINCON_B8E93799C18401400'}, 'yamaha': {'volume': -10.0, 'ctrl_url': 'http://10.0.10.43:80/YamahaRemoteControl/ctrl', 'soundprg': 'Straight', 'input': 'AUDIO1', 'off_volume': -80.0, 'friendly_name': 'Master Bedroom', 'model_name': 'RX-V675'}} [__init__ 89]
2016-03-14 21:31:48,612 INFO Master Bedroom (RX-V675) Power=False, Input=HDMI2, Volume=-50.0 [monitor 220]
2016-03-14 21:31:48,612 INFO Master Bedroom SONOS Subscribing to events [_subscription 126]
2016-03-14 21:31:48,654 INFO Master Bedroom SONOS: STOPPED [_status 198]
```

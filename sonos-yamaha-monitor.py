#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import soco
import Queue
from signal import signal, SIGTERM
import argparse
import logging
import rxv
import yaml
from urlparse import urlparse
from pushover import Client as pushover

__version__ = '1.0'

logger = logging.getLogger(__name__)
lfmt = '%(asctime)s %(levelname)s %(name)s %(funcName)s %(lineno)d %(message)s'
lfmt = '%(asctime)s %(levelname)s %(funcName)s %(lineno)d %(message)s'
lfmt = '%(asctime)s %(levelname)s %(message)s [%(funcName)s %(lineno)d]'
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO, format=lfmt)
logging.getLogger("requests").setLevel(logging.ERROR)
logging.getLogger("soco").setLevel(logging.ERROR)
logging.getLogger("rxv").setLevel(logging.ERROR)


def scan():
    zones = soco.discover()
    print "SONOS" + "\n" + "-----"
    for zone in zones:
        transport_info = zone.get_current_transport_info()

        # zone.get_speaker_info().get('hardware_version')
        if True is True:
            print "{}: {}, {}, {}, {}, IP={}".format(
                zone.uid,
                zone.player_name,
                transport_info['current_transport_status'],
                transport_info['current_transport_state'],
                transport_info['current_transport_speed'],
                zone.ip_address
            )

    print "\n" + "YAMAHA" + "\n" + "------"
    receivers = rxv.find()
    for rx in receivers:
        uri = urlparse(rx.ctrl_url)

        print "{}: {} ({})\n\t\t{}\n\t\t{}".format(
            uri.hostname,
            rx.friendly_name,
            rx.model_name,
            rx.ctrl_url,
            rx.basic_status)


def get_args():
    parser = argparse.ArgumentParser(
        description="Sonos and Yamaha receiver monitor")

    parser.add_argument('--scan', action='store_true')
    parser.add_argument('--zone', type=str, help='name of zone')
    args = parser.parse_args()
    return args


class SonosYamahaMonitor():
    def __init__(self, zone):
        self.log = logger or logging.getLogger(__name__)
        self.log.info('initializing %s', self.__class__.__name__)
        self.zone = zone
        self.state = None
        self.cfg = None
        self.subscription = None
        self.renewal_time = 120
        self.break_loop = False
        self.last_status = None
        self.sonos = None
        self.yamaha = None
        self.status = None
        self.event = None

        self.find_cfg()
        if not self.state:
            self.log.error('error loading config.')
            return None
        self.log.info(self.cfg)
        self.monitor()

    def find_cfg(self):
        cfg_fname = "/home/wylie/.sonos-yamaha-monitor/%s.yml" % (self.zone)
        try:
            with open(cfg_fname, 'r') as yml:
                self.log.debug('yml=%s', yml)
                self.cfg = yaml.load(yml)
                self.state = True
                self.log.info('configuration %s', cfg_fname)
                return True
        except Exception, e:
            self.log.error('failure to process=%s', cfg_fname)
            self.log.error('exception:%s', repr(e))
            return None
        return False

    def handle_sigterm(self, *args):
        self.log.info("SIGTERM caught. Exiting gracefully")
        self.break_loop = True

    def _subscription(self):
        if not self.subscription or not self.subscription.is_subscribed or \
                self.subscription.time_left <= 5:
            if self.subscription:
                self.log.info("{} SONOS Unsubscribing from events"
                              .format(self.cfg['sonos']['player_name']))
                try:
                    self.subscription.unsubscribe()
                    soco.events.event_listener.stop()
                except Exception as e:
                    self.log.info(
                        "{} SONOS Unsubscribe from events failed: {}"
                        .format(self.cfg['sonos']['player_name'], e))

            self.log.info("{} SONOS Subscribing to events"
                          .format(self.cfg['sonos']['player_name']))
            try:
                self.subscription = self.sonos.avTransport.subscribe(
                    requested_timeout=self.renewal_time, auto_renew=True)
            except Exception as e:
                self.log.info("{} SONOS Subscribe to events failed: {}"
                              .format(self.cfg['sonos']['player_name'], e))
                time.sleep(10)

    def _yamaha_on(self):
        self.log.info("{} Yamaha setting on".format(
            self.cfg['yamaha']['friendly_name']))
        self.yamaha.on = True
        while not self.yamaha.on:
            time.sleep(1)

    def _yamaha_set_input(self):
        self.log.info("{} Yamaha setting input to {}".format(
            self.cfg['yamaha']['friendly_name'],
            self.cfg['yamaha']['input']))
        self.yamaha.input = self.cfg['yamaha']['input']

    def _yamaha_set_volume(self):
        self.log.info("{} Yamaha setting volume to {}".format(
            self.cfg['yamaha']['friendly_name'],
            self.cfg['yamaha']['volume']))
        self.yamaha.volume = self.cfg['yamaha']['volume']

    def _started(self):
        if not self.yamaha.on:
            self._yamaha_on()
            self._yamaha_set_input()
            self._yamaha_set_volume()
        else:
            if self.yamaha.input != self.cfg['yamaha']['input']:
                self.log.info("{} Yamaha ignoring, it's already on".format(
                    self.cfg['yamaha']['friendly_name']))
                if self.cfg['notifications']['pushover']['enabled']:
                    notify = pushover(
                        self.cfg['notifications']['pushover']['user'],
                        api_token=self.cfg['notifications']['pushover']['app'])
                    notify.send_message(
                        "{} Yamaha ignoring SONOS because it is already on!"
                        .format(self.cfg['yamaha']['friendly_name']),
                        title="{} Yamaha".format(
                            self.cfg['yamaha']['friendly_name']))
            elif self.yamaha.volume != self.cfg['yamaha']['volume']:
                self._yamaha_set_volume()

    def _stopped(self):
        if self.yamaha.on:
            if self.yamaha.input == self.cfg['yamaha']['input']:
                self.log.info("{} Yamaha setting volume to {}".format(
                    self.cfg['yamaha']['friendly_name'],
                    self.cfg['yamaha']['off_volume']))
                self.yamaha.volume = self.cfg['yamaha']['off_volume']
                self.log.info("{} Yamaha turning off".format(
                    self.cfg['yamaha']['friendly_name']))
                self.yamaha.on = False
            else:
                self.log.info("{} Yamaha, SONOS ignored".format(
                    self.cfg['yamaha']['friendly_name']))

    def _status(self):
        if not self.status:
            self.log.info("{} SONOS Invalid Status: {}".format(
                self.cfg['sonos']['player_name'],
                self.event.variables))

        if self.last_status != self.status:
            self.log.info("{} SONOS: {}".format(
                self.cfg['sonos']['player_name'],
                self.status))

        if self.last_status != 'PLAYING' and self.status == 'PLAYING':
            self._started()

        if self.last_status != 'PAUSED_PLAYBACK' and \
                self.status == 'PAUSED_PLAYBACK' or \
                self.last_status != "STOPPED" and self.status == 'STOPPED':
            self._stopped()

        self.last_status = self.status

    def monitor(self):
        soco.config.EVENT_LISTENER_PORT = self.cfg['sonos']['event_port']
        self.sonos = soco.SoCo(
            self.cfg['sonos']['ip'])
        self.yamaha = rxv.RXV(
            self.cfg['yamaha']['ctrl_url'], self.cfg['yamaha']['model_name'])

        self.log.info("{} ({}) Power={}, Input={}, Volume={}".format(
            self.cfg['yamaha']['friendly_name'],
            self.cfg['yamaha']['model_name'],
            self.yamaha.on, self.yamaha.input, self.yamaha.volume))

        signal(SIGTERM, self.handle_sigterm)

        while self.break_loop is False:
            self._subscription()
            try:
                self.event = self.subscription.events.get(timeout=10)
                self.status = self.event.variables.get('transport_state')
                self._status()
            except Queue.Empty:
                pass
            except KeyboardInterrupt:
                self.handle_sigterm()
                break

        if self.break_loop:
            self.subscription.unsubscribe()
            soco.events.event_listener.stop()


def main():
    args = get_args()

    if args.scan:
        scan()
    elif args.zone:
        SonosYamahaMonitor(zone=args.zone)

if __name__ == "__main__":
    main()

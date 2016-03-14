#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import soco
import Queue
import signal
import argparse
import logging
import rxv
import yaml
from urlparse import urlparse

__version__ = '1.0'

logger = logging.getLogger(__name__)
lfmt = '%(asctime)s %(levelname)s %(name)s %(funcName)s %(lineno)d %(message)s'
lfmt = '%(asctime)s %(levelname)s %(funcName)s %(lineno)d %(message)s'
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
        self.break_loop = False

        self.find_cfg()
        if not self.state:
            self.log.error('error loading config.')
            return None
        self.log.info(self.cfg)

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
        print u"SIGTERM caught. Exiting gracefully.".encode('utf-8')
        self.break_loop = True

    def monitor(self):
        soco.config.EVENT_LISTENER_PORT = self.cfg['sonos']['event_port']
        connect = soco.SoCo(
            self.cfg['sonos']['ip'])
        yamaha = rxv.RXV(
            self.cfg['yamaha']['ctrl_url'], self.cfg['yamaha']['model_name'])

        subscription = None
        renewal_time = 120

        print u"Yamaha Power status:  {}".format(yamaha.on)
        print u"Yamaha Input select:  {}".format(yamaha.input)
        print u"Yamaha Volume:        {}".format(yamaha.volume)
        print

        self.break_loop = False
        last_status = None

        signal.signal(signal.SIGTERM, self.handle_sigterm)

        while self.break_loop is False:
            if not subscription or not subscription.is_subscribed or \
                    subscription.time_left <= 5:
                if subscription:
                    self.log.info("Unsubscribing from SONOS device events")
                    try:
                        subscription.unsubscribe()
                        soco.events.event_listener.stop()
                    except Exception as e:
                        self.log.info("Unsubscribe from SONOS failed")

                self.log.info("Subscribing to SONOS device events")
                try:
                    subscription = connect.avTransport.subscribe(
                        requested_timeout=renewal_time, auto_renew=True)
                except Exception as e:
                    self.log.info("Subscribe failed: {}".format(e))
                    time.sleep(10)
                    continue

            try:
                event = subscription.events.get(timeout=10)
                status = event.variables.get('transport_state')

                if not status:
                    self.log.info("Invalid SONOS status: {}"
                                  .format(event.variables))

                if last_status != status:
                    self.log.info("SONOS play status: {}".format(status))

                if last_status != 'PLAYING' and status == 'PLAYING':
                    if not yamaha.on:
                        self.log.info("Yamaha turning on")
                        yamaha.on = True
                        while not yamaha.on:
                            time.sleep(1)
                    if yamaha.volume != yamaha_volume:
                        self.log.info("Yamaha setting volume to {}"
                                      .format(yamaha_volume))
                        yamaha.volume = yamaha_volume
                    if yamaha.input != yamaha_input:
                        self.log.info("Yamaha setting input to {}"
                                      .format(yamaha_input))
                        yamaha.input = yamaha_input

                if last_status != 'PAUSED_PLAYBACK' and \
                        status == 'PAUSED_PLAYBACK':
                    if yamaha.on:
                        if yamaha.input == yamaha_input:
                            self.log.info("Yamaha turning off")
                            yamaha.on = False
                        else:
                            self.log.info(
                                "Ignoring Yamaha, SONOS doesn't have input")
                if last_status != 'STOPPED' and \
                        status == 'STOPPED':
                    if yamaha.on:
                        if yamaha.input == yamaha_input:
                            self.log.info("Yamaha turning off")
                            yamaha.on = False
                        else:
                            self.log.info(
                                "Ignoring Yamaha, SONOS doesn't have input")

                last_status = status
            except Queue.Empty:
                pass
            except KeyboardInterrupt:
                self.handle_sigterm()
                break

        if self.break_loop:
            subscription.unsubscribe()
            soco.events.event_listener.stop()


def main():
    args = get_args()

    if args.scan:
        scan()
    elif args.zone:
        SonosYamahaMonitor(zone=args.zone)

if __name__ == "__main__":
    main()

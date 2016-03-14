#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import time
import soco
import Queue
import signal
import argparse
import rxv
from urlparse import urlparse


__version__ = '1.0'

YAMAHA_IP = '10.0.10.41'
YAMAHA_PORT = 50000
YAMAHA_INPUT = 'AUDIO'
YAMAHA_VOLUME = -20.0
YAMAHA_SOUNDPRG = 'Straight'


def auto_flush_stdout():
    unbuffered = os.fdopen(sys.stdout.fileno(), 'w', 0)
    sys.stdout.close()
    sys.stdout = unbuffered


def handle_sigterm(*args):
    global break_loop
    print u"SIGTERM caught. Exiting gracefully.".encode('utf-8')
    break_loop = True


def monitor(sonos_ip, yamaha_ip, yamaha_input, yamaha_volume, event_port=1400):
    soco.config.EVENT_LISTENER_PORT = event_port
    connect = soco.SoCo(sonos_ip)
    yamaha = rxv.RXV(
        "http://{}:80/YamahaRemoteControl/ctrl".format(yamaha_ip), "HTR-4065")

    subscription = None
    renewal_time = 120

    print u"Yamaha Power status:  {}".format(yamaha.on)
    print u"Yamaha Input select:  {}".format(yamaha.input)
    print u"Yamaha Volume:        {}".format(yamaha.volume)
    print

    break_loop = False
    last_status = None

    """
    last_yamaha_on = yamaha.on
    last_yamaha_input = yamaha.input
    last_yamaha_volume = yamaha.volume
    """

    signal.signal(signal.SIGTERM, handle_sigterm)
    auto_flush_stdout()

    while break_loop is False:
        if not subscription or not subscription.is_subscribed or \
                subscription.time_left <= 5:
            if subscription:
                print "*** Unsubscribing from SONOS device events"
                try:
                    subscription.unsubscribe()
                    soco.events.event_listener.stop()
                except Exception as e:
                    print "*** Unsubscribe failed"

            print "*** Subscribing to SONOS device events"
            try:
                subscription = connect.avTransport.subscribe(
                    requested_timeout=renewal_time, auto_renew=True)
            except Exception as e:
                print "*** Subscribe failed: {}".format(e)
                time.sleep(10)
                continue

        try:
            event = subscription.events.get(timeout=10)
            status = event.variables.get('transport_state')

            if not status:
                print "Invalid SONOS status: {}".format(event.variables)

            if last_status != status:
                print "SONOS play status: {}".format(status)

            if last_status != 'PLAYING' and status == 'PLAYING':
                if not yamaha.on:
                    print "+++ Yamaha turning on"
                    yamaha.on = True
                    while not yamaha.on:
                        time.sleep(1)
                if yamaha.volume != yamaha_volume:
                    print "+++ Yamaha setting volume to {}".format(
                        yamaha_volume)
                    yamaha.volume = yamaha_volume
                if yamaha.input != yamaha_input:
                    print "+++ Yamaha setting input to {}".format(
                        yamaha_input)
                    yamaha.input = yamaha_input

            if last_status != 'PAUSED_PLAYBACK' and status == 'PAUSED_PLAYBACK':
                if yamaha.on:
                    if yamaha.input == yamaha_input:
                        print "--- Yamaha turning off"
                        yamaha.on = False
                    else:
                        print "--- Ignoring Yamaha, SONOS doesn't have input"
            if last_status != 'STOPPED' and status == 'STOPPED':
                if yamaha.on:
                    if yamaha.input == yamaha_input:
                        print "--- Yamaha turning off"
                        yamaha.on = False
                    else:
                        print "--- Ignoring Yamaha, SONOS doesn't have input"

            last_status = status
        except Queue.Empty:
            pass
        except KeyboardInterrupt:
            handle_sigterm()
            break

    if break_loop:
        subscription.unsubscribe()
        soco.events.event_listener.stop()


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

        print "{}: {} ({})\n\t\t{}".format(
            uri.hostname,
            rx.friendly_name,
            rx.model_name,
            rx.basic_status)


def get_args():
    parser = argparse.ArgumentParser(
        description="Sonos and Yamaha receiver monitor")

    parser.add_argument('--scan', action='store_true')
    parser.add_argument('--sonos', type=str, help='Sonos IP')
    parser.add_argument('--yamaha', type=str, help='Yamaha IP')
    parser.add_argument('--volume', type=float, help='Yamaha volume')
    parser.add_argument('--input', type=str, help='Yamaha input')
    parser.add_argument('--port', type=int, help='event port', default=1400)

    args = parser.parse_args()
    return args


def main():
    args = get_args()

    if args.scan:
        scan()
    else:
        monitor(
            sonos_ip=args.sonos,
            yamaha_ip=args.yamaha,
            yamaha_input=args.input,
            yamaha_volume=args.volume,
            event_port=args.port
        )


if __name__ == "__main__":
    main()

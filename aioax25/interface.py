#!/usr/bin/env python3

"""
AX.25 Interface handler
"""

import logging
import asyncio
import random
from functools import partial
from .signal import Signal
import re

from .frame import AX25Frame


class AX25Interface(object):
    """
    The AX25Interface class represents a logical AX.25 interface.
    The interface handles basic queueing and routing of message traffic.

    Outgoing messages are queued and sent when there is a break of greater
    than the cts_delay (250ms) + a randomisation factor (cts_rand).
    Messages may be cancelled prior to transmission.
    """

    def __init__(self, kissport, cts_delay=0.25,
            cts_rand=0.25, log=None, loop=None):
        if log is None:
            log = logging.getLogger(self.__class__.__module__)

        if loop is None:
            loop = asyncio.get_event_loop()

        self._log = log
        self._loop = loop
        self._port = kissport

        # Message queue
        self._tx_queue = []
        self._tx_pending = None

        # Clear-to-send delay and randomisation factor
        self._cts_delay = cts_delay
        self._cts_rand = cts_rand

        # Clear-to-send expiry
        self._cts_expiry = loop.time() \
                + cts_delay \
                + (random.random() * cts_rand)

        # Receivers
        self._receiver_str = {}
        self._receiver_re = {}

        # Received message call-back.  This is triggered whenever a message
        # comes in regardless of destination call-sign.
        self.received_msg = Signal()

        # Bind to the KISS port to receive raw messages.
        kissport.received.connect(self._on_receive)

    def bind(self, callback, callsign, ssid=0, regex=False):
        """
        Bind a receiver to the given call-sign and optional SSID.  The callsign
        argument is expected to be a string, but may also be a regular
        expression pattern which is then matched against the callsign (but not
        the SSID!).

        ssid may be set to None, which means all SSIDs.
        """
        if not isinstance(callsign, str):
            raise TypeError('callsign must be a string (use '
                            'regex=True for regex)')
        if regex:
            (_, call_receivers) = self._receiver_re.setdefault(
                    callsign,
                    (re.compile(callsign), {})
            )
        else:
            call_receivers = self._receiver_str.setdefault(
                    callsign,
                    {}
            )

        call_receivers.setdefault(ssid, []).append(callback)
            
    def unbind(self, callback, callsign, ssid=0, regex=False):
        """
        Unbind a receiver from the given callsign/SSID combo.
        """
        try:
            if regex:
                receivers = self._receiver_re
                (_, call_receivers) = receivers[callsign]
            else:
                receivers = self._receiver_str
                call_receivers = receivers[callsign]

            ssid_receivers = call_receivers[ssid]
        except KeyError:
            return

        try:
            ssid_receivers.remove(callback)
        except ValueError:
            return

        if len(ssid_receivers) == 0:
            call_receivers.pop(ssid)

        if len(call_receivers) == 0:
            receivers.pop(callsign)

    def transmit(self, frame, callback=None):
        """
        Enqueue a message for transmission.  Optionally give a call-back
        function to receive notification of transmission.
        """
        self._log.debug('Adding to queue: %s', frame)
        self._tx_queue.append((frame, callback))
        if not self._tx_pending:
            self._schedule_tx()

    def cancel_transmit(self, frame):
        """
        Cancel the transmission of a frame.
        """
        self._log.debug('Removing from queue: %s', frame)
        self._tx_queue = list(filter(
            lambda item : item[0] is not frame,
            self._tx_queue
        ))

    def _reset_cts(self):
        """
        Reset the clear-to-send timer.
        """
        cts_expiry = self._loop.time() \
                + self._cts_delay + (random.random() * self._cts_rand)

        # Ensure CTS expiry never goes backwards!
        while cts_expiry < self._cts_expiry:
            cts_expiry += (random.random() * self._cts_rand)
        self._cts_expiry = cts_expiry

        self._log.debug('Clear-to-send expiry at %s', self._cts_expiry)
        if self._tx_pending:
            # We were waiting for a clear-to-send, so re-schedule.
            self._schedule_tx()

    def _on_receive(self, frame):
        """
        Handle an incoming message.
        """
        # Decode from raw bytes
        frame = AX25Frame.decode(frame)
        self._log.debug('Handling incoming frame %s', frame)

        # Reset our CTS expiry since we just received a message.
        self._reset_cts()

        # Pass the message to those who elected to receive all traffic
        self._loop.call_soon(partial(
            self.received_msg.emit,
            interface=self, frame=frame))

        destination = frame.header.destination
        callsign = destination.callsign
        ssid = destination.ssid

        # Dispatch the incoming message notification to string match receivers
        calls = []
        try:
            callsign_receivers = self._receiver_str[callsign]
            calls.extend([
                partial(receiver, interface=self, frame=frame)
                for receiver in
                callsign_receivers.get(None, []) \
                            + callsign_receivers.get(ssid, [])
            ])
        except KeyError:
            pass

        # Compare the incoming frame destination to our regex receivers
        for (pattern, pat_receivers) in self._receiver_re.values():
            match = pattern.search(callsign)
            if not match:
                continue

            calls.extend([
                partial(receiver, interface=self, frame=frame, match=match)
                for receiver in
                pat_receivers.get(None, []) \
                        + pat_receivers.get(ssid, [])
            ])

        # Dispatch the received message
        self._log.debug('Dispatching frame to %d receivers', len(calls))
        for receiver in calls:
            self._loop.call_soon(receiver)

    def _schedule_tx(self):
        """
        Schedule the transmit timer to take place after the CTS expiry.
        """
        if self._tx_pending:
            self._tx_pending.cancel()

        delay = self._cts_expiry - self._loop.time()
        if delay > 0:
            self._log.debug('Scheduling next transmission in %s', delay)
            self._tx_pending = self._loop.call_later(delay, self._tx_next)
        else:
            self._log.debug('Scheduling next transmission ASAP')
            self._tx_pending = self._loop.call_soon(self._tx_next)

    def _tx_next(self):
        """
        Transmit the next message.
        """
        self._tx_pending = None

        try:
            (frame, callback) = self._tx_queue.pop(0)
        except IndexError:
            self._log.debug('No traffic to transmit')
            return

        try:
            self._log.debug('Transmitting %s', frame)
            self._port.send(frame)
            if callback:
                self._log.debug('Notifying sender of %s', frame)
                self._loop.call_soon(partial(
                    callback,
                    interface=self,
                    frame=frame
                ))
        except:
            self._log.exception('Failed to transmit %s', frame)

        self._reset_cts()
        if len(self._tx_queue) > 0:
            self._schedule_tx()

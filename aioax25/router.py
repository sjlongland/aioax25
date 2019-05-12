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


class Router(object):
    """
    The Router routes incoming messages to receivers.  It is a mix-in class
    used by AX25Interface.  The base class is assumed to have IOLoop and
    logger instances
    """

    def __init__(self):
        # Receivers
        self._receiver_str = {}
        self._receiver_re = {}

        # Received message call-back.  This is triggered whenever a message
        # comes in regardless of destination call-sign.
        self.received_msg = Signal()

    def _get_destination(self, frame):
        """
        Retrieve the destination of the given frame and return it.
        """
        return frame.header.destination

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

    def _on_receive(self, frame):
        """
        Handle an incoming message.
        """
        # Decode from raw bytes
        if not isinstance(frame, AX25Frame):
            frame = AX25Frame.decode(frame)
        self._log.debug('Handling incoming frame %s', frame)

        # Pass the message to those who elected to receive all traffic
        self._loop.call_soon(partial(
            self.received_msg.emit,
            interface=self, frame=frame))

        destination = self._get_destination(frame)
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

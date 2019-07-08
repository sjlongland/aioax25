#!/usr/bin/env python3

"""
APRS Digipeating module
"""

import logging
import weakref
import re
import time
from ..frame import AX25FrameHeader, AX25Address

# APRS WIDEn/TRACEn regular expression pattern
DIGI_RE = re.compile(r'^(WIDE|TRACE)(\d)$')

class APRSDigipeater(object):
    """
    The APRSDigipeater class implemenets a pure WIDEn-N style digipeater
    handler, hooking into the Router handling hooks and editing the
    digipeater path of all unique APRS messages seen.
    """

    def __init__(self, digipeat_timeout=5.0, log=None):
        """
        Create a new digipeater module instance.
        """
        if log is None:
            log = logging.getLogger(self.__class__.__module__)
        self._digipeat_timeout = digipeat_timeout
        self._log = log
        self._mydigi = set()

    @property
    def mydigi(self):
        """
        Return the set of digipeater calls and aliases this digi responds to.
        """
        return self._mydigi.copy()

    @mydigi.setter
    def mydigi(self, aliases):
        """
        Replace the list of digipeater calls and aliases this digi responds to.
        """
        self._mydigi = set([
            AX25Address.decode(call).normalised
            for call in aliases
        ])

    def addaliases(self, *aliases):
        """
        Add one or more aliases to the digipeater handler.
        """
        for call in aliases:
            self._mydigi.add(AX25Address.decode(call).normalised)

    def rmaliases(self, *aliases):
        """
        Remove one or more aliases from the digipeater handler.
        """
        for call in aliases:
            self._mydigi.discard(AX25Address.decode(call).normalised)

    def connect(self, aprsint, addcall=True):
        """
        Connect to an APRS interface.  This hooks the received_msg signal
        to receive (de-duplicated) incoming traffic and adds the APRS
        interface's call-sign/SSID to the "mydigi" list.

        Note that a message is digipeated on the interface it was received
        *ONLY*.  Cross-interface digipeating is not implemented at this time.
        """
        self._log.debug('Connecting to %s (add call %s)', aprsint, addcall)
        aprsint.received_msg.connect(self._on_receive)
        if addcall:
            self.addaliases(aprsint.mycall)

    def disconnect(self, aprsint, rmcall=True):
        """
        Disconnect from an APRS interface.  This removes the hook to the
        received_msg signal and removes that APRS interface's call-sign/SSID
        from the "mydigi" list.
        """
        if rmcall:
            self.rmaliases(aprsint.mycall)
        aprsint.received_msg.disconnect(self._on_receive)

    def _on_receive(self, interface, frame, **kwargs):
        """
        Handle the incoming to-be-digipeated message.
        """
        # First, have we already digipeated this?
        self._log.debug('On receive call-back: interface=%s, frame=%s',
                interface, frame)
        mycall = interface.mycall
        idx = None
        alias = None
        rem_hops = None

        prev = None
        for (digi_idx, digi) in enumerate(frame.header.repeaters):
            if digi.normalised in self._mydigi:
                self._log.debug('MYDIGI digipeat for %s, last was %s',
                        digi, prev)
                if ((prev is None) or prev.ch) and (not digi.ch):
                    # This is meant to be directly digipeated by us!
                    outgoing = frame.copy(
                        header=AX25FrameHeader(
                            destination=frame.header.destination,
                            source=frame.header.source,
                            repeaters=frame.header.repeaters.replace(
                                alias=digi,
                                address=mycall.copy(ch=True)
                            ),
                            cr=frame.header.cr
                        )
                    )
                    outgoing.deadline = time.time() + self._digipeat_timeout
                    self._on_transmit(
                            interface=interface,
                            alias=alias,
                            frame=outgoing
                    )
                return
            else:
                # Is this a WIDEn/TRACEn call?
                match = DIGI_RE.match(digi.callsign)
                self._log.debug('WIDEn-N?  digi=%s match=%s', digi, match)
                if match:
                    # It is
                    idx = digi_idx
                    alias = digi
                    rem_hops = min(digi.ssid, int(match.group(2)))
                    break
                else:
                    prev = digi

        if alias is None:
            # The path did not mention a WIDEn digi call
            self._log.debug('No alias, ignoring frame')
            return

        if rem_hops == 0:
            # Number of hops expired, do not digipeat this
            self._log.debug('Hops exhausted, ignoring frame')
            return

        # This is to be digipeated.
        digi_path = list(frame.header.repeaters[:idx]) \
                + [mycall.copy(ch=True)]
        if rem_hops > 1:
            # There are more hops left, tack the next hop on
            digi_path.append(alias.copy(
                    ssid=rem_hops - 1,
                    ch=False
            ))
        digi_path.extend(frame.header.repeaters[idx+1:])

        outgoing = frame.copy(
            header=AX25FrameHeader(
                destination=frame.header.destination,
                source=frame.header.source,
                repeaters=digi_path,
                cr=frame.header.cr
            )
        )

        outgoing.deadline = time.time() + self._digipeat_timeout

        self._on_transmit(
                interface=interface,
                alias=alias,
                frame=outgoing
        )

    def _on_transmit(self, interface, alias, frame):
        """
        Transmit a message to be digipeated.  This function is a wrapper
        around the interface.transmit method so we can support subclasses
        that do more advanced routing such as cross-interface digipeating.
        """
        interface.transmit(frame)

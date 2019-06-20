#!/usr/bin/env python3

"""
APRS Digipeating module
"""

import weakref
import re
from ..frame import AX25FrameHeader, AX25Address

# APRS WIDEn regular expression pattern
DIGI_RE = re.compile(r'^WIDE(\d)$')

class APRSDigipeater(object):
    """
    The APRSDigipeater class implemenets a pure WIDEn-N style digipeater
    handler, hooking into the Router handling hooks and editing the
    digipeater path of all unique APRS messages seen.
    """

    def __init__(self, aprsint, mydigi=None):
        aprsint.received_msg.connect(self._on_receive)
        self._mydigi = set([
            AX25Address.decode(call)
            for call in ((mydigi or []) + [aprsint.mycall])
        ])

    def _on_receive(self, interface, frame, **kwargs):
        """
        Handle the incoming to-be-digipeated message.
        """
        # First, have we already digipeated this?
        mycall = interface.mycall
        idx = None
        alias = None
        rem_hops = None

        prev = None
        for (digi_idx, digi) in enumerate(frame.header.repeaters):
            if digi.normalised in self._mydigi:
                if ((prev is None) or prev.ch) and (not digi.ch):
                    # This is meant to be directly digipeated by us!
                    interface.transmit(
                        frame.copy(
                            header=AX25FrameHeader(
                                destination=frame.header.destination,
                                source=frame.header.source,
                                repeaters=frame.header.repeaters.replace(
                                    alias=digi, address=mycall.copy(ch=True)
                                ),
                                cr=frame.header.cr
                            )
                        )
                    )
                return
            else:
                # Is this a WIDEn call?
                match = DIGI_RE.match(digi.callsign)
                if match:
                    # It is
                    idx = digi_idx
                    alias = digi
                    rem_hops = min(digi.ssid, int(match.group(1)))
                    break
                else:
                    prev = digi

        if alias is None:
            # The path did not mention a WIDEn digi call
            return

        if rem_hops == 0:
            # Number of hops expired, do not digipeat this
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

        interface.transmit(
            frame.copy(
                header=AX25FrameHeader(
                    destination=frame.header.destination,
                    source=frame.header.source,
                    repeaters=digi_path,
                    cr=frame.header.cr
                )
            )
        )

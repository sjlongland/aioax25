#!/usr/bin/env python3

"""
AX.25 Station interface.

This implements the base-level AX.25 logic for a station listening at a given
SSID.
"""


import logging
import asyncio
from .signal import Signal
import weakref

from .frame import AX25Address, AX25Path, AX25TestFrame

from .peer import AX25Peer
from .version import AX25Version


class AX25Station(object):
    """
    The AX25Station class represents the station on the AX.25 network
    implemented by the caller of this library.  Notably, it provides
    hooks for handling incoming connections, and methods for making
    connections to other AX.25 stations.

    To be able to participate as a connected-mode station, create an instance
    of AX25Station, referencing an instance of AX25Interface as the interface
    parameter; then call the attach method.
    """

    def __init__(self, interface,
            # Station call-sign and SSID
            callsign, ssid=None,
            # Classes of Procedures options
            full_duplex=False,
            # HDLC Optional Functions
            modulo128=False,        # Whether to use Mod128 by default
            reject_mode=AX25Peer.AX25RejectMode.SELECTIVE_RR,
                                    # What reject mode to use?
            # Parameters (AX.25 2.2 sect 6.7.2)
            max_ifield=256,         # aka N1
            max_ifield_rx=256,      # the N1 we advertise in XIDs
            max_retries=10,         # aka N2, value from figure 4.5
            # k value, for mod128 and mod8 connections, this sets the
            # advertised window size in XID.  Peer station sets actual
            # value used here.
            max_outstanding_mod8=7,
            max_outstanding_mod128=127,
            # Timer parameters
            ack_timeout=3.0,        # Acknowledge timeout (aka T1)
            idle_timeout=900.0,     # Idle timeout before we "forget" peers
            rr_delay=10.0,          # Delay between I-frame and RR
            rr_interval=30.0,       # Poll interval when peer in busy state
            rnr_interval=10.0,      # Delay between RNRs when busy
            # Protocol version to use for our station
            protocol=AX25Version.AX25_22,
            # IOLoop and logging
            log=None, loop=None):

        if log is None:
            log = logging.getLogger(self.__class__.__module__)

        if loop is None:
            loop = asyncio.get_event_loop()

        # Ensure we are running a supported version of AX.25
        protocol = AX25Version(protocol)
        if protocol not in (AX25Version.AX25_20, AX25Version.AX25_22):
            raise ValueError('%r not a supported AX.25 protocol version'\
                    % protocol.value)

        # Configuration parameters
        self._address = AX25Address.decode(callsign, ssid).normalised
        self._interface = weakref.ref(interface)
        self._protocol = protocol
        self._ack_timeout = ack_timeout
        self._idle_timeout = idle_timeout
        self._reject_mode = AX25Peer.AX25RejectMode(reject_mode)
        self._modulo128 = modulo128
        self._max_ifield = max_ifield
        self._max_ifield_rx = max_ifield_rx
        self._max_retries = max_retries
        self._max_outstanding_mod8 = max_outstanding_mod8
        self._max_outstanding_mod128 = max_outstanding_mod128
        self._rr_delay = rr_delay
        self._rr_interval = rr_interval
        self._rnr_interval = rnr_interval
        self._log = log
        self._loop = loop

        # Remote station handlers
        self._peers = {}

        # Signal emitted when a SABM(E) is received
        self.connection_request = Signal()

    @property
    def address(self):
        """
        Return the source address of this station.
        """
        return self._address

    @property
    def protocol(self):
        """
        Return the protocol version of this station.
        """
        return self._protocol

    def attach(self):
        """
        Connect the station to the interface.
        """
        interface = self._interface()
        interface.bind(self._on_receive,
                callsign=self.address.callsign,
                ssid=self.address.ssid,
                regex=False)

    def detach(self):
        """
        Disconnect from the interface.
        """
        interface = self._interface()
        interface.unbind(self._on_receive,
                callsign=self.address.callsign,
                ssid=self.address.ssid,
                regex=False)

    def getpeer(self, callsign, ssid=None, repeaters=None,
            create=True, **kwargs):
        """
        Retrieve an instance of a peer context.  This creates the peer
        object if it doesn't already exist unless create is set to False
        (in which case it will raise KeyError).
        """
        address = AX25Address.decode(callsign, ssid).normalised
        try:
            return self._peers[address]
        except KeyError:
            if not create:
                raise
            pass

        # Not there, so set some defaults, then create
        kwargs.setdefault('reject_mode', self._reject_mode)
        kwargs.setdefault('modulo128', self._modulo128)
        kwargs.setdefault('max_ifield', self._max_ifield)
        kwargs.setdefault('max_ifield_rx', self._max_ifield_rx)
        kwargs.setdefault('max_retries', self._max_retries)
        kwargs.setdefault('max_outstanding_mod8', self._max_outstanding_mod8)
        kwargs.setdefault('max_outstanding_mod128', self._max_outstanding_mod128)
        kwargs.setdefault('rr_delay', self._rr_delay)
        kwargs.setdefault('rr_interval', self._rr_interval)
        kwargs.setdefault('rnr_interval', self._rnr_interval)
        kwargs.setdefault('ack_timeout', self._ack_timeout)
        kwargs.setdefault('idle_timeout', self._idle_timeout)
        kwargs.setdefault('protocol', AX25Version.UNKNOWN)
        peer = AX25Peer(self, address,
                repeaters=AX25Path(*(repeaters or [])),
                log=self._log.getChild('peer.%s' % address),
                loop=self._loop,
                **kwargs)
        self._peers[address] = peer
        return peer

    def _drop_peer(self, peer):
        """
        Drop a peer.  This is called by the peer when its idle timeout expires.
        """
        self._peers.pop(peer.address, None)

    def _on_receive(self, frame, **kwargs):
        """
        Handling of incoming messages.
        """
        if frame.header.cr:
            # This is a command frame
            self._log.debug('Checking command frame sub-class: %s', frame)
            if isinstance(frame, AX25TestFrame):
                # A TEST request frame, context not required
                return self._on_receive_test(frame)

        # If we're still here, then we don't handle unsolicited frames
        # of this type, so pass it to a handler if we have one.
        peer = self.getpeer(frame.header.source,
                repeaters=frame.header.repeaters.reply)
        self._log.debug('Passing frame to peer %s: %s', peer.address, frame)
        peer._on_receive(frame)

    def _on_receive_test(self, frame):
        """
        Handle a TEST frame.
        """
        # The frame is a test request.
        self._log.debug('Responding to test frame: %s', frame)
        interface = self._interface()
        interface.transmit(
                AX25TestFrame(
                    destination=frame.header.source,
                    source=self.address,
                    repeaters=frame.header.repeaters.reply,
                    payload=frame.payload,
                    cr=False
                )
        )

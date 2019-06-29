#!/usr/bin/env python3

"""
APRS messaging handler.
"""

import asyncio
import logging
from functools import partial

from ..signal import Signal
from hashlib import sha256

from .router import APRSRouter
from ..frame import AX25Address
from .frame import APRSFrame
from .message import APRSMessageHandler, \
        APRSMessageFrame, APRSMessageAckFrame, APRSMessageRejFrame


class APRSInterface(APRSRouter):
    def __init__(self, ax25int, mycall,
            # Retransmission parameters
            retransmit_count=4, retransmit_timeout_base=30,
            retransmit_timeout_rand=10, retransmit_timeout_scale=1.5,
            # Destination call to use for our traffic
            aprs_destination='APZAIO',
            # Path to use when sending APRS messages
            aprs_path=['WIDE1-1','WIDE2-1'],
            # Maximum message ID modulo function
            msgid_modulo=1000,
            # Length of time in seconds before duplicates expire
            deduplication_expiry=28,
            # Logger instance
            log=None):

        super(APRSRouter, self).__init__()
        if log is None:
            log = logging.getLogger(self.__class__.__module__)

        self._log = log

        # Use the same loop as parent AX.25 interface
        self._loop = ax25int._loop

        # Retransmission settings
        self._retransmit_timeout_base = retransmit_timeout_base
        self._retransmit_timeout_rand = retransmit_timeout_rand
        self._retransmit_timeout_scale = retransmit_timeout_scale
        self._retransmit_count = retransmit_count

        # AX.25 set-up
        self._ax25int = ax25int
        self._mycall = AX25Address.decode(mycall).normalised

        # Bind to receive all traffic.
        # Whilst there's a list of destination calls for conventional APRS,
        # MIC-e derives the destination from the latitude of the station, thus
        # it could be *ANYTHING*.
        self._ax25int.received_msg.connect(self._on_receive)

        # Message ID counter
        self._msgid = 0

        # Message ID modulo
        self._msgid_modulo = msgid_modulo

        # APRS destination address for broadcast messages
        self._aprs_destination = AX25Address.decode(
                aprs_destination).normalised

        # APRS digi path
        self._aprs_path = [
                AX25Address.decode(call).normalised
                for call in
                aprs_path or []
        ]

        # Pending messages, by addressee and message ID
        self._pending_msg = {}

        # The messages seen in the last `deduplication_expiry` seconds
        self._msg_expiry = {}
        # Length of time to keep message hashes
        self._deduplication_expiry = deduplication_expiry
        # Time-out handle for deduplication
        self._deduplication_timeout = None

        # Received addressed message call-back.  This fires when a message's
        # addressee field matches 'mycall'
        self.received_addressed_msg = Signal()

    @property
    def mycall(self):
        return self._mycall.copy()

    def send_message(self, addressee, message, path=None, oneshot=False):
        """
        Send a APRS message to the named addressee.
        """
        if path is None:
            self._log.debug('Setting default path for message to %s',
                    addressee)
            path=self._aprs_path

        if oneshot:
            # One-shot mode, just fire and forget!
            self._log.info('Send one-shot to %s: %s',
                    addressee, message)

            self.transmit(APRSMessageFrame(
                    destination=addressee,
                    source=self.mycall,
                    addressee=addressee,
                    message=message,
                    msgid=None,
                    repeaters=path
            ))
            return

        handler = APRSMessageHandler(self, addressee, path, message,
                self._log.getChild('message'))
        self._pending_msg[handler.msgid] = handler
        handler._send()
        return handler

    def send_response(self, message, ack=True):
        """
        Send a ACK (or if ack=False, REJ) to a numbered message.
        """
        if message.msgid is None:
            return

        self._log.debug('Responding to message %s with ack=%s',
                message, ack)
        self.send_message(
                addressee=message.header.source.normalised,
                path=message.header.repeaters.reply \
                        if message.header.repeaters is not None else None,
                message='%s%s' % ('ack' if ack else 'rej', message.msgid),
                oneshot=True
        )

    @classmethod
    def _hash_frame(cls, frame):
        """
        Generate a hash of the given frame.
        """
        framehash = sha256()
        framehash.update(bytes(frame.header.destination))
        framehash.update(bytes(frame.header.source))
        framehash.update(bytes(frame.control))
        framehash.update(bytes(frame.frame_payload))
        return framehash.digest()

    def _test_or_add_frame(self, frame):
        """
        Hash the given frame, and test to see if it has been seen.
        """
        framedigest = self._hash_frame(frame)
        expiry = self._msg_expiry.get(framedigest, 0)
        if expiry > self._loop.time():
            # We've seen this before.
            return True

        self._msg_expiry[framedigest] = \
                self._loop.time() + self._deduplication_expiry
        self._loop.call_soon(self._schedule_dedup_cleanup)
        return False

    def _schedule_dedup_cleanup(self):
        """
        Schedule a clean-up.
        """
        if self._deduplication_timeout is not None:
            self._deduplication_timeout.cancel()
            self._deduplication_timeout = None

        if len(self._msg_expiry) == 0:
            return

        delay = min(self._msg_expiry.values()) - self._loop.time()
        if delay > 0:
            self._deduplication_timeout = \
                    self._loop.call_later(delay, self._dedup_cleanup)
        else:
            self._loop.call_soon(self._dedup_cleanup)

    def _dedup_cleanup(self):
        """
        Clean up the duplicated message cache.
        """
        now = self._loop.time()
        self._deduplication_timeout = None
        for digest, time in list(self._msg_expiry.items()):
            if time < now:
                self._msg_expiry.pop(digest, None)

        self._loop.call_soon(self._schedule_dedup_cleanup)

    def _on_receive(self, frame, **kwargs):
        """
        Handle the incoming frame.
        """
        if self._test_or_add_frame(frame):
            self._log.debug('Ignoring duplicate frame: %s', frame)
            return

        try:
            frame = APRSFrame.decode(frame, self._log.getChild('decode'))
            self._log.debug('Processing incoming message %s (type %s)',
                    frame, frame.__class__.__name__)

            # Pass to the super-class handler
            self._loop.call_soon(partial(
                super(APRSInterface, self)._on_receive,
                frame
            ))

            if isinstance(frame, APRSMessageFrame):
                # This is a message, is it for us?
                if frame.addressee == self.mycall:
                    # Is it a response for us?
                    if isinstance(frame, (APRSMessageAckFrame, \
                        APRSMessageRejFrame)):
                        msgid = frame.msgid

                        handler = self._pending_msg.get(msgid)
                        self._log.debug(
                                'Response to %r (pending %r), handler %s',
                                msgid, list(self._pending_msg.keys()), handler)
                        if handler:
                            self._loop.call_soon(handler._on_response, frame)
                            # This is dealt with
                            return
                    else:
                        # This is a message addressed to us.
                        self._loop.call_soon(partial(
                            self.received_addressed_msg.emit,
                            interface=self, frame=frame
                        ))
                else:
                    self._log.debug('Addressee is %s, mycall %s, not for us',
                            frame.addressee, self.mycall)
        except:
            self._log.exception('Exception occurred emitting signal')

    def transmit(self, frame):
        """
        Send an AX.25 frame.
        """
        self._log.info('Sending %s', frame)
        try:
            self._ax25int.transmit(frame)
            self._test_or_add_frame(frame)
        except:
            self._log.exception('Failed to send %s', frame)

    @property
    def _next_msgid(self):
        """
        Return the next message ID
        """
        self._msgid = (self._msgid + 1) % self._msgid_modulo
        return str(self._msgid)

    def _on_msg_handler_finish(self, msgid):
        self._pending_msg.pop(msgid, None)

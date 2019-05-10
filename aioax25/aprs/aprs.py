#!/usr/bin/env python3

"""
APRS messaging handler.
"""

import re
import weakref
import random
import asyncio
import logging
from ..signal import Signal
from hashlib import sha256
from enum import Enum

from ..frame import AX25UnnumberedInformationFrame, AX25Address


# APRS data types
class APRSDataType(Enum):
    """
    APRS message types, given as the first byte in the information field,
    not including unused or reserved types.  Page 17 of APRS 1.0.1 spec.
    """
    MIC_E_BETA0         = 0x1c
    MIC_E_OLD_BETA0     = 0x1d
    POSITION            = ord('!')
    PEET_BROS_WX1       = ord('#')
    RAW_GPRS_ULT2K      = ord('$')
    AGRELO_DFJR         = ord('%')
    RESERVED_MAP        = ord('&')
    MIC_E_OLD           = ord("'")
    ITEM                = ord(')')
    PEET_BROS_WX2       = ord('*')
    TEST_DATA           = ord(',')
    POSITION_TS         = ord('/')
    MESSAGE             = ord(':')
    OBJECT              = ord(';')
    STATIONCAP          = ord('<')
    POSITION_MSGCAP     = ord('=')
    STATUS              = ord('>')
    QUERY               = ord('?')
    POSITION_TS_MSGCAP  = ord('@')
    TELEMETRY           = ord('T')
    MAIDENHEAD          = ord('[')
    WX                  = ord('_')
    MIC_E               = ord('`')
    USER_DEFINED        = ord('{')
    THIRD_PARTY         = ord('}')


class APRSHandler(object):
    def __init__(self, kissint, mycall,
            # Retransmission parameters
            retransmit_count=4, retransmit_timeout_base=30,
            retransmit_timeout_rand=10, retransmit_timeout_scale=1.5,
            # Destination call to use for our traffic
            aprs_destination='APZAIO',
            # Path to use when sending APRS messages
            aprs_path=['WIDE1-1','WIDE2-1'],
            # AX.25 destination SSIDs to listen for
            listen_destinations=[
                # APRS 1.0.1 protocol specification page 13
                dict(callsign='^AIR',   regex=True,     ssid=None), # Legacy
                dict(callsign='^ALL',   regex=True,     ssid=None),
                dict(callsign='^AP',    regex=True,     ssid=None),
                dict(callsign='BEACON', regex=False,    ssid=None),
                dict(callsign='^CQ',    regex=True,     ssid=None),
                dict(callsign='^GPS',   regex=True,     ssid=None),
                dict(callsign='^DF',    regex=True,     ssid=None),
                dict(callsign='^DGPS',  regex=True,     ssid=None),
                dict(callsign='^DRILL', regex=True,     ssid=None),
                dict(callsign='^ID',    regex=True,     ssid=None),
                dict(callsign='^JAVA',  regex=True,     ssid=None),
                dict(callsign='^MAIL',  regex=True,     ssid=None),
                dict(callsign='^MICE',  regex=True,     ssid=None),
                dict(callsign='^QST',   regex=True,     ssid=None),
                dict(callsign='^QTH',   regex=True,     ssid=None),
                dict(callsign='^RTCM',  regex=True,     ssid=None),
                dict(callsign='^SKY',   regex=True,     ssid=None),
                dict(callsign='^SPACE', regex=True,     ssid=None),
                dict(callsign='^SPC',   regex=True,     ssid=None),
                dict(callsign='^SYM',   regex=True,     ssid=None),
                dict(callsign='^TEL',   regex=True,     ssid=None),
                dict(callsign='^TEST',  regex=True,     ssid=None),
                dict(callsign='^TLM',   regex=True,     ssid=None),
                dict(callsign='^WX',    regex=True,     ssid=None),
                dict(callsign='^ZIP',   regex=True,     ssid=None)  # Legacy
            ],
            # listen_altnets uses the same format as listen_destinations
            # and adds *additional* altnets using the same specification
            listen_altnets=None,
            # Maximum message ID modulo function
            msgid_modulo=1000,
            # Length of time in seconds before duplicates expire
            deduplication_expiry=28,
            # Logger and IOLoop instance
            log=None, loop=None):
        if log is None:
            log = logging.getLogger(self.__class__.__module__)
        if loop is None:
            loop = asyncio.get_event_loop()

        self._log = log
        self._loop = loop

        # Retransmission settings
        self._retransmit_timeout_base = retransmit_timeout_base
        self._retransmit_timeout_rand = retransmit_timeout_rand
        self._retransmit_timeout_scale = retransmit_timeout_scale
        self._retransmit_count = retransmit_count

        # AX.25 set-up
        self._kissint = kissint
        self._mycall = AX25Address.decode(mycall).normalised

        # Bind to receive traffic:
        for spec in [
                dict(callsign=self._mycall.callsign,
                    ssid=self._mycall.ssid, regex=False)
                ] + listen_destinations + (listen_altnets or []):
            kissint.bind(self._on_receive_msg, **spec)

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

        # Signal for emitting new messages
        self.received_msg = Signal()

        # Pending messages, by addressee and message ID
        self._pending_msg = {}

        # The messages seen in the last `deduplication_expiry` seconds
        self._msg_expiry = {}
        # Length of time to keep message hashes
        self._deduplication_expiry = deduplication_expiry
        # Time-out handle for deduplication
        self._deduplication_timeout = None

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

            self._send(APRSMessageFrame(
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
        if len(self._msg_expiry) == 0:
            return

        if self._deduplication_timeout is not None:
            self._deduplication_timeout.cancel()
            self._deduplication_timeout = None

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

    def _on_receive_msg(self, frame):
        """
        Handle the incoming frame.
        """
        if self._test_or_add_frame(frame):
            self._log.debug('Ignoring duplicate frame: %s', frame)
            return

        try:
            message = APRSFrame.decode(frame, self._log.getChild('decode'))
            self._log.debug('Processing incoming message %s (type %s)',
                    message, message.__class__.__name__)

            if isinstance(message, (APRSMessageAckFrame, APRSMessageRejFrame)):
                # This is a response to a message, one of ours?
                if message.addressee == self.mycall:
                    # Addressed to us
                    msgid = message.msgid

                    handler = self._pending_msg.get(msgid)
                    self._log.debug('Response to %r (pending %r), handler %s',
                            msgid, list(self._pending_msg.keys()), handler)
                    if handler:
                        handler._on_response(message)
                        # This is dealt with
                        return
                else:
                    self._log.debug('Addressee is %s, mycall %s, not for us',
                            message.addressee, self.mycall)

            # Pass to the generic handler
            self.received_msg.emit(message=message)
        except:
            self._log.exception('Exception occurred emitting signal')

    def _send(self, message):
        """
        Send an AX.25 frame message.
        """
        self._log.info('Sending %s', message)
        try:
            self._kissint.transmit(message)
        except:
            self._log.exception('Failed to send %s', message)

    @property
    def _next_msgid(self):
        """
        Return the next message ID
        """
        self._msgid = (self._msgid + 1) % self._msgid_modulo
        return str(self._msgid)

    def _on_msg_handler_finish(self, msgid):
        self._pending_msg.pop(msgid, None)


class APRSMessageHandler(object):
    """
    The APRS message handler is a helper class that handles the
    retransmissions, timeouts and responses to an APRS message.
    """
    class HandlerState(Enum):
        INIT    = 0
        SEND    = 1
        RETRY   = 2
        SUCCESS = 3
        REJECT  = -1
        CANCEL  = -2
        TIMEOUT = -3
        FAIL    = -4

    def __init__(self, aprshandler, addressee, path, message, log):
        self._log = log
        # Initialise our timer and retry counter
        self._timeout_duration \
                = aprshandler._retransmit_timeout_base \
                + (random.random() * aprshandler._retransmit_timeout_rand)
        self._retransmit_count = aprshandler._retransmit_count
        self._retransmit_timeout_scale = aprshandler._retransmit_timeout_scale
        self._loop = aprshandler._loop
        self._tx_frame = APRSMessageFrame(
                destination=addressee,
                source=aprshandler.mycall,
                addressee=addressee,
                message=message,
                msgid=aprshandler._next_msgid,
                repeaters=[
                    AX25Address.decode(call).normalised for call in path
                ]
        )

        self._aprshandler = weakref.ref(aprshandler)
        self._retransmit_timeout = None
        self._response = None

        self.done = Signal()
        self._state = self.HandlerState.INIT
        self._log.debug('Initialised handler for %s state %s',
                self.msgid, self.state)

    @property
    def frame(self):
        return self._tx_frame

    @property
    def addressee(self):
        return self._tx_frame.addressee

    @property
    def msgid(self):
        return self._tx_frame.msgid

    @property
    def state(self):
        return self._state

    @property
    def response(self):
        return self._response

    def cancel(self):
        self._stop_timer()
        self._enter_state(self.HandlerState.CANCEL)

    def _send(self):
        # Stop any timers
        self._stop_timer()

        self._log.info('Preparing to send %s (state %s)',
                self.msgid, self.state)

        # What state are we in?
        if self.state == self.HandlerState.INIT:
            next_state = self.HandlerState.SEND
        elif self.state in (self.HandlerState.SEND, self.HandlerState.RETRY):
            # Have we exhausted the retries?
            if self._retransmit_count <= 0:
                self._enter_state(self.HandlerState.TIMEOUT)
                return
            self._retransmit_count -= 1
            next_state = self.HandlerState.RETRY
        else:
            self._log.warning('Attempt to send %s in state %s',
                    self.msgid, self.state)
            raise RuntimeError('Incorrect state %s' % self.state)

        handler = self._aprshandler()
        if handler is None:
            # No handler, so can't send
            self._enter_state(self.HandlerState.FAIL)
            return

        # Set the time-out timer
        self._retransmit_timeout = self._loop.call_later(
                self._timeout_duration,
                self._on_timeout
        )
        self._timeout_duration *= self._retransmit_timeout_scale

        # Send the frame
        handler._send(self.frame)
        self._enter_state(next_state)

    def _stop_timer(self):
        self._log.debug('Cancelling timer for %s', self.msgid)
        if self._retransmit_timeout is not None:
            self._retransmit_timeout.cancel()
            self._retransmit_timeout = None

    def _on_timeout(self):
        self._log.warning('Time-out waiting for reponse to %s', self.frame)
        self._loop.call_soon(self._send)

    def _on_response(self, response):
        self._stop_timer()
        self._log.info('%s Received response %s to frame %s',
                self.msgid, response, self.frame)
        if self.state not in (self.HandlerState.SEND, self.HandlerState.RETRY):
            # Ignore the message, we are no longer interested
            return

        self._response = response
        if isinstance(response, APRSMessageAckFrame):
            self._enter_state(self.HandlerState.SUCCESS)
        else:
            self._enter_state(self.HandlerState.REJECT)

    def _enter_state(self, state):
        self._log.debug('%s entering state %s', self.msgid, state)
        self._state = state
        if state in (self.HandlerState.SUCCESS,
                    self.HandlerState.REJECT,
                    self.HandlerState.TIMEOUT,
                    self.HandlerState.CANCEL):
            self._log.info('%s is done', self.frame)
            # These are final states.
            handler = self._aprshandler()
            if handler:
                handler._on_msg_handler_finish(self.msgid)
            self.done.emit(handler=self, state=state)


class APRSFrame(AX25UnnumberedInformationFrame):
    """
    This is a helper sub-class for encoding and decoding APRS messages into
    AX.25 frames.
    """

    DATA_TYPE_HANDLERS = {}

    @classmethod
    def decode(cls, uiframe, log):
        """
        Decode the given UI frame (AX25UnnumberedInformationFrame) to a
        suitable APRSFrame sub-class.
        """
        # Do not decode if not the APRS PID value
        if uiframe.pid != cls.PID_NO_L3:
            # Clearly not an APRS message
            log.debug('Frame has wrong PID for APRS')
            return uiframe

        if len(uiframe.payload) == 0:
            log.debug('Frame has no payload data')
            return uiframe

        try:
            # Inspect the first byte.
            type_code = APRSDataType(uiframe.payload[0])
            handler_class = cls.DATA_TYPE_HANDLERS[type_code]

            # Decode the payload as text
            payload = uiframe.payload.decode('US-ASCII')

            return handler_class.decode(uiframe, payload, log)
        except:
            # Not decodable, leave as-is
            log.debug('Failed to decode as APRS', exc_info=1)
            return uiframe

    def __init__(self, destination, source, payload, repeaters=None,
            pf=False, cr=False):
        super(APRSFrame, self).__init__(
                destination=destination,
                source=source,
                pid=self.PID_NO_L3, # APRS spec
                payload=payload,
                repeaters=repeaters,
                pf=pf, cr=cr)


class APRSMessageFrame(APRSFrame):

    MSGID_RE = re.compile(r'{([0-9A-Za-z]+)(\r?)$')
    ACKREJ_RE = re.compile(r'^(ack|rej)([0-9A-Za-z]+)$')

    @classmethod
    def decode(cls, uiframe, payload, log):
        # aprslib message decoding is buggy
        if (payload[0] != ':') and (payload[10] != ':'):
            raise ValueError('Not a message frame: %r' % payload)

        addressee = AX25Address.decode(payload[1:10].strip())
        message = payload[11:]

        match = cls.ACKREJ_RE.match(message)
        if match:
            ackrej = match.group(1)
            msgid = match.group(2)
            if ackrej == 'ack':
                # This is an ACK
                return APRSMessageAckFrame(
                    destination=uiframe.header.destination,
                    source=uiframe.header.source,
                    addressee=addressee,
                    msgid=msgid,
                    repeaters=uiframe.header.repeaters,
                    pf=uiframe.pf, cr=uiframe.header.cr
                )
            else:
                # Must be a rejection then
                return APRSMessageRejFrame(
                    destination=uiframe.header.destination,
                    source=uiframe.header.source,
                    addressee=addressee,
                    msgid=msgid,
                    repeaters=uiframe.header.repeaters,
                    pf=uiframe.pf, cr=uiframe.header.cr
                )

        match = cls.MSGID_RE.search(message)
        if match:
            msgid = match.group(1)
            message = message[:-(len(msgid)+1)]
        else:
            msgid = None

        return cls(
                destination=uiframe.header.destination,
                source=uiframe.header.source,
                addressee=addressee,
                message=message,
                msgid=msgid,
                repeaters=uiframe.header.repeaters,
                pf=uiframe.pf, cr=uiframe.header.cr
        )

    def __init__(self, destination, source, addressee, message,
            msgid=None, repeaters=None, pf=False, cr=False):

        self._addressee = AX25Address.decode(addressee).normalised
        self._msgid = msgid
        self._message = message

        payload = ':%-9s:%s' % (
            self._addressee,
            message[0:67]
        )

        if msgid is not None:
            msgid = str(msgid)
            if len(msgid) > 5:
                raise ValueError('message ID %r too long' % msgid)
            payload += '{%s' % msgid

        super(APRSMessageFrame, self).__init__(
                destination=destination,
                source=source,
                payload=payload.encode('US-ASCII'),
                repeaters=repeaters, pf=pf, cr=cr)

    @property
    def addressee(self):
        return self._addressee

    @property
    def msgid(self):
        return self._msgid

    @property
    def message(self):
        return self._message
APRSFrame.DATA_TYPE_HANDLERS[APRSDataType.MESSAGE] = APRSMessageFrame


class APRSMessageAckFrame(APRSMessageFrame):
    def __init__(self, destination, source, addressee, msgid,
            repeaters=None, pf=False, cr=False):
        super(APRSMessageAckFrame, self).__init__(
            destination=destination,
            source=source,
            addressee=addressee,
            message='ack%s' % msgid,
            msgid=None, # Don't encode the message ID a second time
            repeaters=repeaters, pf=pf, cr=cr)

        self._msgid = msgid


class APRSMessageRejFrame(APRSMessageFrame):
    def __init__(self, destination, source, addressee, msgid,
            repeaters=None, pf=False, cr=False):
        super(APRSMessageRejFrame, self).__init__(
            destination=destination,
            source=source,
            addressee=addressee,
            message='rej%s' % msgid,
            msgid=None, # Don't encode the message ID a second time
            repeaters=repeaters, pf=pf, cr=cr)

        self._msgid = msgid

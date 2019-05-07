#!/usr/bin/env python3

"""
APRS messaging handler.
"""

import re
import enum
import weakref
import random
import asyncio
import logging
import signalslot
import aprslib
from aioax25.frame import AX25Frame, AX25UnnumberedInformationFrame, \
		AX25Address, AX25FrameHeader


class APRSHandler(object):
    def __init__(self, kissport, mycall, digipeating=True,
            mydigi=['WIDE1-1', 'WIDE2-1'], retransmit_count=4,
            retransmit_timeout_base=5, retransmit_timeout_rand=5,
            retransmit_timeout_scale=1.5, aprs_destination='APRS',
            aprs_path=['WIDE1-1','WIDE2-1'], log=None, loop=None):
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
        self._kissport = kissport
        self._mycall = AX25Address.decode(mycall).normalised
        kissport.received.connect(self._on_receive_frame)

        # Message ID counter
        self._msgid = 0

        if digipeating:
            self._mydigi = set([
                AX25Address.decode(call).normalised
                for call
                in (mydigi or [])
            ])

            self._mydigi.add(self._mycall)
        else:
            # Empty set, will disable digipeating
            self._mydigi = set()

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
        self.received_msg = signalslot.Signal()

        # Pending messages, by addressee and message ID
        self._pending_msg = {}

    @property
    def mycall(self):
        return self._mycall.copy()

    def _on_receive_frame(self, frame):
        """
        Raw frame handler.  Decodes the raw AX.25 message encoded in the
        given bytestring and processes the destination.
        """
        try:
            message = AX25Frame.decode(frame)
        except:
            self._log.debug('Failed to decode frame: %s', frame, exc_info=1)
            return

        self._log.debug('Received incoming message: %s (type %s)',
                message, message.__class__.__name__)

        try:
            # AX.25 standard says we should ignore uplink frames
            # destined for digipeaters, but this is an issue if you're
            # actually not in an area with repeaters present.
            #
            # So handle digipeating if and only if our callsign isn't the
            # destination.
            if message.header.destination.normalised != self.mycall:
                for idx, digi in enumerate(message.header.repeaters or []):
                    # Has the frame passed through this particular repeater?
                    if not digi.ch:
                        # Nope, Is this meant to go *via* us?
                        # Normalise the CH/RES[01]/EXT bits for comparison
                        digi_norm = digi.copy(res0=True, res1=True,
                                ch=False, extension=False)
                        for call in self._mydigi:
                            if digi_norm == call:
                                # This is one of our "mydigi" calls, digipeat
                                # this
                                self._on_digipeat(idx, message)
                                break

            # We've got to the end of the digipeater chain, handle the message.
            self._on_receive_msg(message)
        except:
            self._log.exception(
                    'Failed to process incoming message: %s', message
            )

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
                path=list(reversed(message.header.repeaters or [])),
                message='%s%s' % ('ack' if ack else 'rej', message.msgid),
                oneshot=True
        )

    def _on_digipeat(self, digi_idx, message):
        """
        Handle a message for digipeating.
        """
        try:
            repeaters = (message.header.repeaters or [])

            # Get the repeaters before and after
            prior_repeaters = repeaters[0:digi_idx]
            following_repeaters = repeaters[digi_idx+1:]

            # Insert ourselves into the list
            repeaters = prior_repeaters + [self.mycall.copy(
                    # Message has passed to us, so set the C/H bit.
                    ch=True,
                    # If there are no further digipeaters, set the extension bit
                    extension=(len(following_repeaters) == 0)
            )]

            # Build up a new header
            header = AX25FrameHeader(
                    # Same source/destination as before, CR bits untouched.
                    destination=message.header.destination,
                    source=message.header.source,
                    cr=message.header.cr,
                    # Replace the repeater list
                    repeaters=repeaters
            )

            # Send the frame off with the new header
            self._log.debug('Digipeating %s', message)
            self._send(message.copy(header=header))
        except:
            self._log.exception('Failed to digipeat message %s (idx=%d)',
                    message, digi_idx)

    def _on_receive_msg(self, message):
        """
        Handle the incoming message.
        """
        try:
            message = APRSFrame.decode(message, self._log.getChild('decode'))
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
            self._kissport.send(message)
        except:
            self._log.exception('Failed to send %s', message)

    @property
    def _next_msgid(self):
        """
        Return the next message ID
        """
        self._msgid = (self._msgid + 1) % 100000
        return str(self._msgid)

    def _on_msg_handler_finish(self, msgid):
        self._pending_msg.pop(msgid, None)


class APRSMessageHandler(object):
    """
    The APRS message handler is a helper class that handles the
    retransmissions, timeouts and responses to an APRS message.
    """
    class HandlerState(enum.Enum):
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

        self.done = signalslot.Signal()
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

    KNOWN_FORMATS = {}

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

        try:
            # Decode the payload as text
            payload = uiframe.payload.decode('US-ASCII')

            # Munge the incoming data to something aprslib understands.
            aprsdata = aprslib.parse('FROM>TO:%s' % payload)
            log.debug('APRS frame data: %s', aprsdata)

            return cls.KNOWN_FORMATS[aprsdata['format']].decode(
                    uiframe, aprsdata, log
            )
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

    MSGID_RE = re.compile(r'{([0-9A-Za-z]+)$')
    ACKREJ_RE = re.compile(r'^(ack|rej)([0-9A-Za-z]+)$')

    @classmethod
    def decode(cls, uiframe, aprsdata, log):
        # aprslib message decoding is buggy
        rawtext = uiframe.payload.decode('US-ASCII')
        if (rawtext[0] != ':') and (rawtext[10] != ':'):
            raise ValueError('Not a message frame: %r' % rawtext)

        addressee = AX25Address.decode(rawtext[1:10].strip())
        message = rawtext[11:]

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
APRSFrame.KNOWN_FORMATS['message'] = APRSMessageFrame


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

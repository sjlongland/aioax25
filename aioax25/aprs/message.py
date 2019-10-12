#!/usr/bin/env python3

"""
APRS messaging handler.
"""

import re
import weakref
import random
from ..signal import Signal
from enum import Enum

from ..frame import AX25Address
from .frame import APRSFrame
from .datatype import APRSDataType


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

    def __init__(self, aprshandler, addressee, path, message, replyack, log):
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
                replyack=replyack or False,
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
        handler.transmit(self.frame)
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

        # Response will either be a APRSMessage(Ack|Rej)Frame, or a
        # APRSMessageFrame with a reply-ack set.
        if isinstance(response, APRSMessageRejFrame):
            self._enter_state(self.HandlerState.REJECT)
        else:
            self._enter_state(self.HandlerState.SUCCESS)

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


class APRSMessageFrame(APRSFrame):

    MSGID_RE = re.compile(r'{([0-9A-Za-z]+)(}[0-9A-Za-z]*)?(\r?)$')
    ACKREJ_RE = re.compile(r'^(ack|rej)([0-9A-Za-z]+)$')

    @classmethod
    def decode(cls, uiframe, payload, log):
        if (payload[0] != ':') or (payload[10] != ':'):
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
        replyack = False
        if match:
            msgid = match.group(1)

            # APRS 1.1 Reply-ACK detection
            replyack = match.group(2)
            if replyack:
                replyack = replyack[1:] or True
            else:
                replyack = False
            message = message[:match.start(1)-1]
        else:
            msgid = None

        return cls(
                destination=uiframe.header.destination,
                source=uiframe.header.source,
                addressee=addressee,
                message=message,
                msgid=msgid,
                replyack=replyack,
                repeaters=uiframe.header.repeaters,
                pf=uiframe.pf, cr=uiframe.header.cr
        )

    def __init__(self, destination, source, addressee, message,
            msgid=None, replyack=False, repeaters=None, pf=False, cr=False):

        self._addressee = AX25Address.decode(addressee).normalised
        self._msgid = msgid
        self._replyack = replyack
        self._message = message

        payload = ':%-9s:%s' % (
            self._addressee,
            message[0:67]
        )

        if msgid is not None:
            msgid = str(msgid)
            if len(msgid) > 5:
                raise ValueError('message ID %r too long' % msgid)
            assert '{' not in payload, \
                    'Malformed payload: %r' % payload
            payload += '{%s' % msgid

            if replyack is True:
                # We simply support reply-ack
                assert '}' not in payload, \
                        'Malformed payload: %r' % payload
                payload += '}'
            elif replyack:
                # We are ACKing with a reply
                assert '}' not in payload, \
                        'Malformed payload: %r' % payload
                payload += '}%s' % replyack

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
    def replyack(self):
        return self._replyack

    @property
    def message(self):
        return self._message

    def _copy(self):
        return self.__class__(
                destination=self.header.destination,
                source=self.header.source,
                repeaters=self.header.repeaters,
                cr=self.header.cr,
                pf=self.pf,
                addressee=self.addressee,
                msgid=self.msgid,
                replyack=self.replyack,
                message=self.message
        )

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

    def _copy(self):
        return self.__class__(
                destination=self.header.destination,
                source=self.header.source,
                repeaters=self.header.repeaters,
                cr=self.header.cr,
                pf=self.pf,
                addressee=self.addressee,
                msgid=self.msgid
        )


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

    def _copy(self):
        return self.__class__(
                destination=self.header.destination,
                source=self.header.source,
                repeaters=self.header.repeaters,
                cr=self.header.cr,
                pf=self.pf,
                addressee=self.addressee,
                msgid=self.msgid
        )

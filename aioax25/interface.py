#!/usr/bin/env python3

"""
AX.25 Interface handler
"""

import logging
import asyncio
import random
from functools import partial
from .signal import Signal
import time
import re

from .frame import AX25Frame
from .router import Router


class AX25Interface(Router):
    """
    The AX25Interface class represents a logical AX.25 interface.
    The interface handles basic queueing and routing of message traffic.

    Outgoing messages are queued and sent when there is a break of greater
    than the cts_delay (10ms) + a randomisation factor (cts_rand).
    Messages may be cancelled prior to transmission.
    """

    def __init__(self, kissport, cts_delay=0.01,
            cts_rand=0.01, log=None, loop=None):
        # Initialise the superclass
        super(AX25Interface, self).__init__()

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

        # Bind to the KISS port to receive raw messages.
        kissport.received.connect(self._on_receive)

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
        self._reset_cts()
        super(AX25Interface, self)._on_receive(frame)

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
            if (frame.deadline is not None) and \
                    (frame.deadline < time.time()):
                self._log.info('Dropping expired frame: %s', frame)
                self._schedule_tx()
                return
        except AttributeError: # pragma: no cover
            # Technically, all objects that pass through here should be
            # AX25Frame sub-classes, so this branch should not get executed.
            # If it does, we just pretend there is no deadline.
            pass

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

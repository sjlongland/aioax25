#!/usr/bin/env python3

"""
AX.25 Station Peer interface.

This is used as the "proxy" for interacting with a remote AX.25 station.
"""

import logging
from .signal import Signal
import weakref
import enum

from .frame import AX25Frame, AX25Address, AX25SetAsyncBalancedModeFrame, \
        AX25SetAsyncBalancedModeExtendedFrame, \
        AX25ExchangeIdentificationFrame, AX25UnnumberedAcknowledgeFrame, \
        AX25TestFrame, AX25DisconnectFrame, AX25DisconnectModeFrame, \
        AX25FrameRejectFrame, AX25RawFrame, \
        AX2516BitInformationFrame, AX258BitInformationFrame, \
        AX258BitReceiveReadyFrame, AX2516BitReceiveReadyFrame, \
        AX258BitReceiveNotReadyFrame, AX2516BitReceiveNotReadyFrame, \
        AX258BitRejectFrame, AX2516BitRejectFrame, \
        AX258BitSelectiveRejectFrame, AX2516BitSelectiveRejectFrame


class AX25Peer(object):
    """
    This class is a proxy representation of the remote AX.25 peer that may be
    connected to this station.  The factory for these objects is the
    AX25Station's getpeer method.
    """

    class AX25PeerState(enum.Enum):
        # DISCONNECTED: No connection has been established
        DISCONNECTED = 0

        # Awaiting response to XID request
        NEGOTIATING = 1

        # Awaiting response to SABM(E) request
        CONNECTING = 2

        # Connection is established
        CONNECTED = 3

        # Awaiting response to DISC request
        DISCONNECTING = 4

        # FRMR condition entered
        FRMR = 5


    def __init__(self, station, destination, repeaters, max_ifield, max_retries,
            max_outstanding_mod8, max_outstanding_mod128, rr_delay, rr_interval,
            rnr_interval, idle_timeout, protocol, log, loop, reply_path=None,
            locked_path=False):
        """
        Create a peer context for the station named by 'address'.
        """
        self._station = weakref.ref(station)
        self._repeaters = repeaters
        self._reply_path = reply_path
        self._destination = destination
        self._idle_timeout = idle_timeout
        self._max_ifield = max_ifield
        self._max_retries = max_retries
        self._max_outstanding_mod8 = max_outstanding_mod8
        self._max_outstanding_mod128 = max_outstanding_mod128
        self._rr_delay = rr_delay
        self._rr_interval = rr_interval
        self._rnr_interval = rnr_interval
        self._locked_path = bool(locked_path)
        self._protocol = protocol
        self._log = log
        self._loop = loop

        # Internal state (see AX.25 2.2 spec 4.2.4)
        self._state = self.AX25PeerState.DISCONNECTED
        self._max_outstanding = None    # Decided when SABM(E) received
        self._modulo = None             # Set when SABM(E) received
        self._connected = False         # Set to true on SABM UA
        self._send_state = 0            # AKA V(S)
        self._send_seq   = 0            # AKA N(S)
        self._recv_state = 0            # AKA V(R)
        self._recv_seq   = 0            # AKA N(R)
        self._ack_state  = 0            # AKA V(A)
        self._local_busy = False        # Local end busy, respond to
                                        # RR and I-frames with RNR.
        self._peer_busy  = False        # Peer busy, await RR.

        # Time of last sent RNR notification
        self._last_rnr_sent = 0

        # Classes to use for I and S frames
        self._IFrameClass = None
        self._RRFrameClass = None
        self._RNRFrameClass = None
        self._REJFrameClass = None
        self._SREJFrameClass = None

        # Timeouts
        self._idle_timeout_handle = None
        self._rr_notification_timeout_handle = None

        # Unacknowledged I-frames to be ACKed.  This dictionary maps the N(R)
        # of the frame with a tuple of the form (pid, payload).
        self._pending_iframes = {}

        # Data pending to be sent.  This will be a queue of frames represented
        # as tuples of the form (pid, payload).  Each payload is assumed to be
        # no bigger than max_ifield.
        self._pending_data = []

        # Link quality measurement:
        # rx_path_count is incremented each time a frame is received via a
        # given AX.25 digipeater path.
        self._rx_path_count = {}
        # tx_path_score is incremented for each transmitted frame which is ACKed
        # and decremented each time a frame is REJected.
        self._tx_path_score = {}

        # Handling of TEST frames
        self._testframe_handler = None

        # Signals:

        # Fired when an I-frame is received
        self.received_information = Signal()

        # Fired when the connection state changes
        self.connect_state_changed = Signal()

        # Kick off the idle timer
        self._reset_idle_timeout()

    @property
    def reply_path(self):
        """
        Return the digipeater path to use when contacting this station.
        """
        if self._reply_path is None:
            # No specific path set, are we locked to a given path?
            if self._locked_path:
                # Use the one we were given
                return self._repeaters

            # Enumerate all possible paths and select the "best" path
            all_paths = list(self._tx_path_score.items()) \
                    + [(path, 0) for path in self._rx_path_count.keys()]
            all_paths.sort(key=lambda p : p[0])
            best_path = all_paths[-1][0]

            # Use this until we have reason to change
            self._reply_path = AX25Path(*best_path)

        return self._reply_path

    def weight_path(self, path, weight, relative=True):
        """
        Adjust the weight of a digipeater path used to reach this station.
        If relative is True, this increments by weight; otherwise it overrides
        the weight given.
        """
        path = tuple(reversed(AX25Path(*(path or [])).reply))

        if relative:
            weight += self._tx_path_score.get(path, 0)
        self._tx_path_score[path] = weight

    def _cancel_idle_timeout(self):
        """
        Cancel the idle timeout handle
        """
        if self._idle_timeout_handle is not None:
            self._idle_timeout_handle.cancel()
            self._idle_timeout_handle = None

    def _reset_idle_timeout(self):
        """
        Reset the idle timeout handle
        """
        self._cancel_idle_timeout()
        self._idle_timeout_handle = self._loop.call_later(
                self._idle_timeout, self._cleanup)

    def _cleanup(self):
        """
        Clean up the instance of this peer as the activity has expired.
        """
        if self._state != self.AX25PeerState.DISCONNECTED:
            self._log.warning('Disconnecting peer due to inactivity')
            self._send_dm()

        self._station()._drop_peer(self)

        # Cancel other timers
        self._cancel_rr_notification()

    def _on_receive(self, frame):
        """
        Handle an incoming AX.25 frame from this peer.
        """
        # Kick off the idle timer
        self._reset_idle_timeout()

        if not self._locked_path:
            # Increment the received frame count
            path = tuple(reversed(frame.header.repeaters.reply))
            self._rx_path_count[path] = self._rx_path_count.get(path, 0) + 1

        # AX.25 2.2 sect 6.3.1: "The originating TNC sending a SABM(E) command
        # ignores and discards any frames except SABM, DISC, UA and DM frames
        # from the distant TNC."
        if (self._state == self.AX25PeerState.CONNECTING) and \
                not isinstance(frame, ( \
                    AX25SetAsyncBalancedModeFrame,          # SABM
                    AX25SetAsyncBalancedModeExtendedFrame,  # SABME
                    AX25DisconnectFrame,                    # DISC
                    AX25UnnumberedAcknowledgeFrame,         # UA
                    AX25DisconnectModeFrame)):              # DM
            self._log.debug('Dropping frame due to pending SABM UA: %s', frame)
            return

        # AX.25 2.0 sect 2.4.5: "After sending the FRMR frame, the sending DXE
        # will enter the frame reject condition. This condition is cleared when
        # the DXE that sent the FRMR frame receives a SABM or DISC command, or
        # a DM response frame. Any other command received while the DXE is in
        # the frame reject state will cause another FRMR to be sent out with
        # the same information field as originally sent."
        if (self._state == self.AX25PeerState.FRMR) and \
                not isinstance(frame, ( \
                    AX25SetAsyncBalancedModeFrame,          # SABM
                    AX25DisconnectFrame)):                  # DISC
            self._log.debug('Dropping frame due to FRMR: %s', frame)
            return

        if isinstance(frame, AX25TestFrame):
            # TEST frame
            return self._on_receive_test(frame)
        elif isinstance(frame, (AX25SetAsyncBalancedModeFrame,
                AX25SetAsyncBalancedModeExtendedFrame)):
            # SABM or SABME frame
            return self._on_receive_sabm(frame)
        elif isinstance(frame, AX25DisconnectFrame):
            # DISC frame
            return self._on_receive_disc()
        elif isinstance(frame, AX25DisconnectModeFrame):
            # DM frame
            return self._on_receive_dm()
        elif isinstance(frame, AX25ExchangeIdentificationFrame):
            # XID frame
            return self._on_receive_xid(frame)
        elif isinstance(frame, AX25RawFrame):
            # This is either an I or S frame.  We should know enough now to
            # decode it properly.
            if self._state == self.AX25PeerState.CONNECTED:
                # A connection is in progress, we can decode this
                frame = AX25Frame.decode(frame, modulo128=(self._modulo == 128))
                if isinstance(frame, AX25InformationFrameMixin):
                    # This is an I-frame
                    return self._on_receive_iframe(frame)
                elif isinstance(frame, AX25SupervisoryFrameMixin):
                    # This is an S-frame
                    return self._on_receive_sframe(frame)
                else: # pragma: no cover
                    self._log.warning('Dropping unrecognised frame: %s', frame)
            else:
                # No connection in progress, send a DM.
                return self._send_dm()

    def _on_receive_iframe(self, frame):
        """
        Handle an incoming I-frame
        """
        # Cancel a pending RR notification frame.
        self._cancel_rr_notification()

        # AX.25 2.2 spec 6.4.2.2: "If the TNC is in a busy condition, it
        # ignores any I frames without reporting this condition, other than
        # repeating the indication of the busy condition."
        if self._local_busy:
            self._log.warning(
                    'Dropping I-frame during busy condition: %s', frame
            )
            self._send_rnr_notification()
            return

        # AX.25 2.2 spec 6.4.2.1: "If a TNC receives a valid I frame (one whose
        # send sequence number equals the receiver's receive state variable) and
        # is not in the busy condition,…"
        if frame.ns != self._recv_seq:
            # TODO: should we send a REJ/SREJ after a time-out?
            return

        # "…it accepts the received I frame,
        # increments its receive state variable, and acts in one of the following
        # manners:…"
        self._recv_state = (self._recv_state + 1) % self._modulo

        # "a) If it has an I frame to send, that I frame may be sent with the
        # transmitted N(R) equal to its receive state V(R) (thus acknowledging
        # the received frame)."
        #
        # We need to also be mindful of the number of outstanding frames here!
        if len(self._pending_data) and (len(self._pending_iframes) \
                                        < self._max_outstanding):
            return self._send_next_iframe()

        # "b) If there are no outstanding I frames, the receiving TNC sends
        # an RR frame with N(R) equal to V(R)."
        self._schedule_rr_notification()

    def _on_receive_sframe(self, frame):
        """
        Handle a S-frame from the peer.
        """
        # TODO
        pass

    def _on_receive_test(self, frame):
        self._log.debug('Received TEST response: %s', frame)
        if self._testframe_handler:
            self._testframe_handler._on_receive(frame)

    def _on_receive_sabm(self, frame):
        modulo128 = isinstance(frame, AX25SetAsyncBalancedModeExtendedFrame)
        self._log.debug('Received SABM(E): %s (extended=%s)', frame, modulo128)
        if modulo128:
            # If we don't know the protocol of the peer, we can safely assume
            # AX.25 2.2 now.
            if self._protocol == AX25Version.UNKNOWN:
                self._protocol = AX25Version.AX25_22

            # Make sure both ends are enabled for AX.25 2.2
            if self._station().protocol != AX25Version.AX25_22:
                # We are not in AX.25 2.2 mode.
                #
                # "A TNC that uses a version of AX.25 prior to v2.2 responds
                # with a FRMR".  W bit indicates the control field was not
                # understood.
                self._log.warning(
                        'Sending FRMR as we are not in AX.25 2.2 mode'
                )
                return self._send_frmr(frame, w=True)

            if self._protocol != AX25Version.AX25_22:
                # The other station is not in AX.25 2.2 mode.
                #
                # "If the TNC is not capable of accepting a SABME, it
                # responds with a DM frame".
                self._log.warning(
                        'Sending DM as peer is not in AX.25 2.2 mode'
                )
                return self._send_dm()

        # Set up the connection state
        self._init_connection(modulo128)

        # Send a UA and set ourselves as connected
        self._set_conn_state(self.AX25PeerState.CONNECTED)
        self._send_ua()

    def _init_connection(self, modulo128):
        """
        Initialise the AX.25 connection.
        """
        if modulo128:
            # Set the maximum outstanding frames variable
            self._max_outstanding = self._max_outstanding_mod128

            # Initialise the modulo value
            self._modulo = 128

            # Set the classes to use for I and S frames for modulo128 ops.
            self._IFrameClass = AX2516BitInformationFrame
            self._RRFrameClass = AX2516BitReceiveReadyFrame
            self._RNRFrameClass = AX2516BitReceiveNotReadyFrame
            self._REJFrameClass = AX2516BitRejectFrame
            self._SREJFrameClass = AX2516BitSelectiveRejectFrame
        else:
            # Set the maximum outstanding frames variable
            self._max_outstanding = self._max_outstanding_mod8

            # Initialise the modulo value
            self._modulo = 8

            # Set the classes to use for I and S frames for modulo8 ops.
            self._IFrameClass = AX258BitInformationFrame
            self._RRFrameClass = AX258BitReceiveReadyFrame
            self._RNRFrameClass = AX258BitReceiveNotReadyFrame
            self._REJFrameClass = AX258BitRejectFrame
            self._SREJFrameClass = AX258BitSelectiveRejectFrame

        # Reset state variables
        self._reset_connection_state()

    def _reset_connection_state(self):
        # Reset our state
        self._send_state = 0            # AKA V(S)
        self._send_seq   = 0            # AKA N(S)
        self._recv_state = 0            # AKA V(R)
        self._recv_seq   = 0            # AKA N(R)
        self._ack_state  = 0            # AKA V(A)

        # Unacknowledged I-frames to be ACKed
        self._pending_iframes = {}

        # Data pending to be sent.
        self._pending_data = []

    def _set_conn_state(self, state):
        if self._state == state:
            # Nothing to do
            return

        # Update the state
        self._log.info('Connection state change: %s→%s',
                self._state, state)
        self._state = state

        # Notify any observers that the state changed
        self.connect_state_changed.emit(
                station=self._station(),
                peer=self,
                state=self._state)

    def _on_disconnect(self):
        """
        Clean up the connection.
        """
        # Send a UA and set ourselves as disconnected
        self._set_conn_state(self.AX25PeerState.DISCONNECTED)

        # Reset our state
        self._reset_connection_state()

        # Data pending to be sent.
        self._pending_data = []

    def _on_receive_disc(self):
        """
        Handle a disconnect request from this peer.
        """
        # Send a UA and set ourselves as disconnected
        self._log.info('Received DISC from peer')
        self._on_disconnect()
        self._send_ua()

    def _on_receive_dm(self):
        """
        Handle a disconnect request from this peer.
        """
        # Set ourselves as disconnected
        self._log.info('Received DM from peer')
        self._on_disconnect()

    def _on_receive_xid(self, frame):
        """
        Handle a request to negotiate parameters.
        """
        if self._station().protocol != AX25Version.AX25_22:
            # Not supporting this in AX.25 2.0 mode
            self._log.warning(
                    'Received XID from peer, we are not in AX.25 2.2 mode'
            )
            return self._send_frmr(frame, w=True)
        if self._state in (
                self.AX25PeerState.CONNECTING,
                self.AX25PeerState.DISCONNECTING
        ):
            # AX.25 2.2 sect 4.3.3.7: "A station receiving an XID command
            # returns an XID response unless a UA response to a mode setting
            # command is awaiting transmission, or a FRMR condition exists".
            self._log.warning(
                    'UA is pending, dropping received XID'
            )
            return

        # TODO: figure out XID and send an appropriate response.
        self._log.error('TODO: implement XID')
        return self._send_frmr(frame, w=True)

    def _send_dm(self):
        """
        Send a DM frame to the remote station.
        """
        self._log.debug('Sending DM')
        self._transmit_frame(
                AX25DisconnectModeFrame(
                    destination=self._address,
                    source=self._station().address,
                    repeaters=self.reply_path
                )
        )

    def _send_ua(self):
        """
        Send a UA frame to the remote station.
        """
        self._log.debug('Sending UA')
        self._transmit_frame(
                AX25UnnumberedAcknowledgeFrame(
                    destination=self._address,
                    source=self._station().address,
                    repeaters=self.reply_path
                )
        )

    def _send_frmr(self, frame, w=False, x=False, y=False, z=False):
        """
        Send a FRMR frame to the remote station.
        """
        self._log.debug('Sending FRMR in reply to %s', frame)

        # AX.25 2.0 sect 2.4.5: "After sending the FRMR frame, the sending DXE
        # will enter the frame reject condition. This condition is cleared when
        # the DXE that sent the FRMR frame receives a SABM or DISC command, or
        # a DM response frame. Any other command received while the DXE is in
        # the frame reject state will cause another FRMR to be sent out with
        # the same information field as originally sent."
        self._set_conn_state(self.AX25PeerState.FRMR)

        # See https://www.tapr.org/pub_ax25.html
        self._transmit_frame(
                AX25FrameRejectFrame(
                    destination=self._address,
                    source=self._station().address,
                    repeaters=self.reply_path,
                    w=w, x=x, y=y, z=z,
                    vr=self._recv_state,
                    vs=self._send_state,
                    frmr_cr=frame.header.cr,
                    frmr_control=frame.control
                )
        )

    def _cancel_rr_notification(self):
        """
        Cancel transmission of an RR
        """
        if self._rr_notification_timeout_handle is not None:
            self._rr_notification_timeout_handle.cancel()
            self._rr_notification_timeout_handle = None

    def _schedule_rr_notification(self):
        """
        Schedule a RR notification frame to be sent.
        """
        self._cancel_rr_notification()
        self._rr_notification_timeout_handle = \
                self._loop.call_later(self._send_rr_notification)

    def _send_rr_notification(self):
        """
        Send a RR notification frame
        """
        self._cancel_rr_notification()
        self._transmit_frame(
                self._RRFrameClass(
                    destination=self._address,
                    source=self._station().address,
                    repeaters=self.reply_path,
                    pf=False, nr=self._recv_state
                )
        )

    def _send_rnr_notification(self):
        """
        Send a RNR notification if the RNR interval has elapsed.
        """
        now = self._loop.time()
        if (now - self._last_rnr_sent) > self._rnr_interval:
            self._transmit_frame(
                    self._RNRFrameClass(
                        destination=self._address,
                        source=self._station().address,
                        repeaters=self.reply_path,
                        nr=self._recv_seq,
                        pf=False
                    )
            )
            self._last_rnr_sent = now

    def _send_next_iframe(self):
        """
        Send the next I-frame, if there aren't too many frames pending.
        """
        if not len(self._pending_data) or (len(self._pending_iframes) \
                                        >= self._max_outstanding):
            self._log.debug('Waiting for pending I-frames to be ACKed')
            return

        # AX.25 2.2 spec 6.4.1: "Whenever a TNC has an I frame to transmit,
        # it sends the I frame with the N(S) of the control field equal to
        # its current send state variable V(S)…"
        ns = self._send_state
        assert ns not in self._pending_iframes, 'Duplicate N(S) pending'

        # Retrieve the next pending I-frame payload
        (pid, payload) = self._pending_data.pop(0)
        self._pending_iframes[ns] = (pid, payload)

        # Send it
        self._transmit_iframe(ns)

        # "After the I frame is sent, the send state variable is incremented
        # by one."
        self._send_state = (self._send_state + 1) \
                % self._modulo

    def _transmit_iframe(self, ns):
        """
        Transmit the I-frame identified by the given N(S) parameter.
        """
        (pid, payload) = self._pending_iframes[ns]
        self._transmit_frame(
                self._IFrameClass(
                    destination=self._address,
                    source=self._station().address,
                    repeaters=self.reply_path,
                    nr=self._recv_seq,
                    ns=ns,
                    pf=False,
                    pid=pid, payload=payload
                )
        )

    def _transmit_frame(self, frame):
        # Kick off the idle timer
        self._reset_idle_timeout()
        return self._station()._interface().transmit(frame)

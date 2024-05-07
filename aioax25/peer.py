#!/usr/bin/env python3

"""
AX.25 Station Peer interface.

This is used as the "proxy" for interacting with a remote AX.25 station.
"""

from .signal import Signal

import weakref
import enum
import logging

from .version import AX25Version
from .frame import (
    AX25Frame,
    AX25Path,
    AX25SetAsyncBalancedModeFrame,
    AX25SetAsyncBalancedModeExtendedFrame,
    AX25ExchangeIdentificationFrame,
    AX25UnnumberedFrame,
    AX25UnnumberedAcknowledgeFrame,
    AX25TestFrame,
    AX25DisconnectFrame,
    AX25DisconnectModeFrame,
    AX25FrameRejectFrame,
    AX25RawFrame,
    AX2516BitInformationFrame,
    AX258BitInformationFrame,
    AX258BitReceiveReadyFrame,
    AX2516BitReceiveReadyFrame,
    AX258BitReceiveNotReadyFrame,
    AX2516BitReceiveNotReadyFrame,
    AX258BitRejectFrame,
    AX2516BitRejectFrame,
    AX258BitSelectiveRejectFrame,
    AX2516BitSelectiveRejectFrame,
    AX25InformationFrameMixin,
    AX25SupervisoryFrameMixin,
    AX25XIDParameterIdentifier,
    AX25XIDClassOfProceduresParameter,
    AX25XIDHDLCOptionalFunctionsParameter,
    AX25XIDIFieldLengthTransmitParameter,
    AX25XIDIFieldLengthReceiveParameter,
    AX25XIDWindowSizeTransmitParameter,
    AX25XIDWindowSizeReceiveParameter,
    AX25XIDAcknowledgeTimerParameter,
    AX25XIDRetriesParameter,
    AX25_20_DEFAULT_XID_COP,
    AX25_22_DEFAULT_XID_COP,
    AX25_20_DEFAULT_XID_HDLCOPTFUNC,
    AX25_22_DEFAULT_XID_HDLCOPTFUNC,
    AX25_20_DEFAULT_XID_IFIELDRX,
    AX25_22_DEFAULT_XID_IFIELDRX,
    AX25_20_DEFAULT_XID_WINDOWSZRX,
    AX25_22_DEFAULT_XID_WINDOWSZRX,
    AX25_20_DEFAULT_XID_ACKTIMER,
    AX25_22_DEFAULT_XID_ACKTIMER,
    AX25_20_DEFAULT_XID_RETRIES,
    AX25_22_DEFAULT_XID_RETRIES,
)


# AX25RejectMode precedence:
_REJECT_MODE_PRECEDENCE = {"selective_rr": 2, "selective": 1, "implicit": 0}


class AX25RejectMode(enum.Enum):
    IMPLICIT = "implicit"
    SELECTIVE = "selective"
    SELECTIVE_RR = "selective_rr"

    @property
    def precedence(self):
        """
        Get the precedence of this mode.
        """
        return _REJECT_MODE_PRECEDENCE[self.value]


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

    # Incomming connection, awaiting our UA or DM response
    INCOMING_CONNECTION = 6


class AX25Peer(object):
    """
    This class is a proxy representation of the remote AX.25 peer that may be
    connected to this station.  The factory for these objects is the
    AX25Station's getpeer method.
    """

    def __init__(
        self,
        station,
        address,
        repeaters,
        max_ifield,
        max_ifield_rx,
        max_retries,
        max_outstanding_mod8,
        max_outstanding_mod128,
        rr_delay,
        rr_interval,
        rnr_interval,
        ack_timeout,
        idle_timeout,
        protocol,
        modulo128,
        log,
        loop,
        reject_mode,
        full_duplex,
        reply_path=None,
        locked_path=False,
        paclen=128,
    ):
        """
        Create a peer context for the station named by 'address'.
        """
        self._station = weakref.ref(station)
        self._repeaters = repeaters
        self._reply_path = reply_path
        self._address = address
        self._ack_timeout = ack_timeout
        self._idle_timeout = idle_timeout
        self._reject_mode = reject_mode
        self._full_duplex = full_duplex
        self._max_ifield = max_ifield
        self._max_ifield_rx = max_ifield_rx
        self._max_retries = max_retries
        self._modulo128 = modulo128
        self._max_outstanding_mod8 = max_outstanding_mod8
        self._max_outstanding_mod128 = max_outstanding_mod128
        self._rr_delay = rr_delay
        self._rr_interval = rr_interval
        self._rnr_interval = rnr_interval
        self._paclen = paclen
        self._locked_path = bool(locked_path)
        self._protocol = protocol
        self._log = log
        self._loop = loop

        # Internal state (see AX.25 2.2 spec 4.2.4)
        self._state = AX25PeerState.DISCONNECTED
        self._max_outstanding = None  # Decided when SABM(E) received
        self._modulo = None  # Set when SABM(E) received
        self._negotiated = False  # Set to True after XID negotiation
        self._connected = False  # Set to true on SABM UA
        self._last_act = 0  # Time of last activity

        # 2.3.2.4.1 Send State Variable V(S)
        # The send state variable is a variable that is internal to the DXE
        # and is never sent. It contains the next sequential number to be
        # assigned to the next transmitted I frame. This variable is updated
        # upon the transmission of each I frame.
        self._send_state = 0
        self._send_state_name = "V(S)"

        # 2.3.2.4.2 Send Sequence Number N(S)
        # The send sequence number is found in the control field of all I
        # frames. It contains the sequence number of the I frame being sent.
        # Just prior to the transmission of the I frame, N(S) is updated to
        # equal the send state variable.
        self._send_seq = 0
        self._send_seq_name = "N(S)"

        # 2.3.2.4.3 Receive State Variable V(R)
        # The receive state variable is a variable that is internal to the
        # DXE. It contains the sequence number of the next expected received I
        # frame. This variable is updated upon the reception of an error-free
        # I frame whose send sequence number equals the present received state
        # variable value.
        self._recv_state = 0
        self._recv_state_name = "V(R)"

        # 2.3.2.4.4 Received Sequence Number N(R)
        # The received sequence number is in both I and S frames. Prior to
        # sending an I or S frame, this variable is updated to equal that of
        # the received state variable, thus implicitly acknowledging the
        # proper reception of all frames up to and including N(R)-1.
        self._recv_seq = 0
        self._recv_seq_name = "N(R)"

        self._local_busy = False  # Local end busy, respond to
        # RR and I-frames with RNR.
        self._peer_busy = False  # Peer busy, await RR.

        # Time of last sent RNR notification
        self._last_rnr_sent = 0

        # Classes to use for I and S frames
        self._IFrameClass = None
        self._RRFrameClass = None
        self._RNRFrameClass = None
        self._REJFrameClass = None
        self._SREJFrameClass = None

        # Timeouts
        self._ack_timeout_handle = None
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

        # Handling of various incoming frames
        self._testframe_handler = None
        self._xidframe_handler = None
        self._sabmframe_handler = None
        self._uaframe_handler = None
        self._dmframe_handler = None
        self._frmrframe_handler = None

        # Signals:

        # Fired when any frame is received from the peer
        self.received_frame = Signal()

        # Fired when any frame is sent to the peer
        self.sent_frame = Signal()

        # Fired when an I-frame is received
        self.received_information = Signal()

        # Fired when the connection state changes
        self.connect_state_changed = Signal()

        # Kick off the idle timer
        self._reset_idle_timeout()

    @property
    def address(self):
        """
        Return the peer's AX.25 address
        """
        return self._address

    @property
    def state(self):
        """
        Return the peer connection state
        """
        return self._state

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
            # - most highly rated TX path
            # - most frequently seen RX path
            all_paths = list(
                sorted(self._tx_path_score.items(), key=lambda i: i[1])
            ) + list(sorted(self._rx_path_count.items(), key=lambda i: i[1]))

            if all_paths:
                best_path = all_paths[-1][0]
                self._log.info(
                    "Choosing highest rated TX/most common RX path: %s",
                    best_path,
                )
            else:
                # If no paths exist, use whatever default path is set
                best_path = self._repeaters
                self._log.info(
                    "Choosing given path for replies: %s", best_path
                )

            # Use this until we have reason to change
            self._reply_path = AX25Path(*(best_path or []))

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
        self._log.debug("Weighted score for %s: %d", path, weight)

    def ping(self, payload=None, timeout=30.0, callback=None):
        """
        Ping the peer and wait for a response.
        """
        self._log.debug(
            "Beginning ping of station (payload=%r timeout=%r)",
            payload,
            timeout,
        )
        handler = AX25PeerTestHandler(self, bytes(payload or b""), timeout)
        handler.done_sig.connect(self._on_test_done)

        if callback is not None:
            handler.done_sig.connect(callback)

        handler._go()
        return handler

    def connect(self):
        """
        Connect to the remote node.
        """
        if self._state is AX25PeerState.DISCONNECTED:
            self._log.info("Initiating connection to remote peer")
            handler = AX25PeerConnectionHandler(self)
            handler.done_sig.connect(self._on_connect_response)
            handler._go()
        else:
            self._log.info(
                "Will not connect to peer now, currently in state %s.",
                self._state.name,
            )

    def accept(self):
        """
        Accept an incoming connection from the peer.
        """
        if self._state is AX25PeerState.INCOMING_CONNECTION:
            self._log.info("Accepting incoming connection")
            # Send a UA and set ourselves as connected
            self._stop_ack_timer()
            self._send_ua()
            self._log.info("Connection accepted")
            self._set_conn_state(AX25PeerState.CONNECTED)
        else:
            self._log.info(
                "Will not accept connection from peer now, "
                "currently in state %s.",
                self._state.name,
            )

    def reject(self):
        """
        Reject an incoming connection from the peer.
        """
        if self._state is AX25PeerState.INCOMING_CONNECTION:
            self._log.info("Rejecting incoming connection")
            # Send a DM and set ourselves as disconnected
            self._stop_ack_timer()
            self._set_conn_state(AX25PeerState.DISCONNECTED)
            self._send_dm()
        else:
            self._log.info(
                "Will not reject connection from peer now, "
                "currently in state %s.",
                self._state.name,
            )

    def disconnect(self):
        """
        Disconnect from the remote node.
        """
        if self._state is AX25PeerState.CONNECTED:
            self._uaframe_handler = self._on_disconnect
            self._set_conn_state(AX25PeerState.DISCONNECTING)
            self._send_disc()
            self._start_disconnect_ack_timer()
        else:
            self._log.info(
                "Will not disconnect from peer now, "
                "currently in state %s.",
                self._state.name,
            )

    def send(self, payload, pid=AX25Frame.PID_NO_L3):
        """
        Send the given payload data to the remote station.
        """
        while payload:
            block = payload[: self._paclen]
            payload = payload[self._paclen :]

            self._pending_data.append((pid, block))

        self._send_next_iframe()

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
            self._idle_timeout, self._cleanup
        )

    def _cleanup(self):
        """
        Clean up the instance of this peer as the activity has expired.
        """
        if self._state not in (
            AX25PeerState.DISCONNECTED,
            AX25PeerState.DISCONNECTING,
        ):
            self._log.warning("Disconnecting peer due to inactivity")
            if self._state is AX25PeerState.CONNECTED:
                self.disconnect()
            else:
                self._send_dm()
        else:
            self._log.debug(
                "Clean-up initiated in state %s", self._state.name
            )

        # Cancel other timers
        self._cancel_rr_notification()

    def _on_receive(self, frame):
        """
        Handle an incoming AX.25 frame from this peer.
        """
        self._log.debug("Received: %s", frame)

        # Kick off the idle timer
        self._reset_idle_timeout()

        # Update the last activity timestamp
        self._last_act = self._loop.time()

        if not self._locked_path:
            # Increment the received frame count
            path = tuple(reversed(frame.header.repeaters.reply))
            pathcount = self._rx_path_count.get(path, 0) + 1
            self._log.debug(
                "Observed %d frame(s) via path %s", pathcount, path
            )
            self._rx_path_count[path] = pathcount

        # AX.25 2.2 sect 6.3.1: "The originating TNC sending a SABM(E) command
        # ignores and discards any frames except SABM, DISC, UA and DM frames
        # from the distant TNC."
        if (self._state is AX25PeerState.CONNECTING) and not isinstance(
            frame,
            (
                AX25SetAsyncBalancedModeFrame,  # SABM
                AX25SetAsyncBalancedModeExtendedFrame,  # SABME
                AX25DisconnectFrame,  # DISC
                AX25UnnumberedAcknowledgeFrame,  # UA
                AX25DisconnectModeFrame,
            ),
        ):  # DM
            self._log.debug(
                "Dropping frame due to pending SABM UA: %s", frame
            )
            return

        # AX.25 2.0 sect 2.4.5: "After sending the FRMR frame, the sending DXE
        # will enter the frame reject condition. This condition is cleared when
        # the DXE that sent the FRMR frame receives a SABM or DISC command, or
        # a DM response frame. Any other command received while the DXE is in
        # the frame reject state will cause another FRMR to be sent out with
        # the same information field as originally sent."
        if (self._state is AX25PeerState.FRMR) and not isinstance(
            frame,
            (AX25SetAsyncBalancedModeFrame, AX25DisconnectFrame),  # SABM
        ):  # DISC
            self._log.debug("Dropping frame due to FRMR: %s", frame)
            return

        # Is this a U frame?  I frames and S frames must be decoded elsewhere.
        if isinstance(frame, AX25UnnumberedFrame):
            self.received_frame.emit(frame=frame, peer=self)

        if isinstance(frame, AX25TestFrame):
            # TEST frame
            return self._on_receive_test(frame)
        elif isinstance(frame, AX25FrameRejectFrame):
            # FRMR frame
            return self._on_receive_frmr(frame)
        elif isinstance(frame, AX25UnnumberedAcknowledgeFrame):
            # UA frame
            return self._on_receive_ua()
        elif isinstance(
            frame,
            (
                AX25SetAsyncBalancedModeFrame,
                AX25SetAsyncBalancedModeExtendedFrame,
            ),
        ):
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
            if self._state is AX25PeerState.CONNECTED:
                # A connection is in progress, we can decode this
                frame = AX25Frame.decode(
                    frame, modulo128=(self._modulo == 128)
                )
                self._log.debug("Decoded frame: %s", frame)
                self.received_frame.emit(frame=frame, peer=self)
                if isinstance(frame, AX25InformationFrameMixin):
                    # This is an I-frame
                    return self._on_receive_iframe(frame)
                elif isinstance(frame, AX25SupervisoryFrameMixin):
                    # This is an S-frame
                    return self._on_receive_sframe(frame)
                else:  # pragma: no cover
                    self._log.warning(
                        "Dropping unrecognised frame: %s", frame
                    )
            else:
                # No connection in progress, send a DM.
                self._log.debug(
                    "Received I or S frame in state %s", self._state.name
                )
                self.received_frame.emit(frame=frame, peer=self)
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
                "Dropping I-frame during busy condition: %s", frame
            )
            self._send_rnr_notification()
            return

        # AX.25 2.2 spec 6.4.2.1: "If a TNC receives a valid I frame (one whose
        # send sequence number equals the receiver's receive state variable) and
        # is not in the busy condition,…"
        if frame.ns != self._recv_seq:
            # TODO: should we send a REJ/SREJ after a time-out?
            self._log.debug(
                "I-frame sequence is %s, expecting %s, ignoring",
                frame.ns,
                self._recv_seq,
            )
            return

        # "…it accepts the received I frame,
        # increments its receive state variable, and acts in one of the
        # following manners:…"
        self._update_state(
            "_recv_state", value=frame.ns + 1, comment="from I-frame N(S)"
        )
        self._on_receive_isframe_nr_ns(frame)

        # TODO: the payload here may be a repeat of data already seen, or
        # for _future_ data (i.e. there's an I-frame that got missed in between
        # the last one we saw, and this one).  How do we handle this possibly
        # out-of-order data?
        self.received_information.emit(frame=frame, payload=frame.payload)

        # "a) If it has an I frame to send, that I frame may be sent with the
        # transmitted N(R) equal to its receive state V(R) (thus acknowledging
        # the received frame)."
        #
        # We need to also be mindful of the number of outstanding frames here!
        if len(self._pending_data) and (
            len(self._pending_iframes) < self._max_outstanding
        ):
            return self._send_next_iframe()

        # "b) If there are no outstanding I frames, the receiving TNC sends
        # an RR frame with N(R) equal to V(R)."
        self._schedule_rr_notification()

    def _on_receive_sframe(self, frame):
        """
        Handle a S-frame from the peer.
        """
        self._on_receive_isframe_nr_ns(frame)
        if isinstance(frame, self._RRFrameClass):
            self._on_receive_rr(frame)
        elif isinstance(frame, self._RNRFrameClass):
            self._on_receive_rnr(frame)
        elif isinstance(frame, self._REJFrameClass):
            self._on_receive_rej(frame)
        elif isinstance(frame, self._SREJFrameClass):
            self._on_receive_srej(frame)

    def _on_receive_isframe_nr_ns(self, frame):
        """
        Handle the N(R) / N(S) fields from an I or S frame from the peer.
        """
        # "Whenever an I or S frame is correctly received, even in a busy
        # condition, the N(R) of the received frame should be checked to see
        # if it includes an acknowledgement of outstanding sent I frames. The
        # T1 timer should be cancelled if the received frame actually
        # acknowledges previously unacknowledged frames. If the T1 timer is
        # cancelled and there are still some frames that have been sent that
        # are not acknowledged, T1 should be started again. If the T1 timer
        # runs out before an acknowledgement is received, the device should
        # proceed to the retransmission procedure in 2.4.4.9."

        # Check N(R) for received frames.
        self._ack_outstanding((frame.nr - 1) % self._modulo)

    def _on_receive_rr(self, frame):
        if frame.pf:
            # Peer requesting our RR status
            self._log.debug("RR status requested from peer")
            self._on_receive_rr_rnr_rej_query()
        else:
            # Received peer's RR status, peer no longer busy
            self._log.debug(
                "RR notification received from peer N(R)=%d", frame.nr
            )
            # AX.25 sect 4.3.2.1: "acknowledges properly received
            # I frames up to and including N(R)-1"
            self._ack_outstanding((frame.nr - 1) % self._modulo)
            self._peer_busy = False
            self._send_next_iframe()

    def _on_receive_rnr(self, frame):
        if frame.pf:
            # Peer requesting our RNR status
            self._log.debug("RNR status requested from peer")
            self._on_receive_rr_rnr_rej_query()
        else:
            # Received peer's RNR status, peer is busy
            self._log.debug("RNR notification received from peer")
            # AX.25 sect 4.3.2.2: "Frames up to N(R)-1 are acknowledged."
            self._ack_outstanding((frame.nr - 1) % self._modulo)
            self._peer_busy = True

    def _on_receive_rej(self, frame):
        if frame.pf:
            # Peer requesting rejected frame status.
            self._log.debug("REJ status requested from peer")
            self._on_receive_rr_rnr_rej_query()
        else:
            # Reject reject.
            self._log.debug("REJ notification received from peer")
            # AX.25 sect 4.3.2.3: "Any frames sent with a sequence number
            # of N(R)-1 or less are acknowledged."
            self._ack_outstanding((frame.nr - 1) % self._modulo)
            # AX.25 2.2 section 6.4.7 says we set V(S) to this frame's
            # N(R) and begin re-transmission.
            self._log.debug("Set state V(S) from frame N(R) = %d", frame.nr)
            self._update_state(
                "_send_state", value=frame.nr, comment="from REJ N(R)"
            )
            self._send_next_iframe()

    def _on_receive_srej(self, frame):
        if frame.pf:
            # AX.25 2.2 sect 4.3.2.4: "If the P/F bit in the SREJ is set to
            # '1', then I frames numbered up to N(R)-1 inclusive are considered
            # as acknowledged."
            self._log.debug("SREJ received with P/F=1")
            self._ack_outstanding((frame.nr - 1) % self._modulo)

        # Re-send the outstanding frame
        self._log.debug("Re-sending I-frame %d due to SREJ", frame.nr)
        self._transmit_iframe(frame.nr)

    def _on_receive_rr_rnr_rej_query(self):
        """
        Handle a RR or RNR query
        """
        if self._local_busy:
            self._log.debug("RR poll request from peer: we're busy")
            self._send_rnr_notification()
        else:
            self._log.debug("RR poll request from peer: we're ready")
            self._send_rr_notification()

    def _ack_outstanding(self, nr):
        """
        Receive all frames up to N(R)-1
        """
        self._log.debug("%d through to %d are received", self._recv_seq, nr)
        while self._recv_seq != nr:
            if self._log.isEnabledFor(logging.DEBUG):
                self._log.debug("Pending frames: %r", self._pending_iframes)

            self._log.debug("ACKing N(R)=%s", self._recv_seq)
            try:
                frame = self._pending_iframes.pop(self._recv_seq)
                if self._log.isEnabledFor(logging.DEBUG):
                    self._log.debug(
                        "Popped %s off pending queue, N(R)s pending: %r",
                        frame,
                        self._pending_iframes,
                    )
            except KeyError:
                if self._log.isEnabledFor(logging.DEBUG):
                    self._log.debug(
                        "ACK to unexpected N(R) number %s, pending: %r",
                        self._recv_seq,
                        self._pending_iframes,
                    )
            finally:
                self._update_state(
                    "_recv_seq", delta=1, comment="ACKed by peer N(R)"
                )

    def _on_receive_test(self, frame):
        self._log.debug("Received TEST response: %s", frame)
        if not self._testframe_handler:
            return

        handler = self._testframe_handler()
        if not handler:
            # It's dead now.
            self._testframe_handler = None
            return

        handler._on_receive(frame)

    def _on_test_done(self, handler, **kwargs):
        if not self._testframe_handler:
            self._log.debug("TEST completed without frame handler")
            return

        real_handler = self._testframe_handler()
        if (real_handler is not None) and (handler is not real_handler):
            self._log.debug("TEST completed with stale handler")
            return

        self._log.debug("TEST completed, removing handler")
        self._testframe_handler = None

    def _on_receive_frmr(self, frame):
        # We just received a FRMR.
        self._log.warning("Received FRMR from peer: %s", frame)
        if self._frmrframe_handler is not None:
            # Pass to handler
            self._frmrframe_handler(frame)
        else:
            # No handler, send SABM to recover (this is clearly an AX.25 2.0
            # station)
            self._send_sabm()

    def _on_receive_sabm(self, frame):
        extended = isinstance(frame, AX25SetAsyncBalancedModeExtendedFrame)
        self._log.info("Received SABM%s", "E" if extended else "")
        if extended:
            # If we don't know the protocol of the peer, we can safely assume
            # AX.25 2.2 now.
            if self._protocol == AX25Version.UNKNOWN:
                self._log.info("Assuming sender is AX.25 2.2")
                self._protocol = AX25Version.AX25_22

            # Make sure both ends are enabled for AX.25 2.2
            if self._station()._protocol != AX25Version.AX25_22:
                # We are not in AX.25 2.2 mode.
                #
                # "A TNC that uses a version of AX.25 prior to v2.2 responds
                # with a FRMR".  W bit indicates the control field was not
                # understood.
                self._log.warning(
                    "Sending FRMR as we are not in AX.25 2.2 mode"
                )
                return self._send_frmr(frame, w=True)

            if self._protocol != AX25Version.AX25_22:
                # The other station is not in AX.25 2.2 mode.
                #
                # "If the TNC is not capable of accepting a SABME, it
                # responds with a DM frame".
                self._log.warning(
                    "Sending DM as peer is not in AX.25 2.2 mode"
                )
                return self._send_dm()

        # Set up the connection state
        self._init_connection(extended)

        # Are we already connecting ourselves to this station?  If yes,
        # we should just treat their SABM(E) as a UA, since _clearly_ both
        # parties wish to connect.
        if self._state == AX25PeerState.CONNECTING:
            self._log.info(
                "Auto-accepting incoming connection as we are waiting for "
                "UA from our connection attempt."
            )
            self._sabmframe_handler()
        else:
            # Set the incoming connection state, and emit a signal via the
            # station's 'connection_request' signal.
            self._log.debug("Preparing incoming connection")
            self._set_conn_state(AX25PeerState.INCOMING_CONNECTION)
            self._start_connect_ack_timer()
            self._log.debug("Announcing incoming connection")
            self._station().connection_request.emit(peer=self)

    def _start_connect_ack_timer(self):
        self._start_ack_timer(self._on_incoming_connect_timeout)

    def _start_disconnect_ack_timer(self):
        self._start_ack_timer(self._on_disc_ua_timeout)

    def _start_ack_timer(self, handler):
        self._ack_timeout_handle = self._loop.call_later(
            self._ack_timeout, handler
        )

    def _stop_ack_timer(self):
        if self._ack_timeout_handle is not None:
            self._ack_timeout_handle.cancel()

        self._ack_timeout_handle = None

    def _on_incoming_connect_timeout(self):
        if self._state is AX25PeerState.INCOMING_CONNECTION:
            self._log.info("Incoming connection timed out")
            self._ack_timeout_handle = None
            self.reject()
        else:
            self._log.debug(
                "Incoming connection time-out in state %s", self._state.name
            )

    def _on_connect_response(self, response, **kwargs):
        # Handle the connection result.
        self._log.debug("Connection response: %r", response)
        if response == "ack":
            # We're in.
            self._set_conn_state(AX25PeerState.CONNECTED)
        else:
            # Didn't work
            self._set_conn_state(AX25PeerState.DISCONNECTED)

    def _negotiate(self, callback):
        """
        Undertake negotiation with the peer station.
        """
        # Sanity check, don't call this if we know the station won't take it.
        if self._protocol not in (AX25Version.UNKNOWN, AX25Version.AX25_22):
            raise RuntimeError(
                "%s does not support negotiation" % self._protocol.value
            )

        self._log.debug("Attempting protocol negotiation")
        handler = AX25PeerNegotiationHandler(self)
        handler.done_sig.connect(self._on_negotiate_result)
        handler.done_sig.connect(callback)

        handler._go()
        self._set_conn_state(AX25PeerState.NEGOTIATING)
        return

    def _on_negotiate_result(self, response, **kwargs):
        """
        Handle the negotiation response.
        """
        self._log.debug("Negotiation response: %r", response)
        if response in ("frmr", "dm"):
            # Other station did not like this.
            self._log.info(
                "Failed XID negotiation, loading AX.25 2.0 defaults"
            )
            self._process_xid_cop(AX25_20_DEFAULT_XID_COP)
            self._process_xid_hdlcoptfunc(AX25_20_DEFAULT_XID_HDLCOPTFUNC)
            self._process_xid_ifieldlenrx(AX25_20_DEFAULT_XID_IFIELDRX)
            self._process_xid_winszrx(AX25_20_DEFAULT_XID_WINDOWSZRX)
            self._process_xid_acktimer(AX25_20_DEFAULT_XID_ACKTIMER)
            self._process_xid_retrycounter(AX25_20_DEFAULT_XID_RETRIES)
            if self._protocol in (AX25Version.UNKNOWN, AX25Version.AX25_22):
                self._log.info("Downgrading to AX.25 2.0 due to failed XID")
                self._protocol = AX25Version.AX25_20
                self._modulo128 = False
        elif self._protocol != AX25Version.AX25_22:
            # Clearly this station understands AX.25 2.2
            self._log.info("Upgrading to AX.25 2.2 due to successful XID")
            self._protocol = AX25Version.AX25_22

        self._negotiated = True
        self._log.debug("XID negotiation complete")
        self._set_conn_state(AX25PeerState.DISCONNECTED)

    def _init_connection(self, extended):
        """
        Initialise the AX.25 connection.
        """
        if extended:
            # Set the maximum outstanding frames variable
            self._log.debug("Initialising AX.25 2.2 mod128 connection")
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
            self._log.debug("Initialising AX.25 2.0/2.2 mod8 connection")
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
        self._log.debug("Resetting the peer state")

        # Reset our state
        self._update_state("_send_state", value=0, comment="reset")
        self._update_state("_send_seq", value=0, comment="reset")
        self._update_state("_recv_state", value=0, comment="reset")
        self._update_state("_recv_seq", value=0, comment="reset")

        # Unacknowledged I-frames to be ACKed
        self._pending_iframes = {}

        # Data pending to be sent.
        self._pending_data = []

    def _set_conn_state(self, state):
        if self._state is state:
            # Nothing to do
            return

        # Update the state
        self._log.info("Connection state change: %s→%s", self._state, state)
        self._state = state

        # Notify any observers that the state changed
        self.connect_state_changed.emit(
            station=self._station(), peer=self, state=self._state
        )

    def _on_disc_ua_timeout(self):
        if self._state is AX25PeerState.DISCONNECTING:
            self._log.info("DISC timed out, assuming we're disconnected")
            # Assume we are disconnected.
            self._ack_timeout_handle = None
            self._on_disconnect()
        else:
            self._log.debug("DISC time-out in state %s", self._state.name)

    def _on_disconnect(self):
        """
        Clean up the connection.
        """
        self._log.info("Disconnected from peer")

        # Cancel disconnect timers
        self._stop_ack_timer()

        # Set ourselves as disconnected
        self._set_conn_state(AX25PeerState.DISCONNECTED)

        # Reset our state
        self._reset_connection_state()

        # Clear data pending to be sent.
        self._pending_data = []

    def _on_receive_disc(self):
        """
        Handle a disconnect request from this peer.
        """
        # Send a UA and set ourselves as disconnected
        self._log.info("Received DISC from peer")
        self._send_ua()
        self._on_disconnect()

    def _on_receive_ua(self):
        """
        Handle a Un-numbered Acknowledge from the peer
        """
        self._log.info("Received UA from peer")
        if self._uaframe_handler:
            self._uaframe_handler()
        else:
            self._log.debug("No one cares about the UA")

    def _on_receive_dm(self):
        """
        Handle a disconnect request from this peer.
        """
        if self._state is AX25PeerState.CONNECTED:
            # Set ourselves as disconnected
            self._log.info("Received DM from peer")
            self._on_disconnect()
        elif self._dmframe_handler:
            self._log.debug(
                "Received DM from peer whilst in state %s", self._state.name
            )
            self._dmframe_handler()
            self._dmframe_handler = None
        else:
            self._log.debug(
                "No one cares about the DM in state %s", self._state.name
            )

    def _on_receive_xid(self, frame):
        """
        Handle a request to negotiate parameters.
        """
        self._log.info("Received XID from peer")
        if self._station()._protocol != AX25Version.AX25_22:
            # Not supporting this in AX.25 2.0 mode
            self._log.warning(
                "Received XID from peer, we are not in AX.25 2.2 mode"
            )
            return self._send_frmr(frame, w=True)

        if self._state in (
            AX25PeerState.CONNECTING,
            AX25PeerState.DISCONNECTING,
        ):
            # AX.25 2.2 sect 4.3.3.7: "A station receiving an XID command
            # returns an XID response unless a UA response to a mode setting
            # command is awaiting transmission, or a FRMR condition exists".
            self._log.warning(
                "UA is pending, dropping received XID (state %s)",
                self._state.name,
            )
            return

        # We have received an XID, AX.25 2.0 and earlier stations do not know
        # this frame, so clearly this is at least AX.25 2.2.
        if self._protocol == AX25Version.UNKNOWN:
            self._log.info("Assuming AX.25 2.2 peer")
            self._protocol = AX25Version.AX25_22

        # Don't process the contents of the frame unless FI and GI match.
        if (frame.fi == frame.FI) and (frame.gi == frame.GI):
            # Key these by PI
            params = dict([(p.pi, p) for p in frame.parameters])

            # Process the parameters in this order

            self._process_xid_cop(
                params.get(
                    AX25XIDParameterIdentifier.ClassesOfProcedure,
                    AX25_22_DEFAULT_XID_COP,
                )
            )

            self._process_xid_hdlcoptfunc(
                params.get(
                    AX25XIDParameterIdentifier.HDLCOptionalFunctions,
                    AX25_22_DEFAULT_XID_HDLCOPTFUNC,
                )
            )

            self._process_xid_ifieldlenrx(
                params.get(
                    AX25XIDParameterIdentifier.IFieldLengthReceive,
                    AX25_22_DEFAULT_XID_IFIELDRX,
                )
            )

            self._process_xid_winszrx(
                params.get(
                    AX25XIDParameterIdentifier.WindowSizeReceive,
                    AX25_22_DEFAULT_XID_WINDOWSZRX,
                )
            )

            self._process_xid_acktimer(
                params.get(
                    AX25XIDParameterIdentifier.AcknowledgeTimer,
                    AX25_22_DEFAULT_XID_ACKTIMER,
                )
            )

            self._process_xid_retrycounter(
                params.get(
                    AX25XIDParameterIdentifier.Retries,
                    AX25_22_DEFAULT_XID_RETRIES,
                )
            )

        if frame.header.cr:
            # Other station is requesting negotiation, send response.
            self._log.debug("Sending XID response")
            self._send_xid(cr=False)
        elif self._xidframe_handler is not None:
            # This is a reply to our XID
            self._log.debug("Forwarding XID response")
            self._xidframe_handler(frame)
            self._xidframe_handler = None
        else:
            # No one cared?
            self._log.debug("Received XID response but no one cares")

        # Having received the XID, we consider ourselves having negotiated
        # parameters.  Future connections will skip this step.
        self._negotiated = True
        self._log.debug("XID negotiation complete")

    def _process_xid_cop(self, param):
        if param.pv is None:
            # We were told to use defaults.  This is from a XID frame,
            # so assume AX.25 2.2 defaults.
            self._log.debug("XID: Assuming default Classes of Procedure")
            param = AX25_22_DEFAULT_XID_COP

        # Ensure we don't confuse ourselves if the station sets both
        # full-duplex and half-duplex bits.  Half-duplex is always a
        # safe choice in case of such confusion.
        self._full_duplex = (
            self._full_duplex
            and param.full_duplex
            and (not param.half_duplex)
        )
        self._log.debug("XID: Setting full-duplex: %s", self._full_duplex)

    def _process_xid_hdlcoptfunc(self, param):
        if param.pv is None:
            # We were told to use defaults.  This is from a XID frame,
            # so assume AX.25 2.2 defaults.
            self._log.debug("XID: Assuming default HDLC Optional Features")
            param = AX25_22_DEFAULT_XID_HDLCOPTFUNC

        # Negotiable parts of this parameter are:
        # - SREJ/REJ bits
        if param.srej and param.rej:
            reject_mode = AX25RejectMode.SELECTIVE_RR
        elif param.srej:
            reject_mode = AX25RejectMode.SELECTIVE
        else:
            # Technically this means also the invalid SREJ=0 REJ=0,
            # we'll assume they meant REJ=1 in that case.
            reject_mode = AX25RejectMode.IMPLICIT

        # We take the option with the lowest precedence
        if self._reject_mode.precedence > reject_mode.precedence:
            self._reject_mode = reject_mode
        self._log.debug("XID: Set reject mode: %s", self._reject_mode.value)

        # - Modulo 8/128: again, unless the station positively says
        #   "I support modulo 128", use modulo 8.
        #   The remote station is meant to set either modulo128 *OR* modulo8.
        #   If we have it enabled our end, and they either have the modulo8
        #   bit set, or the modulo128 bit clear, then fail back to modulo8.
        if self._modulo128 and ((not param.modulo128) or param.modulo8):
            self._modulo128 = False
        self._log.debug("XID: Set modulo128 mode: %s", self._modulo128)

    def _process_xid_ifieldlenrx(self, param):
        if param.pv is None:
            # We were told to use defaults.  This is from a XID frame,
            # so assume AX.25 2.2 defaults.
            self._log.debug("XID: Assuming default I-Field Receive Length")
            param = AX25_22_DEFAULT_XID_IFIELDRX

        self._max_ifield = min(
            [self._max_ifield, int(param.value / 8)]  # Value is given in bits
        )
        self._log.debug(
            "XID: Setting I-Field Receive Length: %d", self._max_ifield
        )

    def _process_xid_winszrx(self, param):
        if param.pv is None:
            # We were told to use defaults.  This is from a XID frame,
            # so assume AX.25 2.2 defaults.
            self._log.debug("XID: Assuming default Window Size Receive")
            param = AX25_22_DEFAULT_XID_WINDOWSZRX

        self._max_outstanding = min(
            [
                (
                    self._max_outstanding_mod128
                    if self._modulo128
                    else self._max_outstanding_mod8
                ),
                param.value,
            ]
        )
        self._log.debug(
            "XID: Setting Window Size Receive: %d", self._max_outstanding
        )

    def _process_xid_acktimer(self, param):
        if param.pv is None:
            # We were told to use defaults.  This is from a XID frame,
            # so assume AX.25 2.2 defaults.
            self._log.debug("XID: Assuming default ACK timer")
            param = AX25_22_DEFAULT_XID_ACKTIMER

        self._ack_timeout = (
            max([self._ack_timeout * 1000, param.value]) / 1000
        )
        self._log.debug(
            "XID: Setting ACK timeout: %.3f sec", self._ack_timeout
        )

    def _process_xid_retrycounter(self, param):
        if param.pv is None:
            # We were told to use defaults.  This is from a XID frame,
            # so assume AX.25 2.2 defaults.
            self._log.debug("XID: Assuming default retry limit")
            param = AX25_22_DEFAULT_XID_RETRIES

        self._max_retries = max([self._max_retries, param.value])
        self._log.debug("XID: Setting retry limit: %d", self._max_retries)

    def _send_sabm(self):
        """
        Send a SABM(E) frame to the remote station.
        """
        self._log.info("Sending SABM%s", "E" if self._modulo128 else "")
        SABMClass = (
            AX25SetAsyncBalancedModeExtendedFrame
            if self._modulo128
            else AX25SetAsyncBalancedModeFrame
        )

        self._transmit_frame(
            SABMClass(
                destination=self.address.normcopy(ch=True),
                source=self._station().address.normcopy(ch=False),
                repeaters=self.reply_path,
            )
        )
        if self._state is not AX25PeerState.INCOMING_CONNECTION:
            self._set_conn_state(AX25PeerState.CONNECTING)

    def _send_xid(self, cr):
        self._transmit_frame(
            AX25ExchangeIdentificationFrame(
                destination=self.address.normcopy(ch=True),
                source=self._station().address.normcopy(ch=False),
                repeaters=self.reply_path,
                parameters=[
                    AX25XIDClassOfProceduresParameter(
                        half_duplex=not self._full_duplex,
                        full_duplex=self._full_duplex,
                    ),
                    AX25XIDHDLCOptionalFunctionsParameter(
                        rej=(
                            self._reject_mode
                            in (
                                AX25RejectMode.IMPLICIT,
                                AX25RejectMode.SELECTIVE_RR,
                            )
                        ),
                        srej=(
                            self._reject_mode
                            in (
                                AX25RejectMode.SELECTIVE,
                                AX25RejectMode.SELECTIVE_RR,
                            )
                        ),
                        modulo8=(not self._modulo128),
                        modulo128=(self._modulo128),
                    ),
                    AX25XIDIFieldLengthTransmitParameter(
                        self._max_ifield * 8
                    ),
                    AX25XIDIFieldLengthReceiveParameter(
                        self._max_ifield_rx * 8
                    ),
                    AX25XIDWindowSizeTransmitParameter(
                        self._max_outstanding_mod128
                        if self._modulo128
                        else self._max_outstanding_mod8
                    ),
                    AX25XIDWindowSizeReceiveParameter(
                        self._max_outstanding_mod128
                        if self._modulo128
                        else self._max_outstanding_mod8
                    ),
                    AX25XIDAcknowledgeTimerParameter(
                        int(self._ack_timeout * 1000)
                    ),
                    AX25XIDRetriesParameter(self._max_retries),
                ],
                cr=cr,
            )
        )

    def _send_dm(self):
        """
        Send a DM frame to the remote station.
        """
        self._log.info("Sending DM")
        self._transmit_frame(
            AX25DisconnectModeFrame(
                destination=self.address.normcopy(ch=True),
                source=self._station().address.normcopy(ch=False),
                repeaters=self.reply_path,
            )
        )

    def _send_disc(self):
        """
        Send a DISC frame to the remote station.
        """
        self._log.info("Sending DISC")
        self._transmit_frame(
            AX25DisconnectFrame(
                destination=self.address.normcopy(ch=True),
                source=self._station().address.normcopy(ch=False),
                repeaters=self.reply_path,
            )
        )

    def _send_ua(self):
        """
        Send a UA frame to the remote station.
        """
        self._log.info("Sending UA")
        self._transmit_frame(
            AX25UnnumberedAcknowledgeFrame(
                destination=self.address.normcopy(ch=True),
                source=self._station().address.normcopy(ch=False),
                repeaters=self.reply_path,
            )
        )

    def _send_frmr(self, frame, w=False, x=False, y=False, z=False):
        """
        Send a FRMR frame to the remote station.
        """
        self._log.debug("Sending FRMR in reply to %s", frame)

        # AX.25 2.0 sect 2.4.5: "After sending the FRMR frame, the sending DXE
        # will enter the frame reject condition. This condition is cleared when
        # the DXE that sent the FRMR frame receives a SABM or DISC command, or
        # a DM response frame. Any other command received while the DXE is in
        # the frame reject state will cause another FRMR to be sent out with
        # the same information field as originally sent."
        self._set_conn_state(AX25PeerState.FRMR)

        # See https://www.tapr.org/pub_ax25.html
        self._transmit_frame(
            AX25FrameRejectFrame(
                destination=self.address.normcopy(ch=True),
                source=self._station().address.normcopy(ch=False),
                repeaters=self.reply_path,
                w=w,
                x=x,
                y=y,
                z=z,
                vr=self._recv_state,
                vs=self._send_state,
                frmr_cr=frame.header.cr,
                frmr_control=frame.control,
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
        self._log.debug("Waiting before sending RR notification")
        self._cancel_rr_notification()
        self._rr_notification_timeout_handle = self._loop.call_later(
            self._rr_delay, self._send_rr_notification
        )

    def _send_rr_notification(self):
        """
        Send a RR notification frame
        """
        # "If there are no outstanding I frames, the receiving device will
        # send a RR frame with N(R) equal to V(R). The receiving DXE may wait
        # a small period of time before sending the RR frame to be sure
        # additional I frames are not being transmitted."

        self._cancel_rr_notification()
        if self._state is AX25PeerState.CONNECTED:
            self._log.debug(
                "Sending RR with N(R) == V(R) == %d", self._recv_state
            )
            self._update_recv_seq()
            self._transmit_frame(
                self._RRFrameClass(
                    destination=self.address.normcopy(ch=True),
                    source=self._station().address.normcopy(ch=False),
                    repeaters=self.reply_path,
                    pf=False,
                    nr=self._recv_state,
                )
            )

    def _send_rnr_notification(self):
        """
        Send a RNR notification if the RNR interval has elapsed.
        """
        if self._state is AX25PeerState.CONNECTED:
            now = self._loop.time()
            if (now - self._last_rnr_sent) > self._rnr_interval:
                self._update_recv_seq()
                self._transmit_frame(
                    self._RNRFrameClass(
                        destination=self.address.normcopy(ch=True),
                        source=self._station().address.normcopy(ch=False),
                        repeaters=self.reply_path,
                        nr=self._recv_seq,
                        pf=False,
                    )
                )
                self._last_rnr_sent = now

    def _send_next_iframe(self):
        """
        Send the next I-frame, if there aren't too many frames pending.
        """
        if len(self._pending_iframes) >= self._max_outstanding:
            self._log.debug("Waiting for pending I-frames to be ACKed")
            return

        # AX.25 2.2 spec 6.4.1: "Whenever a TNC has an I frame to transmit,
        # it sends the I frame with the N(S) of the control field equal to
        # its current send state variable V(S)…"
        ns = self._send_state
        if ns not in self._pending_iframes:
            if not self._pending_data:
                # No data waiting
                self._log.debug("No data pending transmission")
                return

            # Retrieve the next pending I-frame payload and add it to the queue
            self._pending_iframes[ns] = self._pending_data.pop(0)
            self._log.debug("Creating new I-Frame %d", ns)

        # Send it
        self._log.debug("Sending new I-Frame %d", ns)
        self._transmit_iframe(ns)

        # "After the I frame is sent, the send state variable is incremented
        # by one."
        self._update_state(
            "_send_state", delta=1, comment="send next I-frame"
        )

        if self._log.isEnabledFor(logging.DEBUG):
            self._log.debug("Pending frames: %r", self._pending_iframes)

    def _transmit_iframe(self, ns):
        """
        Transmit the I-frame identified by the given N(S) parameter.
        """
        # "Whenever a DXE has an I frame to transmit, it will send the I frame
        # with N(S) of the control field equal to its current send state
        # variable V(S). Once the I frame is sent, the send state variable is
        # incremented by one. If timer T1 is not running, it should be
        # started. If timer T1 is running, it should be restarted."

        # "If it has an I frame to send, that I frame may be sent with the
        # transmitted N(R) equal to its receive state variable V(R) (thus
        # acknowledging the received frame)."
        (pid, payload) = self._pending_iframes[ns]
        self._log.debug(
            "Sending I-frame N(R)=%d N(S)=%d PID=0x%02x Payload=%r",
            self._recv_state,
            ns,
            pid,
            payload,
        )

        self._update_send_seq()
        self._update_recv_seq()

        self._transmit_frame(
            self._IFrameClass(
                destination=self.address.normcopy(ch=True),
                source=self._station().address.normcopy(ch=False),
                repeaters=self.reply_path,
                nr=self._recv_state,  # N(R) == V(R)
                ns=ns,
                pf=False,
                pid=pid,
                payload=payload,
            )
        )

    def _transmit_frame(self, frame, callback=None):
        self.sent_frame.emit(frame=frame, peer=self)

        # Update the last activity timestamp
        self._last_act = self._loop.time()

        # Reset the idle timer
        self._reset_idle_timeout()
        return self._station()._interface().transmit(frame, callback=None)

    def _update_state(self, prop, delta=None, value=None, comment=""):
        if comment:
            comment = " " + comment

        if value is None:
            value = getattr(self, prop)

        if delta is not None:
            value += delta
            comment += " delta=%s" % delta

        # Always apply modulo op
        value %= self._modulo

        self._log.debug(
            "%s = %s" + comment, getattr(self, "%s_name" % prop), value
        )
        setattr(self, prop, value)

    def _update_send_seq(self):
        """
        Update the send sequence.  Call this just prior to sending an
        I-frame.
        """
        # "Just prior to the transmission of the I frame, N(S) is updated to
        # equal the send state variable." § 2.3.2.4.2
        # _send_seq (aka N(S)) ← _send_state (aka V(S))
        self._update_state(
            "_send_seq", value=self._send_state, comment="from V(S)"
        )

    def _update_recv_seq(self):
        """
        Update the send sequence.  Call this just prior to sending an
        I-frame or S-frame.
        """
        # "Prior to sending an I or S frame, this variable is updated to equal
        # that of the received state variable" § 2.3.2.4.4
        # _recv_seq (aka N(R)) ← _recv_state (aka V(R))
        self._update_state(
            "_recv_seq", value=self._recv_state, comment="from V(R)"
        )


class AX25PeerHelper(object):
    """
    This is a base class for handling more complex acts like connecting,
    negotiating parameters or sending test frames.
    """

    def __init__(self, peer, timeout):
        self._peer = peer
        self._loop = peer._loop
        self._log = peer._log.getChild(self.__class__.__name__)
        self._done = False
        self._timeout = timeout
        self._timeout_handle = None

        # Signal on "done" or time-out.
        self.done_sig = Signal()

    @property
    def peer(self):
        """
        Return the peer being pinged
        """
        return self._peer

    def _start_timer(self):
        self._timeout_handle = self._loop.call_later(
            self._timeout, self._on_timeout
        )

    def _stop_timer(self):
        if self._timeout_handle is None:
            return

        self._timeout_handle.cancel()
        self._timeout_handle = None

    def _finish(self, **kwargs):
        if self._done:
            return

        self._done = True
        self._stop_timer()
        self._log.debug("finished: %r", kwargs)
        self.done_sig.emit(**kwargs)


class AX25PeerConnectionHandler(AX25PeerHelper):
    """
    This class is used to manage the connection to the peer station.  If the
    station has not yet negotiated with the peer, this is done (unless we know
    the peer won't tolerate it), then a SABM or SABME connection is made.
    """

    def __init__(self, peer):
        super(AX25PeerConnectionHandler, self).__init__(
            peer, peer._ack_timeout
        )
        self._retries = peer._max_retries

    def _go(self):
        if self.peer._negotiated:
            # Already done, we can connect immediately
            self._log.debug("XID negotiation already done")
            self._on_negotiated(response="already")
        elif (
            self.peer._protocol
            not in (AX25Version.AX25_22, AX25Version.UNKNOWN)
        ) or (self.peer._station()._protocol != AX25Version.AX25_22):
            # Not compatible, just connect
            self._log.debug("XID negotiation not supported")
            self._on_negotiated(response="not_compatible")
        else:
            # Need to negotiate first.
            self._log.debug("XID negotiation to be attempted")
            self.peer._negotiate(self._on_negotiated)

    def _on_negotiated(self, response, **kwargs):
        if response in (
            "xid",
            "frmr",
            "dm",
            "already",
            "not_compatible",
            "retry",
        ):
            # We successfully negotiated with this station (or it was not
            # required)
            if (
                (self.peer._uaframe_handler is not None)
                or (self.peer._frmrframe_handler is not None)
                or (self.peer._dmframe_handler is not None)
            ):
                # We're handling another frame now.
                self._log.debug("Received XID, but we're busy")
                self._finish(response="station_busy")
                return

            self._log.debug(
                "XID done (state %s), beginning connection", response
            )
            self.peer._uaframe_handler = self._on_receive_ua
            self.peer._frmrframe_handler = self._on_receive_frmr
            self.peer._dmframe_handler = self._on_receive_dm
            self.peer._send_sabm()
            self._start_timer()
        else:
            self._log.debug("Bailing out due to XID response %s", response)
            self._finish(response=response)

    def _on_receive_ua(self):
        # Peer just acknowledged our connection
        self._log.debug("UA received")
        self._log.info("Connection is established")
        self.peer._init_connection(self.peer._modulo128)
        self._finish(response="ack")

    def _on_receive_frmr(self):
        # Peer just rejected our connect frame, begin FRMR recovery.
        self._log.debug("FRMR received, recovering")
        self.peer._send_dm()
        self._finish(response="frmr")

    def _on_receive_dm(self):
        # Peer just rejected our connect frame.
        self._log.debug("DM received, bailing here")
        self._finish(response="dm")

    def _on_timeout(self):
        self._unhook()
        if self._retries:
            self._retries -= 1
            self._log.debug("Retrying, remaining=%d", self._retries)
            self._on_negotiated(response="retry")
        else:
            self._log.debug("Giving up")
            self._finish(response="timeout")

    def _unhook(self):
        if self.peer._uaframe_handler == self._on_receive_ua:
            self._log.debug("Unhooking UA handler")
            self.peer._uaframe_handler = None

        if self.peer._frmrframe_handler == self._on_receive_frmr:
            self._log.debug("Unhooking FRMR handler")
            self.peer._frmrframe_handler = None

        if self.peer._dmframe_handler == self._on_receive_dm:
            self._log.debug("Unhooking DM handler")
            self.peer._dmframe_handler = None

    def _finish(self, **kwargs):
        self._unhook()
        super(AX25PeerConnectionHandler, self)._finish(**kwargs)


class AX25PeerNegotiationHandler(AX25PeerHelper):
    """
    This class is used to manage the negotiation of link parameters with the
    peer.  Notably, if the peer is an AX.25 2.0, this loads defaults for that
    revision of AX.25 and handles the FRMR/DM condition.
    """

    def __init__(self, peer):
        super(AX25PeerNegotiationHandler, self).__init__(
            peer, peer._ack_timeout
        )
        self._retries = peer._max_retries

    def _go(self):
        # Specs say AX.25 2.2 should respond with XID and 2.0 should respond
        # with FRMR.  It is also possible we could get a DM as some buggy AX.25
        # implementations respond with that in reply to unknown frames.
        if (
            (self.peer._xidframe_handler is not None)
            or (self.peer._frmrframe_handler is not None)
            or (self.peer._dmframe_handler is not None)
        ):
            raise RuntimeError("Another frame handler is busy")

        self.peer._xidframe_handler = self._on_receive_xid
        self.peer._frmrframe_handler = self._on_receive_frmr
        self.peer._dmframe_handler = self._on_receive_dm

        self.peer._send_xid(cr=True)
        self._start_timer()

    def _on_receive_xid(self, *args, **kwargs):
        # XID frame received, we can consider ourselves done.
        self._finish(response="xid")

    def _on_receive_frmr(self, *args, **kwargs):
        # FRMR received.  Evidently this station does not like XID.  Caller
        # will need to kiss and make up with the offended legacy station either
        # with a SABM or DM.  We can be certain this is not an AX.25 2.2 station.
        self._finish(response="frmr")

    def _on_receive_dm(self, *args, **kwargs):
        # DM received.  This is not strictly in spec, but we'll treat it as a
        # legacy AX.25 station telling us we're disconnected.  No special
        # handling needed.
        self._finish(response="dm")

    def _on_timeout(self):
        # No response received
        if self._retries:
            self._retries -= 1
            self._go()
        else:
            self._finish(response="timeout")

    def _finish(self, **kwargs):
        # Clean up hooks
        if self.peer._xidframe_handler == self._on_receive_xid:
            self.peer._xidframe_handler = None
        if self.peer._frmrframe_handler == self._on_receive_frmr:
            self.peer._frmrframe_handler = None
        if self.peer._dmframe_handler == self._on_receive_dm:
            self.peer._dmframe_handler = None
        super(AX25PeerNegotiationHandler, self)._finish(**kwargs)


class AX25PeerTestHandler(AX25PeerHelper):
    """
    This class is used to manage the sending of a TEST frame to the peer
    station and receiving the peer reply.  Round-trip time is made available
    in case the calling application needs it.
    """

    def __init__(self, peer, payload, timeout):
        super(AX25PeerTestHandler, self).__init__(peer, timeout)

        # Create the frame to send
        self._tx_frame = AX25TestFrame(
            destination=peer.address,
            source=peer._station().address,
            repeaters=peer._station().reply_path,
            payload=payload,
            cr=True,
        )

        # Store the received frame here
        self._rx_frame = None

        # Time of transmission
        self._tx_time = None

        # Time of reception
        self._rx_time = None

    @property
    def tx_time(self):
        """
        Return the transmit time, as measured by the IO loop
        """
        return self._tx_time

    @property
    def tx_frame(self):
        """
        Return the transmitted frame
        """
        return self._tx_frame

    @property
    def rx_time(self):
        """
        Return the receive time, as measured by the IO loop
        """
        return self._rx_time

    @property
    def rx_frame(self):
        """
        Return the received frame
        """
        return self._rx_frame

    def _go(self):
        """
        Start the transmission.
        """
        if self.peer._testframe_handler is not None:
            raise RuntimeError("Test frame already pending")
        self.peer._testframe_handler = weakref.ref(self)
        self.peer._transmit_frame(self.tx_frame, callback=self._transmit_done)
        self._start_timer()

    def _transmit_done(self, *args, **kwargs):
        """
        Note the time that the transmission took place.
        """
        self._tx_time = self.peer._loop.time()

    def _on_receive(self, frame, **kwargs):
        """
        Process the incoming frame.
        """
        if self._done:
            # We are done
            return

        # Stop the clock!
        self._rx_time = self.peer._loop.time()

        # Stash the result and notify the caller
        self._rx_frame = frame
        self._finish(handler=self)

    def _on_timeout(self):
        """
        Process a time-out
        """
        self._finish(handler=self)

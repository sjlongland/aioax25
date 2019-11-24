#!/usr/bin/env python3

"""
AX.25 Station Peer interface.

This is used as the "proxy" for interacting with a remote AX.25 station.
"""

from .signal import Signal

import weakref
import enum

from .version import AX25Version
from .frame import AX25Frame, AX25Path, AX25SetAsyncBalancedModeFrame, \
        AX25SetAsyncBalancedModeExtendedFrame, \
        AX25ExchangeIdentificationFrame, AX25UnnumberedAcknowledgeFrame, \
        AX25TestFrame, AX25DisconnectFrame, AX25DisconnectModeFrame, \
        AX25FrameRejectFrame, AX25RawFrame, \
        AX2516BitInformationFrame, AX258BitInformationFrame, \
        AX258BitReceiveReadyFrame, AX2516BitReceiveReadyFrame, \
        AX258BitReceiveNotReadyFrame, AX2516BitReceiveNotReadyFrame, \
        AX258BitRejectFrame, AX2516BitRejectFrame, \
        AX258BitSelectiveRejectFrame, AX2516BitSelectiveRejectFrame, \
        AX25InformationFrameMixin, AX25SupervisoryFrameMixin, \
        AX25XIDParameterIdentifier, AX25XIDClassOfProceduresParameter, \
        AX25XIDHDLCOptionalFunctionsParameter, \
        AX25XIDIFieldLengthTransmitParameter, \
        AX25XIDIFieldLengthReceiveParameter, \
        AX25XIDWindowSizeTransmitParameter, \
        AX25XIDWindowSizeReceiveParameter, \
        AX25XIDAcknowledgeTimerParameter, \
        AX25XIDRetriesParameter, \
        AX25_20_DEFAULT_XID_COP, \
        AX25_22_DEFAULT_XID_COP, \
        AX25_20_DEFAULT_XID_HDLCOPTFUNC, \
        AX25_22_DEFAULT_XID_HDLCOPTFUNC, \
        AX25_20_DEFAULT_XID_IFIELDRX, \
        AX25_22_DEFAULT_XID_IFIELDRX, \
        AX25_20_DEFAULT_XID_WINDOWSZRX, \
        AX25_22_DEFAULT_XID_WINDOWSZRX, \
        AX25_20_DEFAULT_XID_ACKTIMER, \
        AX25_22_DEFAULT_XID_ACKTIMER, \
        AX25_20_DEFAULT_XID_RETRIES, \
        AX25_22_DEFAULT_XID_RETRIES


class AX25Peer(object):
    """
    This class is a proxy representation of the remote AX.25 peer that may be
    connected to this station.  The factory for these objects is the
    AX25Station's getpeer method.
    """

    class AX25RejectMode(enum.Enum):
        IMPLICIT = 'implicit'
        SELECTIVE = 'selective'
        SELECTIVE_RR = 'selective_rr'

        # Value precedence:
        _PRECEDENCE = {
                'selective_rr': 2,
                'selective': 1,
                'implicit': 0
        }

        @property
        def precedence(self):
            """
            Get the precedence of this mode.
            """
            return self._PRECEDENCE[self.value]


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


    def __init__(self, station, address, repeaters, max_ifield, max_ifield_rx,
            max_retries, max_outstanding_mod8, max_outstanding_mod128,
            rr_delay, rr_interval, rnr_interval, ack_timeout, idle_timeout,
            protocol, modulo128, log, loop, reject_mode,
            reply_path=None, locked_path=False):
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
        self._max_ifield = max_ifield
        self._max_ifield_rx = max_ifield_rx
        self._max_retries = max_retries
        self._modulo128 = modulo128
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
        self._reject_mode = None
        self._max_outstanding = None    # Decided when SABM(E) received
        self._modulo = None             # Set when SABM(E) received
        self._negotiated = False        # Set to True after XID negotiation
        self._connected = False         # Set to true on SABM UA
        self._last_act   = 0            # Time of last activity
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
        self._incoming_connect_timeout_handle = None
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
        self._uaframe_handler = None
        self._dmframe_handler = None
        self._frmrframe_handler = None

        # Signals:

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

    def ping(self, payload=None, timeout=30.0, callback=None):
        """
        Ping the peer and wait for a response.
        """
        handler = AX25PeerTestHandler(self, bytes(payload or b''), timeout)
        handler.done_sig.connect(self._on_test_done)

        if callback is not None:
            handler.done_sig.connect(callback)

        handler._go()
        return handler

    def connect(self):
        """
        Connect to the remote node.
        """
        if self._state in self.AX25PeerState.DISCONNECTED:
            handler = AX25PeerConnectionHandler(self)
            handler.done_sig.connect(self._on_connect_response)
            handler._go()

    def accept(self):
        """
        Accept an incoming connection from the peer.
        """
        if self._state in self.AX25PeerState.INCOMING_CONNECTION:
            self._log.info('Accepting incoming connection')
            # Send a UA and set ourselves as connected
            self._stop_incoming_connect_timer()
            self._set_conn_state(self.AX25PeerState.CONNECTED)
            self._send_ua()

    def reject(self):
        """
        Reject an incoming connection from the peer.
        """
        if self._state in self.AX25PeerState.INCOMING_CONNECTION:
            self._log.info('Rejecting incoming connection')
            # Send a DM and set ourselves as disconnected
            self._stop_incoming_connect_timer()
            self._set_conn_state(self.AX25PeerState.DISCONNECTED)
            self._send_dm()

    def disconnect(self):
        """
        Disconnect from the remote node.
        """
        if self._state == self.AX25PeerState.CONNECTED:
            self._uaframe_handler = self._on_disconnect
            self._send_disc()

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

        # Update the last activity timestamp
        self._last_act = self._loop.time()

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
        elif isinstance(frame, AX25FrameRejectFrame):
            # FRMR frame
            return self._on_receive_frmr()
        elif isinstance(frame, AX25UnnumberedAcknowledgeFrame):
            # UA frame
            return self._on_receive_ua()
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
        if isinstance(frame, self._RRFrameClass):
            self._on_receive_rr(frame)
        elif isinstance(frame, self._RNRFrameClass):
            self._on_receive_rnr(frame)
        elif isinstance(frame, self._REJFrameClass):
            self._on_receive_rej(frame)
        elif isinstance(frame, self._SREJFrameClass):
            self._on_receive_srej(frame)

    def _on_receive_rr(self, frame):
        if frame.header.pf:
            # Peer requesting our RR status
            self._on_receive_rr_rnr_rej_query()
        else:
            # Received peer's RR status, peer no longer busy
            self._log.debug('RR notification received from peer')
            # AX.25 sect 4.3.2.1: "acknowledges properly received
            # I frames up to and including N(R)-1"
            self._ack_outstanding((frame.nr - 1) % self._modulo)
            self._peer_busy = False
            self._send_next_iframe()

    def _on_receive_rnr(self, frame):
        if frame.header.pf:
            # Peer requesting our RNR status
            self._on_receive_rr_rnr_rej_query()
        else:
            # Received peer's RNR status, peer is busy
            self._log.debug('RNR notification received from peer')
            # AX.25 sect 4.3.2.2: "Frames up to N(R)-1 are acknowledged."
            self._ack_outstanding((frame.nr - 1) % self._modulo)
            self._peer_busy = True

    def _on_receive_rej(self, frame):
        if frame.header.pf:
            # Peer requesting rejected frame status.
            self._on_receive_rr_rnr_rej_query()
        else:
            # Reject reject.
            # AX.25 sect 4.3.2.3: "Any frames sent with a sequence number
            # of N(R)-1 or less are acknowledged."
            self._ack_outstanding((frame.nr - 1) % self._modulo)
            # AX.25 2.2 section 6.4.7 says we set V(S) to this frame's
            # N(R) and begin re-transmission.
            self._send_state = frame.nr
            self._send_next_iframe()

    def _on_receive_srej(self, frame):
        if frame.header.pf:
            # AX.25 2.2 sect 4.3.2.4: "If the P/F bit in the SREJ is set to
            # '1', then I frames numbered up to N(R)-1 inclusive are considered
            # as acknowledged."
            self._ack_outstanding((frame.nr - 1) % self._modulo)

        # Re-send the outstanding frame
        self._log.debug('Re-sending I-frame %d due to SREJ', frame.nr)
        self._transmit_iframe(frame.nr)

    def _on_receive_rr_rnr_rej_query(self):
        """
        Handle a RR or RNR query
        """
        if self._local_busy:
            self._log.debug('RR poll request from peer: we\'re busy')
            self._send_rnr_notification()
        else:
            self._log.debug('RR poll request from peer: we\'re ready')
            self._send_rr_notification()

    def _ack_outstanding(self, nr):
        """
        Receive all frames up to N(R)
        """
        self._log.debug('%d through to %d are received', self._send_state, nr)
        while self._send_state != nr:
            self._pending_iframes.pop(self._send_state)
            self._send_state = (self._send_state + 1) % self._modulo

    def _on_receive_test(self, frame):
        self._log.debug('Received TEST response: %s', frame)
        if not self._testframe_handler:
            return

        handler = self._testframe_handler()
        if not handler:
            return

        self.handler._on_receive(frame)

    def _on_test_done(self, handler, **kwargs):
        if not self._testframe_handler:
            return

        if handler is not self._testframe_handler():
            return

        self._testframe_handler = None

    def _on_receive_frmr(self, frame):
        # We just received a FRMR.
        self._log.warning('Received FRMR from peer: %s', frame)
        if self._frmrframe_handler is not None:
            # Pass to handler
            self._frmrframe_handler(frame)
        else:
            # No handler, send DM to recover
            self._send_dm()

    def _on_receive_sabm(self, frame):
        extended = isinstance(frame, AX25SetAsyncBalancedModeExtendedFrame)
        self._log.info('Received SABM%s', 'E' if extended else '')
        if extended:
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
        self._init_connection(extended)

        # Set the incoming connection state, and emit a signal via the
        # station's 'connection_request' signal.
        self._set_conn_state(self.AX25PeerState.INCOMING_CONNECTION)
        self._start_incoming_connect_timer()
        self._station().connection_request.emit(peer=self)

    def _start_incoming_connect_timer(self):
        self._incoming_connect_timeout_handle = self._loop.call_later(
                self._ack_timeout, self._on_incoming_connect_timeout)

    def _stop_incoming_connect_timer(self):
        if self._incoming_connect_timeout_handle is not None:
            self._incoming_connect_timeout_handle.cancel()

        self._incoming_connect_timeout_handle = None

    def _on_incoming_connect_timeout(self):
        if self._state == self.AX25PeerState.INCOMING_CONNECTION:
            self._incoming_connect_timeout_handle = None
            self.reject()

    def _on_connect_response(self, response, **kwargs):
        # Handle the connection result.
        if response == 'ack':
            # We're in.
            self._set_conn_state(self.AX25PeerState.CONNECTED)
        else:
            # Didn't work
            self._set_conn_state(self.AX25PeerState.DISCONNECTED)

    def _negotiate(self, callback):
        """
        Undertake negotiation with the peer station.
        """
        # Sanity check, don't call this if we know the station won't take it.
        if self._protocol not in (AX25Version.UNKNOWN,
                                    AX25Version.AX25_22):
            raise RuntimeError('%s does not support negotiation' \
                    % self._protocol.value)

        handler = AX25PeerNegotiationHandler(self)
        handler.done_sig.connect(self._on_negotiate_result)
        handler.done_sig.connect(callback)

        handler._go()
        self._set_conn_state(self.AX25PeerState.NEGOTIATING)
        return

    def _on_negotiate_result(self, response, **kwargs):
        """
        Handle the negotiation response.
        """
        if response in ('frmr', 'dm'):
            # Other station did not like this.
            self._log.info('Failed XID negotiation, loading AX.25 2.0 defaults')
            self._process_xid_cop(AX25_20_DEFAULT_XID_COP)
            self._process_xid_hdlcoptfunc(AX25_20_DEFAULT_XID_HDLCOPTFUNC)
            self._process_xid_ifieldlenrx(AX25_20_DEFAULT_XID_IFIELDRX)
            self._process_xid_winszrx(AX25_20_DEFAULT_XID_WINDOWSZRX)
            self._process_xid_acktimer(AX25_20_DEFAULT_XID_ACKTIMER)
            self._process_xid_retrycounter(AX25_20_DEFAULT_XID_RETRIES)
            if self._protocol in (AX25Version.UNKNOWN,
                                        AX25Version.AX25_22):
                self._log.info('Downgrading to AX.25 2.0 due to failed XID')
                self._protocol = AX25Version.AX25_20
                self._modulo128 = False
        elif self._protocol != AX25Version.AX25_22:
            # Clearly this station understands AX.25 2.2
            self._log.info('Upgrading to AX.25 2.2 due to successful XID')
            self._protocol = AX25Version.AX25_22

        self._negotiated = True
        self._set_conn_state(self.AX25PeerState.DISCONNECTED)

    def _init_connection(self, extended):
        """
        Initialise the AX.25 connection.
        """
        if extended:
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
        self._log.info('Disconnected from peer')
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
        self._send_ua()
        self._on_disconnect()

    def _on_receive_ua(self):
        """
        Handle a Un-numbered Acknowledge from the peer
        """
        self._log.info('Received UA from peer')
        if self._uaframe_handler:
            self._uaframe_handler()

    def _on_receive_dm(self):
        """
        Handle a disconnect request from this peer.
        """
        if self._state in (self.AX25PeerState.CONNECTED,
                            self.AX25PeerState.CONNECTING):
            # Set ourselves as disconnected
            self._log.info('Received DM from peer')
            self._on_disconnect()
        elif self._dmframe_handler:
            self._dmframe_handler()
            self._dmframe_handler = None

    def _on_receive_xid(self, frame):
        """
        Handle a request to negotiate parameters.
        """
        self._log.info('Received XID from peer')
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

        # We have received an XID, AX.25 2.0 and earlier stations do not know
        # this frame, so clearly this is at least AX.25 2.2.
        if self._protocol == AX25Version.UNKNOWN:
            self._protocol = AX25Version.AX25_22

        # Don't process the contents of the frame unless FI and GI match.
        if (frame.fi == frame.FI) and (frame.gi == frame.GI):
            # Key these by PI
            params = dict([(p.pi, p) for p in frame.parameters])

            # Process the parameters in this order

            self._process_xid_cop(params.get(
                AX25XIDParameterIdentifier.ClassesOfProcedure,
                AX25_22_DEFAULT_XID_COP
            ))

            self._process_xid_hdlcoptfunc(params.get(
                AX25XIDParameterIdentifier.HDLCOptionalFunctions,
                AX25_22_DEFAULT_XID_HDLCOPTFUNC
            ))

            self._process_xid_ifieldlenrx(params.get(
                AX25XIDParameterIdentifier.IFieldLengthReceive,
                AX25_22_DEFAULT_XID_IFIELDRX
            ))

            self._process_xid_winszrx(params.get(
                AX25XIDParameterIdentifier.WindowSizeReceive,
                AX25_22_DEFAULT_XID_WINDOWSZRX
            ))

            self._process_xid_acktimer(params.get(
                AX25XIDParameterIdentifier.AcknowledgeTimer,
                AX25_22_DEFAULT_XID_ACKTIMER
            ))

            self._process_xid_retrycounter(params.get(
                AX25XIDParameterIdentifier.Retries,
                AX25_22_DEFAULT_XID_RETRIES
            ))

        if frame.header.cr:
            # Other station is requesting negotiation, send response.
            self._send_xid(cr=False)
        elif self._xidframe_handler is not None:
            # This is a reply to our XID
            self._xidframe_handler(frame)
            self._xidframe_handler = None

        # Having received the XID, we consider ourselves having negotiated
        # parameters.  Future connections will skip this step.
        self._negotiated = True

    def _process_xid_cop(self, param):
        if param.pv is None:
            # We were told to use defaults.  This is from a XID frame,
            # so assume AX.25 2.2 defaults.
            self._log.debug('XID: Assuming default Classes of Procedure')
            param = AX25_22_DEFAULT_XID_COP

        # Ensure we don't confuse ourselves if the station sets both
        # full-duplex and half-duplex bits.  Half-duplex is always a
        # safe choice in case of such confusion.
        self._full_duplex = \
                self._full_duplex \
                and param.full_duplex \
                and (not param.half_duplex)
        self._log.debug('XID: Setting full-duplex: %s', self._full_duplex)

    def _process_xid_hdlcoptfunc(self, param):
        if param.pv is None:
            # We were told to use defaults.  This is from a XID frame,
            # so assume AX.25 2.2 defaults.
            self._log.debug('XID: Assuming default HDLC Optional Features')
            param = AX25_22_DEFAULT_XID_HDLCOPTFUNC

        # Negotiable parts of this parameter are:
        # - SREJ/REJ bits
        if param.srej and param.rej:
            reject_mode = self.AX25RejectMode.SELECTIVE_RR
        elif param.srej:
            reject_mode = self.AX25RejectMode.SELECTIVE
        else:
            # Technically this means also the invalid SREJ=0 REJ=0,
            # we'll assume they meant REJ=1 in that case.
            reject_mode = self.AX25RejectMode.IMPLICIT

        # We take the option with the lowest precedence
        if self._reject_mode.precedence > reject_mode.precedence:
            self._reject_mode = reject_mode
        self._log.debug('XID: Set reject mode: %s', self._reject_mode.value)

        # - Modulo 8/128: again, unless the station positively says
        #   "I support modulo 128", use modulo 8.
        #   The remote station is meant to set either modulo128 *OR* modulo8.
        #   If we have it enabled our end, and they either have the modulo8
        #   bit set, or the modulo128 bit clear, then fail back to modulo8.
        if self._modulo128 and ((not param.modulo128) or param.modulo8):
            self._modulo128 = False
        self._log.debug('XID: Set modulo128 mode: %s', self._modulo128)

    def _process_xid_ifieldlenrx(self, param):
        if param.pv is None:
            # We were told to use defaults.  This is from a XID frame,
            # so assume AX.25 2.2 defaults.
            self._log.debug('XID: Assuming default I-Field Receive Length')
            param = AX25_22_DEFAULT_XID_IFIELDRX

        self._max_ifield = min([
            self._max_ifield,
            param.value
        ])
        self._log.debug('XID: Setting I-Field Receive Length: %d',
                self._max_ifield)

    def _process_xid_winszrx(self, param):
        if param.pv is None:
            # We were told to use defaults.  This is from a XID frame,
            # so assume AX.25 2.2 defaults.
            self._log.debug('XID: Assuming default Window Size Receive')
            param = AX25_22_DEFAULT_XID_WINDOWSZRX

        self._max_outstanding = min([
            self._max_outstanding_mod128 \
                    if self._modulo128
                    else self._max_outstanding_mod8,
            param.value
        ])
        self._log.debug('XID: Setting Window Size Receive: %d',
                self._max_outstanding)

    def _process_xid_acktimer(self, param):
        if param.pv is None:
            # We were told to use defaults.  This is from a XID frame,
            # so assume AX.25 2.2 defaults.
            self._log.debug('XID: Assuming default ACK timer')
            param = AX25_22_DEFAULT_XID_ACKTIMER

        self._ack_timeout = max([
            self._ack_timeout * 1000,
            param.value
        ]) / 1000
        self._log.debug('XID: Setting ACK timeout: %.3f sec',
                self._ack_timeout)

    def _process_xid_retrycounter(self, param):
        if param.pv is None:
            # We were told to use defaults.  This is from a XID frame,
            # so assume AX.25 2.2 defaults.
            self._log.debug('XID: Assuming default retry limit')
            param = AX25_22_DEFAULT_XID_RETRIES

        self._max_retries = max([
            self._max_retries,
            param.value
        ])
        self._log.debug('XID: Setting retry limit: %d',
                self._max_retries)

    def _send_sabm(self):
        """
        Send a SABM(E) frame to the remote station.
        """
        self._log.info('Sending SABM%s',
                'E' if self._modulo128 else '')
        SABMClass = AX25SetAsyncBalancedModeExtendedFrame \
                if self._modulo128 else AX25SetAsyncBalancedModeFrame

        self._transmit_frame(
                SABMClass(
                    destination=self.address,
                    source=self._station().address,
                    repeaters=self.reply_path
                )
        )
        self._set_conn_state(self.AX25PeerState.CONNECTING)

    def _send_xid(self, cr):
        self._transmit_frame(
                AX25ExchangeIdentificationFrame(
                    destination=self.address,
                    source=self._station().address,
                    repeaters=self.reply_path,
                    parameters=[
                        AX25XIDClassOfProceduresParameter(
                            half_duplex=not self._full_duplex,
                            full_duplex=self._full_duplex
                            ),
                        AX25XIDHDLCOptionalFunctionsParameter(
                            rej=(self._reject_mode in (
                                self.AX25RejectMode.IMPLICIT,
                                self.AX25RejectMode.SELECTIVE_RR
                                )),
                            srej=(self._reject_mode in (
                                self.AX25RejectMode.SELECTIVE,
                                self.AX25RejectMode.SELECTIVE_RR
                                )),
                            modulo8=(not self._modulo128),
                            modulo128=(self._modulo128)
                            ),
                        AX25XIDIFieldLengthTransmitParameter(
                            self._max_ifield * 8
                            ),
                        AX25XIDIFieldLengthReceiveParameter(
                            self._max_ifield_rx * 8
                            ),
                        AX25XIDWindowSizeTransmitParameter(
                            self._max_outstanding
                            ),
                        AX25XIDWindowSizeReceiveParameter(
                            self._max_outstanding_mod128 \
                                    if self._modulus128
                                    else self._max_outstanding_mod8
                                    ),
                        AX25XIDAcknowledgeTimerParameter(
                            int(self._ack_timeout * 1000)
                        ),
                        AX25XIDRetriesParameter(
                            self._max_retries
                        ),
                    ],
                    cr=cr
                )
        )

    def _send_dm(self):
        """
        Send a DM frame to the remote station.
        """
        self._log.info('Sending DM')
        self._transmit_frame(
                AX25DisconnectModeFrame(
                    destination=self.address,
                    source=self._station().address,
                    repeaters=self.reply_path
                )
        )

    def _send_disc(self):
        """
        Send a DISC frame to the remote station.
        """
        self._log.info('Sending DISC')
        self._transmit_frame(
                AX25DisconnectFrame(
                    destination=self.address,
                    source=self._station().address,
                    repeaters=self.reply_path
                )
        )

    def _send_ua(self):
        """
        Send a UA frame to the remote station.
        """
        self._log.info('Sending UA')
        self._transmit_frame(
                AX25UnnumberedAcknowledgeFrame(
                    destination=self.address,
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
                    destination=self.address,
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
                self._loop.call_later(self._rr_delay, \
                        self._send_rr_notification)

    def _send_rr_notification(self):
        """
        Send a RR notification frame
        """
        self._cancel_rr_notification()
        self._transmit_frame(
                self._RRFrameClass(
                    destination=self.address,
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
                        destination=self.address,
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
        if len(self._pending_iframes) >= self._max_outstanding:
            self._log.debug('Waiting for pending I-frames to be ACKed')
            return

        # AX.25 2.2 spec 6.4.1: "Whenever a TNC has an I frame to transmit,
        # it sends the I frame with the N(S) of the control field equal to
        # its current send state variable V(S)…"
        ns = self._send_state
        if ns not in self._pending_iframes:
            if not self._pending_data:
                # No data waiting
                self._log.debug('No data pending transmission')
                return

            # Retrieve the next pending I-frame payload and add it to the queue
            self._pending_iframes[ns] = self._pending_data.pop(0)
            self._log.debug('Creating new I-Frame %d', ns)

        # Send it
        self._log.debug('Sending new I-Frame %d', ns)
        self._transmit_iframe(ns)

        # "After the I frame is sent, the send state variable is incremented
        # by one."
        self._send_state = (self._send_state + 1) % self._modulo

    def _transmit_iframe(self, ns):
        """
        Transmit the I-frame identified by the given N(S) parameter.
        """
        (pid, payload) = self._pending_iframes[ns]
        self._transmit_frame(
                self._IFrameClass(
                    destination=self.address,
                    source=self._station().address,
                    repeaters=self.reply_path,
                    nr=self._recv_seq,
                    ns=ns,
                    pf=False,
                    pid=pid, payload=payload
                )
        )

    def _transmit_frame(self, frame, callback=None):
        # Update the last activity timestamp
        self._last_act = self._loop.time()

        # Reset the idle timer
        self._reset_idle_timeout()
        return self._station()._interface().transmit(frame, callback=None)


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
                self._timeout, self._on_timeout)

    def _stop_timer(self):
        if self._timeout_handle is None:
            return

        if not self._timeout_handle.cancelled:
            self._timeout_handle.cancel()

        self._timeout_handle = None

    def _finish(self, **kwargs):
        if self._done:
            return

        self._done = True
        self._stop_timer()
        self.done_sig.emit(**kwargs)


class AX25PeerConnectionHandler(AX25PeerHelper):
    """
    This class is used to manage the connection to the peer station.  If the
    station has not yet negotiated with the peer, this is done (unless we know
    the peer won't tolerate it), then a SABM or SABME connection is made.
    """

    def __init__(self, peer):
        super(AX25PeerConnectionHandler, self).__init__(peer,
                peer._ack_timeout)
        self._retries = peer._max_retries

    def _go(self):
        if self.peer._negotiated:
            # Already done, we can connect immediately
            self._on_negotiated(response='already')
        elif self.peer._protocol not in (
                AX25Version.AX25_22, AX25Version.UNKNOWN):
            # Not compatible, just connect
            self._on_negotiated(response='not_compatible')
        else:
            # Need to negotiate first.
            self.peer._negotiate(self._on_negotiated)

    def _on_negotiated(self, response, **kwargs):
        if response in ('xid', 'frmr', 'dm', 'already', 'retry'):
            # We successfully negotiated with this station (or it was not
            # required)
            self.peer._uaframe_handler = self._on_receive_ua
            self.peer._frmrframe_handler = self._on_receive_frmr
            self.peer._dmframe_handler = self._on_receive_dm
            self.peer._send_sabm()
            self._start_timer()
        else:
            self._finish(response=response)

    def _on_receive_ua(self):
        # Peer just acknowledged our connection
        self._finish(response='ack')

    def _on_receive_frmr(self):
        # Peer just rejected our connect frame, begin FRMR recovery.
        self.peer._send_dm()
        self._finish(response='frmr')

    def _on_receive_dm(self):
        # Peer just rejected our connect frame.
        self._finish(response='dm')

    def _on_timeout(self):
        if self._retries:
            self._retries -= 1
            self._on_negotiated(response='retry')
        else:
            self._finish(response='timeout')

    def _finish(self, **kwargs):
        # Clean up hooks
        self.peer._uaframe_handler = None
        self.peer._frmrframe_handler = None
        self.peer._dmframe_handler = None
        super(AX25PeerConnectionHandler, self)._finish(**kwargs)


class AX25PeerNegotiationHandler(AX25PeerHelper):
    """
    This class is used to manage the negotiation of link parameters with the
    peer.  Notably, if the peer is an AX.25 2.0, this loads defaults for that
    revision of AX.25 and handles the FRMR/DM condition.
    """
    def __init__(self, peer):
        super(AX25PeerNegotiationHandler, self).__init__(peer,
                peer._ack_timeout)
        self._retries = peer._max_retries

    def _go(self):
        # Specs say AX.25 2.2 should respond with XID and 2.0 should respond
        # with FRMR.  It is also possible we could get a DM as some buggy AX.25
        # implementations respond with that in reply to unknown frames.
        self.peer._xidframe_handler = self._on_receive_xid
        self.peer._frmrframe_handler = self._on_receive_frmr
        self.peer._dmframe_handler = self._on_receive_dm
        self.peer._send_xid(cr=True)
        self._start_timer()

    def _on_receive_xid(self, *args, **kwargs):
        # XID frame received, we can consider ourselves done.
        self._finish(response='xid')

    def _on_receive_frmr(self, *args, **kwargs):
        # FRMR received.  Evidently this station does not like XID.  Caller
        # will need to kiss and make up with the offended legacy station either
        # with a SABM or DM.  We can be certain this is not an AX.25 2.2 station.
        self._finish(response='frmr')

    def _on_receive_dm(self, *args, **kwargs):
        # DM received.  This is not strictly in spec, but we'll treat it as a
        # legacy AX.25 station telling us we're disconnected.  No special
        # handling needed.
        self._finish(response='dm')

    def _on_timeout(self):
        # No response received
        if self._retries:
            self._retries -= 1
            self._go()
        else:
            self._finish(response='timeout')

    def _finish(self, **kwargs):
        # Clean up hooks
        self.peer._xidframe_handler = None
        self.peer._frmrframe_handler = None
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
                cr=True
        )

        # Store the received frame here
        self._rx_frame = None

        # Time of transmission
        self._tx_time = None

        # Time of reception
        self._rx_time = None

        # Flag indicating we are done
        self._done = False

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
            raise RuntimeError('Test frame already pending')
        self.peer._testframe_handler = self
        self.peer._transmit_frame(self.tx_frame,
                callback=self._transmit_done)
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

#!/usr/bin/env python3

"""
AX.25 framing
"""

import re
import time
from collections.abc import Sequence

# Frame type classes


class AX25Frame(object):
    """
    Base class for AX.25 frames.
    """

    CONTROL_I_MASK = 0b00000001
    CONTROL_I_VAL = 0b00000000
    CONTROL_US_MASK = 0b00000011
    CONTROL_S_VAL = 0b00000001
    CONTROL_U_VAL = 0b00000011

    # PID codes
    PID_ISO8208_CCITT = 0x01
    PID_VJ_IP4_COMPRESS = 0x06
    PID_VJ_IP4 = 0x07
    PID_SEGMENTATION = 0x08
    PID_TEXNET = 0xC3
    PID_LINKQUALITY = 0xC4
    PID_APPLETALK = 0xCA
    PID_APPLETALK_ARP = 0xCB
    PID_ARPA_IP4 = 0xCC
    PID_APRA_ARP = 0xCD
    PID_FLEXNET = 0xCE
    PID_NETROM = 0xCF
    PID_NO_L3 = 0xF0
    PID_ESCAPE = 0xFF

    @classmethod
    def decode(cls, data):
        """
        Decode a single AX.25 frame from the given data.
        """
        (header, data) = AX25FrameHeader.decode(data)
        if not data:
            raise ValueError("Insufficient packet data")

        # Next should be the control field.  Control field
        # can be either 8 or 16-bits, we don't know at this point.
        # We'll look at the first 8-bits to see if it's a U-frame
        # since that has a defined bit pattern we can look for.
        control = data[0]

        if (control & cls.CONTROL_US_MASK) == cls.CONTROL_U_VAL:
            # This is a U frame.  Data starts after the control byte
            # which can only be 8-bits wide.
            return AX25UnnumberedFrame.decode(header, control, data[1:])
        else:
            # This is either a I or S frame, both of which can either
            # have a 8-bit or 16-bit control field.  We don't know at
            # this point so the only safe answer is to return a raw frame
            # and decode it later.
            return AX25RawFrame(
                destination=header.destination,
                source=header.source,
                repeaters=header.repeaters,
                cr=header.cr,
                src_cr=header.src_cr,
                payload=data,
            )

    def __init__(
        self,
        destination,
        source,
        repeaters=None,
        cr=False,
        src_cr=None,
        timestamp=None,
        deadline=None,
    ):
        self._header = AX25FrameHeader(
            destination, source, repeaters, cr, src_cr
        )
        self._timestamp = timestamp or time.time()
        self._deadline = deadline

    def _encode(self):
        """
        Generate the encoded AX.25 frame.
        """
        # Send the addressing header
        for byte in bytes(self.header):
            yield byte

        # Send the payload
        for byte in self.frame_payload:
            yield byte

    def __bytes__(self):
        """
        Encode the AX.25 frame
        """
        return bytes(self._encode())

    def __str__(self):
        return str(self._header)

    @property
    def timestamp(self):
        """
        Timestamp for message (creation time)
        """
        return self._timestamp

    @property
    def deadline(self):
        """
        Message expiry
        """
        return self._deadline

    @deadline.setter
    def deadline(self, deadline):
        if self._deadline is not None:
            raise ValueError("Deadline may not be changed after being set")
        self._deadline = deadline

    @property
    def header(self):
        return self._header

    @property
    def frame_payload(self):
        """
        Return the bytes in the frame payload (including the control bytes)
        """
        return b""

    @property
    def tnc2(self):
        """
        Return the frame in "TNC2" format.
        """
        return self.header.tnc2

    def copy(self, header=None):
        """
        Make a copy of this frame with a new header for digipeating.
        """
        clone = self._copy()
        if header is not None:
            clone._header = header
        return clone


class AX258BitFrame(AX25Frame):
    """
    Base class for AX.25 frames which have a 8-bit control field.
    """

    POLL_FINAL = 0b00010000

    # Control field bits
    #
    #  7   6   5   4   3   2   1   0
    # --------------------------------
    #     N(R)   | P |    N(S)   | 0   I Frame
    #     N(R)   |P/F| S   S | 0   1   S Frame
    #  M   M   M |P/F| M   M | 1   1   U Frame
    CONTROL_NR_MASK = 0b11100000
    CONTROL_NR_SHIFT = 5
    CONTROL_NS_MASK = 0b00001110
    CONTROL_NS_SHIFT = 1

    def __init__(
        self,
        destination,
        source,
        repeaters=None,
        cr=False,
        src_cr=None,
        timestamp=None,
        deadline=None,
    ):
        super(AX258BitFrame, self).__init__(
            destination=destination,
            source=source,
            repeaters=repeaters,
            cr=cr,
            src_cr=src_cr,
            timestamp=timestamp,
            deadline=deadline,
        )

    @property
    def control(self):
        return self._control

    @property
    def frame_payload(self):
        """
        Return the bytes in the frame payload (including the control byte)
        """
        return bytes([self.control])


class AX2516BitFrame(AX25Frame):
    """
    Base class for AX.25 frames which have a 16-bit control field.
    """

    POLL_FINAL = 0b0000000100000000

    # Control field bits.  These are sent least-significant bit first.
    # Unnumbered frames _always_ use the 8-bit control format, so here
    # we will only see I frames or S frames.
    #
    # 15  14  13  12  11  10   9   8   7   6   5   4   3   2   1   0
    # --------------------------------------------------------------
    #            N(R)            | P |            N(S)           | 0   I Frame
    #            N(R)            |P/F| 0   0   0   0 | S   S | 0   1   S Frame
    CONTROL_NR_MASK = 0b1111111000000000
    CONTROL_NR_SHIFT = 9
    CONTROL_NS_MASK = 0b0000000011111110
    CONTROL_NS_SHIFT = 1

    def __init__(
        self,
        destination,
        source,
        repeaters=None,
        cr=False,
        src_cr=None,
        timestamp=None,
        deadline=None,
    ):
        super(AX2516BitFrame, self).__init__(
            destination=destination,
            source=source,
            repeaters=repeaters,
            cr=cr,
            src_cr=src_cr,
            timestamp=timestamp,
            deadline=deadline,
        )

    @property
    def control(self):
        return self._control

    @property
    def frame_payload(self):
        """
        Return the bytes in the frame payload (including the control bytes)
        """
        # The control field is sent in LITTLE ENDIAN format so as to avoid
        # S frames possibly getting confused with U frames.
        control = self.control
        return bytes([control & 0x00FF, (control >> 8) & 0x00FF])


class AX25RawFrame(AX25Frame):
    """
    A representation of a raw AX.25 frame.
    """

    def __init__(
        self,
        destination,
        source,
        repeaters=None,
        cr=False,
        src_cr=None,
        payload=None,
    ):
        self._header = AX25FrameHeader(
            destination, source, repeaters, cr, src_cr
        )
        self._payload = payload or b""

    @property
    def frame_payload(self):
        return self._payload

    def _copy(self):
        return self.__class__(
            destination=self.header.destination,
            source=self.header.source,
            repeaters=self.header.repeaters,
            cr=self.header.cr,
            src_cr=self.header.src_cr,
            payload=self.frame_payload,
        )


class AX25UnnumberedFrame(AX258BitFrame):
    """
    A representation of an un-numbered frame.
    """

    MODIFIER_MASK = 0b11101111

    @classmethod
    def decode(cls, header, control, data):
        # Decode based on the control field
        modifier = control & cls.MODIFIER_MASK
        for subclass in (
            AX25UnnumberedInformationFrame,
            AX25FrameRejectFrame,
            AX25SetAsyncBalancedModeFrame,
            AX25SetAsyncBalancedModeExtendedFrame,
            AX25DisconnectFrame,
            AX25DisconnectModeFrame,
            AX25ExchangeIdentificationFrame,
            AX25UnnumberedAcknowledgeFrame,
            AX25TestFrame,
        ):
            if modifier == subclass.MODIFIER:
                return subclass.decode(header, control, data)

        # If we're still here, clearly this is a plain U frame.
        if data:
            raise ValueError(
                "Unnumbered frames (other than UI and "
                "FRMR) do not have payloads"
            )

        return cls(
            destination=header.destination,
            source=header.source,
            repeaters=header.repeaters,
            cr=header.cr,
            src_cr=header.src_cr,
            modifier=modifier,
            pf=bool(control & cls.POLL_FINAL),
        )

    def __init__(
        self,
        destination,
        source,
        modifier,
        repeaters=None,
        pf=False,
        cr=False,
        src_cr=None,
        timestamp=None,
        deadline=None,
    ):
        super(AX25UnnumberedFrame, self).__init__(
            destination=destination,
            source=source,
            repeaters=repeaters,
            cr=cr,
            src_cr=src_cr,
            timestamp=timestamp,
            deadline=deadline,
        )
        self._pf = bool(pf)
        self._modifier = int(modifier) & self.MODIFIER_MASK

    @property
    def _control(self):
        """
        Return the value of the control byte.
        """
        control = self._modifier
        if self._pf:
            control |= self.POLL_FINAL
        return control

    @property
    def pf(self):
        """
        Return the state of the poll/final bit
        """
        return self._pf

    @property
    def modifier(self):
        """
        Return the modifier bits
        """
        return self._modifier

    def _copy(self):
        return self.__class__(
            destination=self.header.destination,
            source=self.header.source,
            repeaters=self.header.repeaters,
            modifier=self.modifier,
            cr=self.header.cr,
            src_cr=self.header.src_cr,
            pf=self.pf,
        )


class AX25InformationFrameMixin(object):
    """
    Common code for AX.25 all information frames
    """

    @classmethod
    def decode(cls, header, control, data):
        return cls(
            destination=header.destination,
            source=header.source,
            repeaters=header.repeaters,
            cr=header.cr,
            nr=int((control & cls.CONTROL_NR_MASK) >> cls.CONTROL_NR_SHIFT),
            ns=int((control & cls.CONTROL_NS_MASK) >> cls.CONTROL_NS_SHIFT),
            pf=bool(control & cls.POLL_FINAL),
            pid=data[0],
            payload=data[1:],
        )

    def __init__(
        self,
        destination,
        source,
        pid,
        nr,
        ns,
        payload,
        repeaters=None,
        pf=False,
        cr=False,
        timestamp=None,
        deadline=None,
    ):
        super(AX25InformationFrameMixin, self).__init__(
            destination=destination,
            source=source,
            repeaters=repeaters,
            cr=cr,
            timestamp=timestamp,
            deadline=deadline,
        )
        self._nr = int(nr)
        self._pf = bool(pf)
        self._ns = int(ns)
        self._pid = int(pid) & 0xFF
        self._payload = bytes(payload)

    @property
    def pid(self):
        return self._pid

    @property
    def nr(self):
        """
        Return the receive sequence number
        """
        return self._nr

    @property
    def pf(self):
        """
        Return the state of the poll/final bit
        """
        return self._pf

    @property
    def ns(self):
        """
        Return the send sequence number
        """
        return self._ns

    @property
    def payload(self):
        return self._payload

    @property
    def frame_payload(self):
        return (
            super(AX25InformationFrameMixin, self).frame_payload
            + bytearray([self.pid])
            + self.payload
        )

    @property
    def _control(self):
        """
        Return the value of the control byte.
        """
        return (
            ((self.nr << self.CONTROL_NR_SHIFT) & self.CONTROL_NR_MASK)
            | (self.POLL_FINAL if self.pf else 0)
            | ((self.ns << self.CONTROL_NS_SHIFT) & self.CONTROL_NS_MASK)
            | self.CONTROL_I_VAL
        )

    def __str__(self):
        return "%s: N(R)=%d P/F=%s N(S)=%d PID=0x%02x Payload=%r" % (
            self.header,
            self.nr,
            self.pf,
            self.ns,
            self.pid,
            self.payload,
        )

    def _copy(self):
        return self.__class__(
            destination=self.header.destination,
            source=self.header.source,
            repeaters=self.header.repeaters,
            cr=self.header.cr,
            pf=self.pf,
            pid=self.pid,
            nr=self.nr,
            ns=self.ns,
            payload=self.payload,
        )


class AX258BitInformationFrame(AX25InformationFrameMixin, AX258BitFrame):
    """
    A representation of an information frame using modulo-8 acknowledgements.
    """

    pass


class AX2516BitInformationFrame(AX25InformationFrameMixin, AX2516BitFrame):
    """
    A representation of an information frame using modulo-128 acknowledgements.
    """

    pass


class AX25SupervisoryFrameMixin(object):
    """
    Common code for AX.25 all supervisory frames
    """

    # Supervisory field bits
    SUPER_MASK = 0b00001100

    @classmethod
    def decode(cls, header, control):
        code = int(control & cls.SUPER_MASK)
        return cls.SUBCLASSES[code](
            destination=header.destination,
            source=header.source,
            repeaters=header.repeaters,
            cr=header.cr,
            nr=int((control & cls.CONTROL_NR_MASK) >> cls.CONTROL_NR_SHIFT),
            pf=bool(control & cls.POLL_FINAL),
        )

    def __init__(
        self,
        destination,
        source,
        nr,
        repeaters=None,
        pf=False,
        cr=False,
        timestamp=None,
        deadline=None,
    ):
        super(AX25SupervisoryFrameMixin, self).__init__(
            destination=destination,
            source=source,
            repeaters=repeaters,
            cr=cr,
            timestamp=timestamp,
            deadline=deadline,
        )
        self._nr = int(nr)
        self._code = self.SUPERVISOR_CODE
        self._pf = bool(pf)

    @property
    def nr(self):
        """
        Return the receive sequence number
        """
        return self._nr

    @property
    def pf(self):
        """
        Return the state of the poll/final bit
        """
        return self._pf

    @property
    def code(self):
        """
        Return the supervisory control code
        """
        return self._code

    @property
    def _control(self):
        """
        Return the value of the control byte.
        """
        return (
            ((self.nr << self.CONTROL_NR_SHIFT) & self.CONTROL_NR_MASK)
            | (self.POLL_FINAL if self.pf else 0)
            | (self.code & self.SUPER_MASK)
            | self.CONTROL_S_VAL
        )

    def __str__(self):
        return "%s: N(R)=%d P/F=%s %s" % (
            self.header,
            self.nr,
            self.pf,
            self.__class__.__name__,
        )

    def _copy(self):
        return self.__class__(
            destination=self.header.destination,
            source=self.header.source,
            repeaters=self.header.repeaters,
            cr=self.header.cr,
            pf=self.pf,
            nr=self.nr,
        )


# The 4 types of supervisory frame


class AX25ReceiveReadyFrameMixin(AX25SupervisoryFrameMixin):
    """
    Receive Ready supervisory frame.

    This frame is sent to indicate readyness to receive more frames.
    If pf=True, this is a query being sent asking "are you ready?", otherwise
    this is a response saying "I am ready".
    """

    SUPERVISOR_CODE = 0b00000000


class AX25ReceiveNotReadyFrameMixin(AX25SupervisoryFrameMixin):
    """
    Receive Not Ready supervisory frame.

    This is the opposite to a RR frame, and indicates we are not yet ready
    to receive more traffic and that we may need to re-transmit frames when
    we're ready to receive them.
    """

    SUPERVISOR_CODE = 0b00000100


class AX25RejectFrameMixin(AX25SupervisoryFrameMixin):
    """
    Reject frame.

    This indicates the indicated frame were not received and need to be re-sent.
    All frames prior to the indicated frame are received, everything that
    follows must be re-sent.
    """

    SUPERVISOR_CODE = 0b00001000


class AX25SelectiveRejectFrameMixin(AX25SupervisoryFrameMixin):
    """
    Selective Reject frame.

    This indicates a specific frame was not received and needs to be re-sent.
    There is no requirement to send subsequent frames.
    """

    SUPERVISOR_CODE = 0b00001100


# 8 and 16-bit variants of the above 4 types


class AX258BitReceiveReadyFrame(AX25ReceiveReadyFrameMixin, AX258BitFrame):
    pass


class AX2516BitReceiveReadyFrame(AX25ReceiveReadyFrameMixin, AX2516BitFrame):
    pass


class AX258BitReceiveNotReadyFrame(
    AX25ReceiveNotReadyFrameMixin, AX258BitFrame
):
    pass


class AX2516BitReceiveNotReadyFrame(
    AX25ReceiveNotReadyFrameMixin, AX2516BitFrame
):
    pass


class AX258BitRejectFrame(AX25RejectFrameMixin, AX258BitFrame):
    pass


class AX2516BitRejectFrame(AX25RejectFrameMixin, AX2516BitFrame):
    pass


class AX258BitSelectiveRejectFrame(
    AX25SelectiveRejectFrameMixin, AX258BitFrame
):
    pass


class AX2516BitSelectiveRejectFrame(
    AX25SelectiveRejectFrameMixin, AX2516BitFrame
):
    pass


# 8 and 16-bit variants of the base class


class AX258BitSupervisoryFrame(AX25SupervisoryFrameMixin, AX258BitFrame):
    SUBCLASSES = dict(
        [
            (c.SUPERVISOR_CODE, c)
            for c in (
                AX258BitReceiveReadyFrame,
                AX258BitReceiveNotReadyFrame,
                AX258BitRejectFrame,
                AX258BitSelectiveRejectFrame,
            )
        ]
    )


class AX2516BitSupervisoryFrame(AX25SupervisoryFrameMixin, AX2516BitFrame):
    SUBCLASSES = dict(
        [
            (c.SUPERVISOR_CODE, c)
            for c in (
                AX2516BitReceiveReadyFrame,
                AX2516BitReceiveNotReadyFrame,
                AX2516BitRejectFrame,
                AX2516BitSelectiveRejectFrame,
            )
        ]
    )


# Un-numbered frame types


class AX25UnnumberedInformationFrame(AX25UnnumberedFrame):
    """
    A representation of an un-numbered information frame.
    """

    MODIFIER = 0b00000011

    @classmethod
    def decode(cls, header, control, data):
        if not data:
            raise ValueError("Payload of UI must be at least one byte")
        return cls(
            destination=header.destination,
            source=header.source,
            repeaters=header.repeaters,
            cr=header.cr,
            src_cr=header.src_cr,
            pf=bool(control & cls.POLL_FINAL),
            pid=data[0],
            payload=data[1:],
        )

    def __init__(
        self,
        destination,
        source,
        pid,
        payload,
        repeaters=None,
        pf=False,
        cr=False,
        src_cr=None,
        timestamp=None,
        deadline=None,
    ):
        super(AX25UnnumberedInformationFrame, self).__init__(
            destination=destination,
            source=source,
            repeaters=repeaters,
            cr=cr,
            src_cr=src_cr,
            pf=pf,
            modifier=self.MODIFIER,
            timestamp=timestamp,
            deadline=deadline,
        )
        self._pid = int(pid) & 0xFF
        self._payload = bytes(payload)

    @property
    def pid(self):
        return self._pid

    @property
    def payload(self):
        return self._payload

    @property
    def frame_payload(self):
        return (
            super(AX25UnnumberedInformationFrame, self).frame_payload
            + bytearray([self.pid])
            + self.payload
        )

    def __str__(self):
        return "%s: PID=0x%02x Payload=%r" % (
            self.header,
            self.pid,
            self.payload,
        )

    def _copy(self):
        return self.__class__(
            destination=self.header.destination,
            source=self.header.source,
            repeaters=self.header.repeaters,
            cr=self.header.cr,
            src_cr=self.header.src_cr,
            pf=self.pf,
            pid=self.pid,
            payload=self.payload,
        )

    @property
    def tnc2(self):
        """
        Return the frame in "TNC2" format (default charset).
        """
        return self.get_tnc2()

    def get_tnc2(self, charset="latin1", errors="strict"):
        """
        Return the frame in "TNC2" format with given charset.
        """
        return "%s:%s" % (
            self.header.tnc2,
            self.payload.decode(charset, errors),
        )


class AX25FrameRejectFrame(AX25UnnumberedFrame):
    """
    A representation of a Frame Reject (FRMR) frame.

    Not much effort has been made to decode the meaning of these bits.
    """

    MODIFIER = 0b10000111
    W_MASK = 0b00000001
    X_MASK = 0b00000010
    Y_MASK = 0b00000100
    Z_MASK = 0b00001000
    VR_MASK = 0b11100000
    VR_POS = 5
    CR_MASK = 0b00010000
    VS_MASK = 0b00001110
    VS_POS = 1

    @classmethod
    def decode(cls, header, control, data):
        if len(data) != 3:
            raise ValueError("Payload of FRMR must be 3 bytes")

        # W, X, Y and Z bits
        w = bool(data[0] & cls.W_MASK)
        x = bool(data[0] & cls.X_MASK)
        y = bool(data[0] & cls.Y_MASK)
        z = bool(data[0] & cls.Z_MASK)

        # VR, CR and VS fields
        vr = (data[1] & cls.VR_MASK) >> cls.VR_POS
        cr = bool(data[1] & cls.CR_MASK)
        vs = (data[1] & cls.VS_MASK) >> cls.VS_POS

        # Control field of rejected frame
        frmr_control = data[2]

        return cls(
            destination=header.destination,
            source=header.source,
            repeaters=header.repeaters,
            cr=header.cr,
            src_cr=header.src_cr,
            pf=bool(control & cls.POLL_FINAL),
            w=w,
            x=x,
            y=y,
            z=z,
            vr=vr,
            frmr_cr=cr,
            vs=vs,
            frmr_control=frmr_control,
        )

    def __init__(
        self,
        destination,
        source,
        w,
        x,
        y,
        z,
        vr,
        frmr_cr,
        vs,
        frmr_control,
        repeaters=None,
        pf=False,
        cr=False,
        src_cr=None,
    ):
        super(AX25FrameRejectFrame, self).__init__(
            destination=destination,
            source=source,
            repeaters=repeaters,
            cr=cr,
            src_cr=src_cr,
            pf=pf,
            modifier=self.MODIFIER,
        )

        self._w = bool(w)
        self._x = bool(x)
        self._y = bool(y)
        self._z = bool(z)
        self._frmr_cr = bool(frmr_cr)
        self._frmr_control = int(frmr_control)
        self._vr = int(vr)
        self._vs = int(vs)

    @property
    def frame_payload(self):
        return super(AX25FrameRejectFrame, self).frame_payload + bytes(
            self._gen_frame_payload()
        )

    def _gen_frame_payload(self):
        wxyz = 0
        if self._w:
            wxyz |= self.W_MASK
        if self._x:
            wxyz |= self.X_MASK
        if self._y:
            wxyz |= self.Y_MASK
        if self._z:
            wxyz |= self.Z_MASK
        yield wxyz

        vrcrvs = 0
        vrcrvs |= (self._vr << self.VR_POS) & self.VR_MASK
        if self._frmr_cr:
            vrcrvs |= self.CR_MASK
        vrcrvs |= (self._vs << self.VS_POS) & self.VS_MASK
        yield vrcrvs

        yield self._frmr_control

    @property
    def w(self):
        return self._w

    @property
    def x(self):
        return self._x

    @property
    def y(self):
        return self._y

    @property
    def z(self):
        return self._z

    @property
    def vs(self):
        return self._vs

    @property
    def vr(self):
        return self._vr

    @property
    def frmr_cr(self):
        return self._frmr_cr

    @property
    def frmr_control(self):
        return self._frmr_control

    def _copy(self):
        return self.__class__(
            destination=self.header.destination,
            source=self.header.source,
            repeaters=self.header.repeaters,
            w=self.w,
            x=self.x,
            y=self.y,
            z=self.z,
            frmr_cr=self.frmr_cr,
            vr=self.vr,
            vs=self.vs,
            frmr_control=self.frmr_control,
            cr=self.header.cr,
            src_cr=self.header.src_cr,
            pf=self.pf,
        )


class AX25BaseUnnumberedFrame(AX25UnnumberedFrame):
    """
    Base unnumbered frame sub-class.  This is used to provide a common
    decode and _copy implementation for basic forms of UI frames without
    information fields.
    """

    @classmethod
    def decode(cls, header, control, data):
        if len(data):
            raise ValueError("Frame does not support payload")

        return cls(
            destination=header.destination,
            source=header.source,
            repeaters=header.repeaters,
            pf=bool(control & cls.POLL_FINAL),
            cr=header.cr,
        )

    def __init__(
        self,
        destination,
        source,
        repeaters=None,
        pf=False,
        cr=False,
        timestamp=None,
        deadline=None,
    ):
        super(AX25BaseUnnumberedFrame, self).__init__(
            destination=destination,
            source=source,
            modifier=self.MODIFIER,
            repeaters=repeaters,
            cr=cr,
            timestamp=timestamp,
            deadline=deadline,
        )

    def _copy(self):
        return self.__class__(
            destination=self.header.destination,
            source=self.header.source,
            repeaters=self.header.repeaters,
            cr=self.header.cr,
            pf=self.pf,
        )


class AX25SetAsyncBalancedModeFrame(AX25BaseUnnumberedFrame):
    """
    Set Async Balanced Mode (modulo 8).

    This frame is used to initiate a connection request with the destination
    AX.25 node.
    """

    MODIFIER = 0b01101111


class AX25SetAsyncBalancedModeExtendedFrame(AX25BaseUnnumberedFrame):
    """
    Set Async Balanced Mode Extended (modulo 128).

    This frame is used to initiate a connection request with the destination
    AX.25 node, using modulo 128 acknowledgements.
    """

    MODIFIER = 0b00101111


class AX25DisconnectFrame(AX25BaseUnnumberedFrame):
    """
    Disconnect frame.

    This frame is used to initiate a disconnection from the other station.
    """

    MODIFIER = 0b01000011


class AX25DisconnectModeFrame(AX25BaseUnnumberedFrame):
    """
    Disconnect mode frame.

    This frame is used to indicate to the other station that it is disconnected.
    """

    MODIFIER = 0b00001111


class AX25ExchangeIdentificationFrame(AX25UnnumberedFrame):
    """
    Exchange Identification frame.

    This frame is used to negotiate TNC features.
    """

    MODIFIER = 0b10101111

    @classmethod
    def decode(cls, header, control, data):
        return cls(
            destination=header.destination,
            source=header.source,
            repeaters=header.repeaters,
            payload=data,
            pf=bool(control & cls.POLL_FINAL),
            cr=header.cr,
        )

    def __init__(
        self,
        destination,
        source,
        payload,
        repeaters=None,
        pf=False,
        cr=False,
        timestamp=None,
        deadline=None,
    ):
        super(AX25ExchangeIdentificationFrame, self).__init__(
            destination=destination,
            source=source,
            repeaters=repeaters,
            cr=cr,
            pf=pf,
            modifier=self.MODIFIER,
            timestamp=timestamp,
            deadline=deadline,
        )
        self._payload = bytes(payload)

    @property
    def payload(self):
        return self._payload

    def _copy(self):
        return self.__class__(
            destination=self.header.destination,
            source=self.header.source,
            payload=self.payload,
            repeaters=self.header.repeaters,
            cr=self.header.cr,
            pf=self.pf,
        )


class AX25UnnumberedAcknowledgeFrame(AX25BaseUnnumberedFrame):
    """
    Unnumbered Acknowledge frame.

    This frame is used to acknowledge a SABM/SABME frame.
    """

    MODIFIER = 0b10101111


class AX25TestFrame(AX25UnnumberedFrame):
    """
    Test frame.

    This frame is used to initiate an echo request.
    """

    MODIFIER = 0b11100011

    @classmethod
    def decode(cls, header, control, data):
        return cls(
            destination=header.destination,
            source=header.source,
            repeaters=header.repeaters,
            payload=data,
            pf=bool(control & cls.POLL_FINAL),
            cr=header.cr,
        )

    def __init__(
        self,
        destination,
        source,
        payload,
        repeaters=None,
        pf=False,
        cr=False,
        timestamp=None,
        deadline=None,
    ):
        super(AX25TestFrame, self).__init__(
            destination=destination,
            source=source,
            repeaters=repeaters,
            cr=cr,
            pf=pf,
            modifier=self.MODIFIER,
            timestamp=timestamp,
            deadline=deadline,
        )
        self._payload = bytes(payload)

    @property
    def payload(self):
        return self._payload

    def _copy(self):
        return self.__class__(
            destination=self.header.destination,
            source=self.header.source,
            payload=self.payload,
            repeaters=self.header.repeaters,
            cr=self.header.cr,
            pf=self.pf,
        )


# Helper classes


class AX25FrameHeader(object):
    """
    A representation of an AX.25 frame header.
    """

    @classmethod
    def decode(cls, data):
        """
        Decode a frame header from the data given, return the
        decoded header and the data remaining.
        """
        # Decode the addresses
        addresses = []
        while data and (not (addresses and addresses[-1].extension)):
            addresses.append(AX25Address.decode(data))
            data = data[7:]

        # Whatever's left is the frame payload data.
        if len(addresses) < 2:
            raise ValueError("Too few addresses")

        return (
            cls(
                destination=addresses[0],
                source=addresses[1],
                repeaters=addresses[2:],
                cr=addresses[0].ch,
                src_cr=addresses[1].ch,
            ),
            data,
        )

    def __init__(
        self, destination, source, repeaters=None, cr=False, src_cr=None
    ):
        self._cr = bool(cr)
        self._src_cr = src_cr
        self._destination = AX25Address.decode(destination)
        self._source = AX25Address.decode(source)
        self._repeaters = AX25Path(*(repeaters or []))

    def _encode(self):
        """
        Generate an encoded AX.25 frame header
        """
        # Extension bit should be 0
        # CH bit should be 1 for command, 0 for response
        self._destination.extension = False
        self._destination.ch = self.cr
        for byte in bytes(self._destination):
            yield byte

        # Extension bit should be 0 if digipeaters follow, 1 otherwise
        # CH bit should be 0 for command, 1 for response
        self._source.extension = not bool(self._repeaters)
        self._source.ch = self.src_cr
        for byte in bytes(self._source):
            yield byte

        # Digipeaters
        if self._repeaters:
            # Very last should have extension = 1, others extension 0.
            # Leave the CH bits untouched.
            for rpt in self._repeaters[:-1]:
                rpt.extension = False
            self._repeaters[-1].extension = True

            for rpt in self._repeaters:
                for byte in bytes(rpt):
                    yield byte

    def __str__(self):
        """
        Dump the frame header in human-readable form.
        """
        return "%s>%s%s" % (
            self._source,
            self._destination,
            (",%s" % self._repeaters) if self._repeaters else "",
        )

    def __bytes__(self):
        """
        Encode the AX.25 frame header
        """
        return bytes(self._encode())

    @property
    def destination(self):
        return self._destination

    @property
    def source(self):
        return self._source

    @property
    def repeaters(self):
        return self._repeaters

    @property
    def cr(self):
        """
        Command/Response bit in the destination address.
        """
        return self._cr

    @property
    def src_cr(self):
        """
        Command/Response bit in the source address.
        """
        if self._src_cr is None:
            return not self.cr
        else:
            return self._src_cr

    @property
    def tnc2(self):
        """
        Return the frame header in "TNC2" format.

        Largely the same as the format given by str(), but we ignore
        the C bits on the source and destination call-signs.
        """
        # XXX "TNC2 format" is largely undefined… unless someone feels like
        # deciphering the TAPR TNC2's firmware source code. (hello Z80 assembly!)
        return "%s>%s%s" % (
            self._source.copy(ch=False),
            self._destination.copy(ch=False),
            (",%s" % self._repeaters) if self._repeaters else "",
        )


class AX25Path(Sequence):
    """
    A representation of a digipeater path.
    """

    def __init__(self, *path):
        """
        Construct a path using the given path.
        """
        self._path = tuple([AX25Address.decode(digi) for digi in path])

    def __len__(self):
        """
        Return the path length
        """
        return len(self._path)

    def __getitem__(self, index):
        """
        Return the Nth path element.
        """
        return self._path[index]

    def __str__(self):
        """
        Return a string representation of the digipeater path.
        """
        return ",".join(str(addr) for addr in self._path)

    def __repr__(self):
        """
        Return the Python representation of the digipeater path.
        """
        return "%s(%s)" % (
            self.__class__.__name__,
            ", ".join([repr(addr) for addr in self._path]),
        )

    @property
    def reply(self):
        """
        Return the reply path (the "consumed" digipeaters in reverse order).
        """
        return self.__class__(
            *tuple(
                [
                    digi.copy(ch=False)
                    for digi in filter(
                        lambda digi: digi.ch, reversed(self._path)
                    )
                ]
            )
        )

    def replace(self, alias, address):
        """
        Replace an address alias (e.g. WIDE1-1) with the given address
        (e.g. the address of this station).
        """
        alias = AX25Address.decode(alias).normalised
        address = AX25Address.decode(address)
        return self.__class__(
            *tuple(
                [
                    address if (digi.normalised == alias) else digi
                    for digi in self._path
                ]
            )
        )


class AX25Address(object):
    """
    A representation of an AX.25 address (callsign + SSID)
    """

    CALL_RE = re.compile(r"^([0-9A-Z]+)(?:-([0-9]{1,2}))?(\*?)$")

    @classmethod
    def decode(cls, data):
        """
        Decode an AX.25 address from a frame.
        """
        if isinstance(data, (bytes, bytearray)):
            # Ensure the data is at least 7 bytes!
            if len(data) < 7:
                raise ValueError("AX.25 addresses must be 7 bytes!")

            # This is a binary representation in the AX.25 frame header
            callsign = (
                bytes([b >> 1 for b in data[0:6]]).decode("US-ASCII").strip()
            )
            ssid = (data[6] & 0b00011110) >> 1
            ch = bool(data[6] & 0b10000000)
            res1 = bool(data[6] & 0b01000000)
            res0 = bool(data[6] & 0b00100000)
            extension = bool(data[6] & 0b00000001)
            return cls(callsign, ssid, ch, res0, res1, extension)
        elif isinstance(data, str):
            # This is a human-readable representation
            match = cls.CALL_RE.match(data.upper())
            if not match:
                raise ValueError("Not a valid SSID: %s" % data)
            return cls(
                callsign=match.group(1),
                ssid=int(match.group(2) or 0),
                ch=match.group(3) == "*",
            )
        elif isinstance(data, AX25Address):
            # Clone factory
            return data.copy()
        else:
            raise TypeError("Don't know how to decode %r" % data)

    def __init__(
        self,
        callsign,
        ssid=0,
        ch=False,
        res0=True,
        res1=True,
        extension=False,
    ):
        self._callsign = str(callsign).upper()
        self._ssid = int(ssid) & 0b00001111
        self._ch = bool(ch)
        self._res0 = bool(res0)
        self._res1 = bool(res1)
        self._extension = bool(extension)

    def _encode(self):
        """
        Generate the encoded AX.25 address.
        """
        for byte in self._callsign[0:6].ljust(6).encode("US-ASCII"):
            yield (byte << 1)

        # SSID byte
        ssid = self._ssid << 1
        if self._extension:
            ssid |= 0b00000001
        if self._res0:
            ssid |= 0b00100000
        if self._res1:
            ssid |= 0b01000000
        if self._ch:
            ssid |= 0b10000000
        yield ssid

    def __bytes__(self):
        """
        Return the encoded call-sign.
        """
        return bytes(self._encode())

    def __str__(self):
        """
        Return the call-sign and SSID as a string.
        """
        address = self.callsign
        if self.ssid > 0:
            address += "-%d" % self.ssid

        if self.ch:
            address += "*"
        return address

    def __repr__(self):
        """
        Return the Python representation of this object.
        """
        return (
            "%s(callsign=%s, ssid=%d, ch=%r, res0=%r, "
            "res1=%r, extension=%r)"
        ) % (
            self.__class__.__name__,
            self.callsign,
            self.ssid,
            self.ch,
            self.res0,
            self.res1,
            self.extension,
        )

    def __eq__(self, other):
        if not isinstance(other, AX25Address):
            return NotImplemented

        for field in ("callsign", "ssid", "extension", "res0", "res1", "ch"):
            if getattr(self, field) != getattr(other, field):
                return False

        return True

    def __hash__(self):
        return hash(
            tuple(
                [
                    getattr(self, field)
                    for field in (
                        "callsign",
                        "ssid",
                        "extension",
                        "res0",
                        "res1",
                        "ch",
                    )
                ]
            )
        )

    @property
    def callsign(self):
        """
        The call-sign of the station being referenced.
        """
        return self._callsign

    @property
    def ssid(self):
        """
        Secondary Station Identifier.
        """
        return self._ssid

    @property
    def extension(self):
        """
        Extension bit, used in digipeater SSID lists to indicate
        that this address is the last AX.25 digipeater address in the list.

        AX.25 2.0 doc § 2.2.13.3
        """
        return self._extension

    @extension.setter
    def extension(self, value):
        self._extension = bool(value)

    @property
    def res0(self):
        """
        Reserved bit 0 in the AX.25 address field.
        """
        return self._res0

    @property
    def res1(self):
        """
        Reserved bit 1 in the AX.25 address field.
        """
        return self._res1

    @property
    def ch(self):
        """
        C/H bit.

        In repeater call-signs, this is the H bit, and indicative of a frame
        that "has been repeated" by that digipeater (AX.25 2.0 doc § 2.2.13.3).

        In source/destination call-signs, this is the C bit, and indicative
        of a "command" (AX.25 2.0 doc § 2.4.1.2).
        """
        return self._ch

    @ch.setter
    def ch(self, value):
        self._ch = bool(value)

    def copy(self, **overrides):
        """
        Return a copy of this address, optionally with fields overridden.
        """
        mydata = dict(
            callsign=self.callsign,
            ssid=self.ssid,
            ch=self.ch,
            res0=self.res0,
            res1=self.res1,
            extension=self.extension,
        )
        mydata.update(overrides)
        return self.__class__(**mydata)

    @property
    def normalised(self):
        """
        Return a normalised copy of this address.  (Set reserved bits to ones,
        clear the CH bit and extension bit.)
        """
        return self.copy(res0=True, res1=True, ch=False, extension=False)

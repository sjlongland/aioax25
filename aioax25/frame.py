#!/usr/bin/env python3

"""
AX.25 framing.  This module defines encoders and decoders for all frame types
used in version 2.2 of the AX.25 standard.

AX25Frame is the base class, and provides an abstract interface for interacting
with all frame types.  AX.25 identifies the specific type of frame from bits in
the control field which can be 8 or 16-bits wide.

The only way to know if it's 16-bits is in witnessing the initial connection
being made between two stations which means it's impossible for a stateless
decoder to fully decode an arbitrary AX.25 frame.

Thankfully the control field is sent little-endian format, so the first byte we
encounter is the least significant bits -- which is sufficient to identify whether
the frame is an I, S or U frame: the least significant two bits carry this
information.

For this reason there are 3 sub-classes of this top-level class:

    - AX25RawFrame: This is used when we only need to decode the initial AX.25
      addressing header to know whether we need to worry about the frame
      further.

    - AX258BitFrame: This is used for AX.25 frames with an 8-bit control field,
      which is anything sent by an AX.25 v2.0 station, any un-numbered frame,
      or any I or S frame where modulo-8 frame numbering is used.

    - AX2516BitFrame: This is used for AX.25 v2.2 stations where modulo-128
      frame numbering has been negotiated by both parties.

Decoding is done by calling the AX25Frame.decode class method.  This takes two
parameters:

    - data: either raw bytes or an AX25Frame class.  The latter form is useful when
      you've previously decoded a frame as a AX25RawFrame and need to further
      dissect it as either a AX258BitFrame or AX2516BitFrame sub-class.

    - modulo128: by default is None, but if set to a boolean, will decode I or S
      frames accordingly instead of just returning AX25RawFrame.
"""

import re
import time
import enum
from collections.abc import Sequence

from . import uint

# Frame type classes


class AX25Frame(object):
    """
    Base class for AX.25 frames.
    """

    # The following are the same for 8 and 16-bit control fields.
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
    def decode(cls, data, modulo128=None):
        """
        Decode a single AX.25 frame from the given data.
        """
        if isinstance(data, AX25Frame):
            # We were given a previously decoded frame.
            header = data.header
            data = data.frame_payload
        else:
            # We were given raw data.
            (header, data) = AX25FrameHeader.decode(bytes(data))

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
            # have a 8-bit or 16-bit control field.
            if modulo128 is True:
                # And the caller has told us it's a 16-bit field, so let's
                # decode the rest of it!
                if len(data) < 2:
                    raise ValueError("Insufficient packet data")
                control |= data[1] << 8

                # Discard the control field from the data payload as we
                # have decoded it now.
                data = data[2:]

                # We'll use these classes
                InformationFrame = AX2516BitInformationFrame
                SupervisoryFrame = AX2516BitSupervisoryFrame
            elif modulo128 is False:
                # Caller has told us it's an 8-bit field, so already decoded.
                data = data[1:]

                # We'll use these classes
                InformationFrame = AX258BitInformationFrame
                SupervisoryFrame = AX258BitSupervisoryFrame
            else:
                # We don't know at this point so the only safe answer is to
                # return a raw frame and decode it later.
                return AX25RawFrame(
                    destination=header.destination,
                    source=header.source,
                    repeaters=header.repeaters,
                    cr=header.cr,
                    src_cr=header.src_cr,
                    payload=data,
                )

            # We've got the full control field and payload now.
            if (control & cls.CONTROL_I_MASK) == cls.CONTROL_I_VAL:
                # This is an I frame.
                return InformationFrame.decode(header, control, data)
            elif (control & cls.CONTROL_US_MASK) == cls.CONTROL_S_VAL:
                # This is a S frame.  No payload expected
                if len(data):
                    raise ValueError(
                        "Supervisory frames do not " "support payloads."
                    )
                return SupervisoryFrame.decode(header, control)
            else:  # pragma: no cover
                assert False, "Unrecognised control field: 0x%04x" % control

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
    def frame_payload(self):  # pragma: no cover
        """
        Return the bytes in the frame payload (including the control bytes)
        """
        raise NotImplementedError("To be implemented in sub-class")

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
        return uint.encode(self.control, big_endian=False, length=2)


class AX25RawFrame(AX25Frame):
    """
    A representation of a raw AX.25 frame.  This class is intended to capture
    partially decoded frame data in the case where we don't know whether a control
    field is 8 or 16-bits wide.

    It may be fed to the AX25Frame.decode function again with modulo128=False for
    known 8-bit frames, or modulo128=True for known 16-bit frames.  For digipeating
    applications, often no further dissection is necessary and so the frame can be
    used as-is.
    """

    def __init__(
        self,
        destination,
        source,
        repeaters=None,
        cr=False,
        src_cr=None,
        payload=None,
        timestamp=None,
        deadline=None,
    ):
        super(AX25RawFrame, self).__init__(
            destination=destination,
            source=source,
            repeaters=repeaters,
            cr=cr,
            src_cr=src_cr,
            timestamp=timestamp,
            deadline=deadline,
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
    A representation of an un-numbered frame.  U frames are used for all
    sorts of in-band signalling as well as for connectionless data transfer
    via UI frames (see AX25UnnumberedInformationFrame).

    All U frames have an 8-bit control field.
    """

    MODIFIER_MASK = 0b11101111

    SUBCLASSES = {}

    @classmethod
    def register(cls, subclass):
        """
        Register a sub-class of UnnumberedFrame with the decoder.
        """
        assert (
            subclass.MODIFIER not in cls.SUBCLASSES
        ), "Duplicate registration"
        cls.SUBCLASSES[subclass.MODIFIER] = subclass

    @classmethod
    def decode(cls, header, control, data):
        """
        Decode an unnumbered frame which has been partially decoded by
        AX25Frame.decode.  This inspects the value of the modifier bits
        in the control field (see AX.25 2.2 spec 4.3.3) and passes the
        arguments given to the appropriate sub-class.
        """

        # Decode based on the control field
        modifier = control & cls.MODIFIER_MASK
        subclass = cls.SUBCLASSES.get(modifier, None)
        if subclass is not None:
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


AX25UnnumberedFrame.register(AX25UnnumberedInformationFrame)


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


AX25UnnumberedFrame.register(AX25FrameRejectFrame)


class AX25BaseUnnumberedFrame(AX25UnnumberedFrame):
    """
    Base unnumbered frame sub-class.  This is used to provide a common
    decode and _copy implementation for basic forms of UI frames without
    information fields.
    """

    # Defaults for PF, CR fields
    PF = False
    CR = False

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
        pf=None,
        cr=None,
        timestamp=None,
        deadline=None,
    ):
        if pf is None:
            pf = self.PF
        if cr is None:
            cr = self.CR

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
    CR = True


AX25UnnumberedFrame.register(AX25SetAsyncBalancedModeFrame)


class AX25SetAsyncBalancedModeExtendedFrame(AX25BaseUnnumberedFrame):
    """
    Set Async Balanced Mode Extended (modulo 128).

    This frame is used to initiate a connection request with the destination
    AX.25 node, using modulo 128 acknowledgements.
    """

    MODIFIER = 0b00101111
    CR = True


AX25UnnumberedFrame.register(AX25SetAsyncBalancedModeExtendedFrame)


class AX25DisconnectFrame(AX25BaseUnnumberedFrame):
    """
    Disconnect frame.

    This frame is used to initiate a disconnection from the other station.
    """

    MODIFIER = 0b01000011
    CR = True


AX25UnnumberedFrame.register(AX25DisconnectFrame)


class AX25DisconnectModeFrame(AX25BaseUnnumberedFrame):
    """
    Disconnect mode frame.

    This frame is used to indicate to the other station that it is disconnected.
    """

    MODIFIER = 0b00001111
    CR = False


AX25UnnumberedFrame.register(AX25DisconnectModeFrame)


class AX25XIDParameterIdentifier(enum.Enum):
    """
    Known values of PI in XID frames.
    """

    # Negotiates half/full duplex operation
    ClassesOfProcedure = 2

    # Selects between REJ, SREJ or both
    HDLCOptionalFunctions = 3

    # Sets the outgoing I field length in bits (not bytes)
    IFieldLengthTransmit = 5

    # Sets the incoming I field length in bits (not bytes)
    IFieldLengthReceive = 6

    # Sets the outgoing number of outstanding I-frames (k)
    WindowSizeTransmit = 7

    # Sets the incoming number of outstanding I-frames (k)
    WindowSizeReceive = 8

    # Sets the duration of the Wait For Acknowledge (T1) timer
    AcknowledgeTimer = 9

    # Sets the retry count (N1)
    Retries = 10

    def __int__(self):
        """
        Return the value of the PI.
        """
        return self.value


class AX25XIDParameter(object):
    """
    Representation of a single XID parameter.
    """

    PARAMETERS = {}

    @classmethod
    def register(cls, subclass):
        """
        Register a sub-class of XID parameter.
        """
        assert subclass.PI not in cls.PARAMETERS
        cls.PARAMETERS[subclass.PI] = subclass

    @classmethod
    def decode(cls, data):
        """
        Decode the parameter value given, return the parameter and the
        remaining data.
        """
        if len(data) < 2:
            raise ValueError("Insufficient data for parameter")

        pi = data[0]
        pl = data[1]
        data = data[2:]

        if pl > 0:
            if len(data) < pl:
                raise ValueError("Parameter is truncated")
            pv = data[0:pl]
            data = data[pl:]
        else:
            pv = None

        try:
            # Hand to the sub-class to decode
            param = cls.PARAMETERS[AX25XIDParameterIdentifier(pi)].decode(pv)
        except (KeyError, ValueError):
            # Not recognised, so return a base class
            param = AX25XIDRawParameter(pi=pi, pv=pv)

        return (param, data)

    def __init__(self, pi):
        """
        Create a new XID parameter
        """
        try:
            pi = AX25XIDParameterIdentifier(pi)
        except ValueError:
            # Pass through the PI as given.
            pass

        self._pi = pi

    @property
    def pi(self):
        """
        Return the Parameter Identifier
        """
        return self._pi

    @property
    def pv(self):  # pragma: no cover
        """
        Return the Parameter Value
        """
        raise NotImplementedError(
            "To be implemented in %s" % self.__class__.__name__
        )

    def __bytes__(self):
        """
        Return the encoded parameter value.
        """
        pv = self.pv
        param = bytes([int(self.pi)])

        if pv is None:
            param += bytes([0])
        else:
            param += bytes([len(pv)]) + pv

        return param

    def copy(self):  # pragma: no cover
        """
        Return a copy of this parameter.
        """
        raise NotImplementedError(
            "To be implemented in %s" % self.__class__.__name__
        )


class AX25XIDRawParameter(AX25XIDParameter):
    """
    Representation of a single XID parameter that we don't recognise.
    """

    def __init__(self, pi, pv):
        """
        Create a new XID parameter
        """
        if pv is not None:
            pv = bytes(pv)
        self._pv = pv
        super(AX25XIDRawParameter, self).__init__(pi=pi)

    @property
    def pv(self):
        """
        Return the Parameter Value
        """
        return self._pv

    def copy(self):
        """
        Return a copy of this parameter.
        """
        return self.__class__(pi=self.pi, pv=self.pv)


class AX25XIDClassOfProceduresParameter(AX25XIDParameter):
    """
    Class of Procedures XID parameter.  This parameter is used to negotiate
    half or full duplex communications between two TNCs.
    """

    PI = AX25XIDParameterIdentifier.ClassesOfProcedure

    # Bit fields for this parameter:
    BALANCED_ABM = 0b0000000000000001  # Should be 1
    UNBALANCED_NRM_PRI = 0b0000000000000010  # Should be 0
    UNBALANCED_NRM_SEC = 0b0000000000000100  # Should be 0
    UNBALANCED_ARM_PRI = 0b0000000000001000  # Should be 0
    UNBALANCED_ARM_SEC = 0b0000000000010000  # Should be 0
    HALF_DUPLEX = 0b0000000000100000  # Should oppose FULL_DUPLEX
    FULL_DUPLEX = 0b0000000001000000  # Should oppose HALF_DUPLEX
    RESERVED_MASK = 0b1111111110000000  # Should be all zeros
    RESERVED_POS = 7

    @classmethod
    def decode(cls, pv):
        # Decode the PV
        pv = uint.decode(pv, big_endian=False)
        return cls(
            full_duplex=bool(pv & cls.FULL_DUPLEX),
            half_duplex=bool(pv & cls.HALF_DUPLEX),
            unbalanced_nrm_pri=bool(pv & cls.UNBALANCED_NRM_PRI),
            unbalanced_nrm_sec=bool(pv & cls.UNBALANCED_NRM_SEC),
            unbalanced_arm_pri=bool(pv & cls.UNBALANCED_ARM_PRI),
            unbalanced_arm_sec=bool(pv & cls.UNBALANCED_ARM_SEC),
            balanced_abm=bool(pv & cls.BALANCED_ABM),
            reserved=((pv & cls.RESERVED_MASK) >> cls.RESERVED_POS),
        )

    def __init__(
        self,
        full_duplex=False,
        half_duplex=False,
        unbalanced_nrm_pri=False,
        unbalanced_nrm_sec=False,
        unbalanced_arm_pri=False,
        unbalanced_arm_sec=False,
        balanced_abm=True,
        reserved=0,
    ):
        """
        Create a Class Of Procedures XID parameter.  The defaults are set
        so that at most, only half_duplex or full_duplex should need setting.
        """
        self._half_duplex = half_duplex
        self._full_duplex = full_duplex
        self._unbalanced_nrm_pri = unbalanced_nrm_pri
        self._unbalanced_nrm_sec = unbalanced_nrm_sec
        self._unbalanced_arm_pri = unbalanced_arm_pri
        self._unbalanced_arm_sec = unbalanced_arm_sec
        self._balanced_abm = balanced_abm
        self._reserved = reserved
        super(AX25XIDClassOfProceduresParameter, self).__init__(pi=self.PI)

    @property
    def pv(self):
        # We reproduce all bits as given, even if the combination is invalid
        # Value is encoded in little-endian format as two bytes.
        return uint.encode(
            (
                ((self.reserved << self.RESERVED_POS) & self.RESERVED_MASK)
                | ((self.full_duplex and self.FULL_DUPLEX) or 0)
                | ((self.half_duplex and self.HALF_DUPLEX) or 0)
                | ((self.unbalanced_nrm_pri and self.UNBALANCED_NRM_PRI) or 0)
                | ((self.unbalanced_nrm_sec and self.UNBALANCED_NRM_SEC) or 0)
                | ((self.unbalanced_arm_pri and self.UNBALANCED_ARM_PRI) or 0)
                | ((self.unbalanced_arm_sec and self.UNBALANCED_ARM_SEC) or 0)
                | ((self.balanced_abm and self.BALANCED_ABM) or 0)
            ),
            big_endian=False,
            length=2,
        )

    @property
    def half_duplex(self):
        return self._half_duplex

    @property
    def full_duplex(self):
        return self._full_duplex

    @property
    def unbalanced_nrm_pri(self):
        return self._unbalanced_nrm_pri

    @property
    def unbalanced_nrm_sec(self):
        return self._unbalanced_nrm_sec

    @property
    def unbalanced_arm_pri(self):
        return self._unbalanced_arm_pri

    @property
    def unbalanced_arm_sec(self):
        return self._unbalanced_arm_sec

    @property
    def balanced_abm(self):
        return self._balanced_abm

    @property
    def reserved(self):
        return self._reserved

    def copy(self):
        return self.__class__(
            half_duplex=self.half_duplex,
            full_duplex=self.full_duplex,
            unbalanced_nrm_pri=self.unbalanced_nrm_pri,
            unbalanced_nrm_sec=self.unbalanced_nrm_sec,
            unbalanced_arm_pri=self.unbalanced_arm_pri,
            unbalanced_arm_sec=self.unbalanced_arm_sec,
            reserved=self.reserved,
        )


AX25XIDParameter.register(AX25XIDClassOfProceduresParameter)


class AX25XIDHDLCOptionalFunctionsParameter(AX25XIDParameter):
    """
    HDLC Optional Functions XID parameter.  This parameter is used to negotiate
    what optional features of the HDLC specification will be used to
    synchronise communications.
    """

    PI = AX25XIDParameterIdentifier.HDLCOptionalFunctions

    # Bit fields for this parameter:
    RESERVED1 = 0b000000000000000000000001  # Should be 0
    REJ = 0b000000000000000000000010  # Negotiable
    SREJ = 0b000000000000000000000100  # Negotiable
    UI = 0b000000000000000000001000  # Should be 0
    SIM_RIM = 0b000000000000000000010000  # Should be 0
    UP = 0b000000000000000000100000  # Should be 0
    BASIC_ADDR = 0b000000000000000001000000  # Should be 1
    EXTD_ADDR = 0b000000000000000010000000  # Should be 0
    DELETE_I_RESP = 0b000000000000000100000000  # Should be 0
    DELETE_I_CMD = 0b000000000000001000000000  # Should be 0
    MODULO8 = 0b000000000000010000000000  # Negotiable
    MODULO128 = 0b000000000000100000000000  # Negotiable
    RSET = 0b000000000001000000000000  # Should be 0
    TEST = 0b000000000010000000000000  # Should be 1
    RD = 0b000000000100000000000000  # Should be 0
    FCS16 = 0b000000001000000000000000  # Should be 1
    FCS32 = 0b000000010000000000000000  # Should be 0
    SYNC_TX = 0b000000100000000000000000  # Should be 1
    START_STOP_TX = 0b000001000000000000000000  # Should be 0
    START_STOP_FLOW_CTL = 0b000010000000000000000000  # Should be 0
    START_STOP_TRANSP = 0b000100000000000000000000  # Should be 0
    SREJ_MULTIFRAME = 0b001000000000000000000000  # Should be 0
    RESERVED2_MASK = 0b110000000000000000000000  # Should be 00
    RESERVED2_POS = 22

    @classmethod
    def decode(cls, pv):
        # Decode the PV
        pv = uint.decode(pv, big_endian=False)
        return cls(
            modulo128=pv & cls.MODULO128,
            modulo8=pv & cls.MODULO8,
            srej=pv & cls.SREJ,
            rej=pv & cls.REJ,
            srej_multiframe=pv & cls.SREJ_MULTIFRAME,
            start_stop_transp=pv & cls.START_STOP_TRANSP,
            start_stop_flow_ctl=pv & cls.START_STOP_FLOW_CTL,
            start_stop_tx=pv & cls.START_STOP_TX,
            sync_tx=pv & cls.SYNC_TX,
            fcs32=pv & cls.FCS32,
            fcs16=pv & cls.FCS16,
            rd=pv & cls.RD,
            test=pv & cls.TEST,
            rset=pv & cls.RSET,
            delete_i_cmd=pv & cls.DELETE_I_CMD,
            delete_i_resp=pv & cls.DELETE_I_RESP,
            extd_addr=pv & cls.EXTD_ADDR,
            basic_addr=pv & cls.BASIC_ADDR,
            up=pv & cls.UP,
            sim_rim=pv & cls.SIM_RIM,
            ui=pv & cls.UI,
            reserved2=(pv & cls.RESERVED2_MASK) >> cls.RESERVED2_POS,
            reserved1=pv & cls.RESERVED1,
        )

    def __init__(
        self,
        modulo128=False,
        modulo8=False,
        srej=False,
        rej=False,
        srej_multiframe=False,
        start_stop_transp=False,
        start_stop_flow_ctl=False,
        start_stop_tx=False,
        sync_tx=True,
        fcs32=False,
        fcs16=True,
        rd=False,
        test=True,
        rset=False,
        delete_i_cmd=False,
        delete_i_resp=False,
        extd_addr=True,
        basic_addr=False,
        up=False,
        sim_rim=False,
        ui=False,
        reserved2=0,
        reserved1=False,
    ):
        """
        HDLC Optional Features XID parameter.  The defaults are set
        so that at most, only srej, rej, modulo8 and/or modulo128 need setting.
        """
        self._modulo128 = modulo128
        self._modulo8 = modulo8
        self._srej = srej
        self._rej = rej
        self._srej_multiframe = srej_multiframe
        self._start_stop_transp = start_stop_transp
        self._start_stop_flow_ctl = start_stop_flow_ctl
        self._start_stop_tx = start_stop_tx
        self._sync_tx = sync_tx
        self._fcs32 = fcs32
        self._fcs16 = fcs16
        self._rd = rd
        self._test = test
        self._rset = rset
        self._delete_i_cmd = delete_i_cmd
        self._delete_i_resp = delete_i_resp
        self._extd_addr = extd_addr
        self._basic_addr = basic_addr
        self._up = up
        self._sim_rim = sim_rim
        self._ui = ui
        self._reserved2 = reserved2
        self._reserved1 = reserved1

        super(AX25XIDHDLCOptionalFunctionsParameter, self).__init__(
            pi=self.PI
        )

    @property
    def pv(self):
        # We reproduce all bits as given, even if the combination is invalid
        return uint.encode(
            (
                ((self.reserved2 << self.RESERVED2_POS) & self.RESERVED2_MASK)
                | ((self.modulo128 and self.MODULO128) or 0)
                | ((self.modulo8 and self.MODULO8) or 0)
                | ((self.srej and self.SREJ) or 0)
                | ((self.rej and self.REJ) or 0)
                | ((self.srej_multiframe and self.SREJ_MULTIFRAME) or 0)
                | ((self.start_stop_transp and self.START_STOP_TRANSP) or 0)
                | (
                    (self.start_stop_flow_ctl and self.START_STOP_FLOW_CTL)
                    or 0
                )
                | ((self.start_stop_tx and self.START_STOP_TX) or 0)
                | ((self.sync_tx and self.SYNC_TX) or 0)
                | ((self.fcs32 and self.FCS32) or 0)
                | ((self.fcs16 and self.FCS16) or 0)
                | ((self.rd and self.RD) or 0)
                | ((self.test and self.TEST) or 0)
                | ((self.rset and self.RSET) or 0)
                | ((self.delete_i_cmd and self.DELETE_I_CMD) or 0)
                | ((self.delete_i_resp and self.DELETE_I_RESP) or 0)
                | ((self.extd_addr and self.EXTD_ADDR) or 0)
                | ((self.basic_addr and self.BASIC_ADDR) or 0)
                | ((self.up and self.UP) or 0)
                | ((self.sim_rim and self.SIM_RIM) or 0)
                | ((self.ui and self.UI) or 0)
                | ((self.reserved1 and self.RESERVED1) or 0)
            ),
            big_endian=False,
            length=3,
        )

    @property
    def modulo128(self):
        return self._modulo128

    @property
    def modulo8(self):
        return self._modulo8

    @property
    def srej(self):
        return self._srej

    @property
    def rej(self):
        return self._rej

    @property
    def srej_multiframe(self):
        return self._srej_multiframe

    @property
    def start_stop_transp(self):
        return self._start_stop_transp

    @property
    def start_stop_flow_ctl(self):
        return self._start_stop_flow_ctl

    @property
    def start_stop_tx(self):
        return self._start_stop_tx

    @property
    def sync_tx(self):
        return self._sync_tx

    @property
    def fcs32(self):
        return self._fcs32

    @property
    def fcs16(self):
        return self._fcs16

    @property
    def rd(self):
        return self._rd

    @property
    def test(self):
        return self._test

    @property
    def rset(self):
        return self._rset

    @property
    def delete_i_cmd(self):
        return self._delete_i_cmd

    @property
    def delete_i_resp(self):
        return self._delete_i_resp

    @property
    def extd_addr(self):
        return self._extd_addr

    @property
    def basic_addr(self):
        return self._basic_addr

    @property
    def up(self):
        return self._up

    @property
    def sim_rim(self):
        return self._sim_rim

    @property
    def ui(self):
        return self._ui

    @property
    def reserved2(self):
        return self._reserved2

    @property
    def reserved1(self):
        return self._reserved1

    def copy(self):
        return self.__class__(
            modulo128=self.modulo128,
            modulo8=self.modulo8,
            srej=self.srej,
            rej=self.rej,
            srej_multiframe=self.srej_multiframe,
            start_stop_transp=self.start_stop_transp,
            start_stop_flow_ctl=self.start_stop_flow_ctl,
            start_stop_tx=self.start_stop_tx,
            sync_tx=self.sync_tx,
            fcs32=self.fcs32,
            fcs16=self.fcs16,
            rd=self.rd,
            test=self.test,
            rset=self.rset,
            delete_i_cmd=self.delete_i_cmd,
            delete_i_resp=self.delete_i_resp,
            extd_addr=self.extd_addr,
            basic_addr=self.basic_addr,
            up=self.up,
            sim_rim=self.sim_rim,
            ui=self.ui,
            reserved2=self.reserved2,
            reserved1=self.reserved1,
        )


AX25XIDParameter.register(AX25XIDHDLCOptionalFunctionsParameter)


class AX25XIDBigEndianParameter(AX25XIDParameter):
    """
    Base class for all big-endian parameters (field lengths, window sizes, ACK
    timers, retries).
    """

    LENGTH = None

    @classmethod
    def decode(cls, pv):
        return cls(value=uint.decode(pv, big_endian=True))

    def __init__(self, value):
        """
        Create a big-endian integer parameter.
        """
        self._value = value

        super(AX25XIDHDLCOptionalFunctionsParameter, self).__init__(
            pi=self.PI
        )

    @property
    def pv(self):
        return uint.encode(self.value, big_endian=True, length=self.LENGTH)

    @property
    def value(self):
        return self._value

    def copy(self):
        return self.__class__(value=self.value)


class AX25XIDIFieldLengthTransmitParameter(AX25XIDBigEndianParameter):
    PI = AX25XIDParameterIdentifier.IFieldLengthTransmit


class AX25XIDIFieldLengthReceiveParameter(AX25XIDBigEndianParameter):
    PI = AX25XIDParameterIdentifier.WindowSizeReceive


class AX25XIDWindowSizeTransmitParameter(AX25XIDBigEndianParameter):
    PI = AX25XIDParameterIdentifier.IFieldLengthTransmit
    LENGTH = 1


class AX25XIDWindowSizeReceiveParameter(AX25XIDBigEndianParameter):
    PI = AX25XIDParameterIdentifier.WindowSizeReceive
    LENGTH = 1


class AX25XIDAcknowledgeTimerParameter(AX25XIDBigEndianParameter):
    PI = AX25XIDParameterIdentifier.AcknowledgeTimer


class AX25XIDRetriesParameter(AX25XIDBigEndianParameter):
    PI = AX25XIDParameterIdentifier.Retries


class AX25ExchangeIdentificationFrame(AX25UnnumberedFrame):
    """
    Exchange Identification frame.

    This frame is used to negotiate TNC features.
    """

    MODIFIER = 0b10101111

    @classmethod
    def decode(cls, header, control, data):
        if len(data) < 4:
            raise ValueError("Truncated XID header")

        fi = data[0]
        gi = data[1]
        # Yep, GL is big-endian, just for a change!
        gl = uint.decode(data[2:4], big_endian=True)
        data = data[4:]

        if len(data) != gl:
            raise ValueError("Truncated XID data")

        parameters = []
        while data:
            (param, data) = AX25XIDParameter.decode(data)
            parameters.append(param)

        return cls(
            destination=header.destination,
            source=header.source,
            repeaters=header.repeaters,
            fi=fi,
            gi=gi,
            parameters=parameters,
            pf=bool(control & cls.POLL_FINAL),
            cr=header.cr,
        )

    def __init__(
        self,
        destination,
        source,
        fi,
        gi,
        parameters,
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
        self._fi = int(fi)
        self._gi = int(gi)
        self._parameters = list(parameters)

    @property
    def fi(self):
        return self._fi

    @property
    def gi(self):
        return self._gi

    @property
    def parameters(self):
        return self._parameters

    @property
    def frame_payload(self):
        parameters = b"".join([bytes(param) for param in self.parameters])
        return (
            super(AX25ExchangeIdentificationFrame, self).frame_payload
            + bytes([self.fi, self.gi])
            + uint.encode(len(parameters), length=2, big_endian=True)
            + parameters
        )

    def _copy(self):
        return self.__class__(
            destination=self.header.destination,
            source=self.header.source,
            fi=self.fi,
            gi=self.gi,
            parameters=[p.copy() for p in self.parameters],
            repeaters=self.header.repeaters,
            cr=self.header.cr,
            pf=self.pf,
        )


AX25UnnumberedFrame.register(AX25ExchangeIdentificationFrame)


class AX25UnnumberedAcknowledgeFrame(AX25BaseUnnumberedFrame):
    """
    Unnumbered Acknowledge frame.

    This frame is used to acknowledge a SABM/SABME frame.
    """

    MODIFIER = 0b01100011
    CR = False


AX25UnnumberedFrame.register(AX25UnnumberedAcknowledgeFrame)


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

    @property
    def frame_payload(self):
        return super(AX25TestFrame, self).frame_payload + bytes(self.payload)

    def _copy(self):
        return self.__class__(
            destination=self.header.destination,
            source=self.header.source,
            payload=self.payload,
            repeaters=self.header.repeaters,
            cr=self.header.cr,
            pf=self.pf,
        )


AX25UnnumberedFrame.register(AX25TestFrame)

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
                # Legacy AX.25 1.x stations set the C bits identically
                legacy=addresses[0].ch is addresses[1].ch,
            ),
            data,
        )

    def __init__(
        self,
        destination,
        source,
        repeaters=None,
        cr=False,
        src_cr=None,
        legacy=False,
    ):
        self._cr = bool(cr)
        self._src_cr = src_cr
        self._legacy = bool(legacy)
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
            if self.legacy:
                return self.cr  # AX.25 1.x: the C/R bits are identical
            else:
                return not self.cr  # AX.25 2.x: the C/R bits are opposite
        else:
            # We were given an explicit value.
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

    @property
    def legacy(self):
        return self._legacy


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
    def decode(cls, data, ssid=None):
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

            if ssid is None:
                ssid = int(match.group(2) or 0)

            return cls(
                callsign=match.group(1), ssid=ssid, ch=match.group(3) == "*"
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

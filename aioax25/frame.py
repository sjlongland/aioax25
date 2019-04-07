#!/usr/bin/env python3

"""
AX.25 framing
"""

from struct import Struct
from crcmod.predefined import mkCrcFun

# Frame-check sequence generation
gen_fcs = mkCrcFun('x-25')

# Frame-check sequence structure
FCS_STRUCT = Struct('>H')


# Frame type classes

class AX25Frame(object):
    """
    Base class for AX.25 frames.
    """

    POLL_FINAL  = 0b00010000

    CONTROL_I_MASK  = 0b00000001
    CONTROL_I_VAL   = 0b00000000
    CONTROL_US_MASK = 0b00000011
    CONTROL_S_VAL   = 0b00000001
    CONTROL_U_VAL   = 0b00000011

    @classmethod
    def decode(cls, data):
        """
        Decode a single AX.25 frame from the given data.
        """
        (header, data) = AX25FrameHeader.decode(data)
        if not data:
            raise ValueError('Insufficient packet data')

        # Next should be the control field
        control = data[0]
        data = data[1:]

        if (control & cls.CONTROL_I_MASK) == cls.CONTROL_I_VAL:
            # This is an I frame - TODO
            #return AX25InformationFrame.decode(header, control, data)
            return AX25RawFrame(
                    destination=header.destination,
                    source=header.source,
                    repeaters=header.repeaters,
                    cr=header.cr,
                    payload=data
            )
        elif (control & cls.CONTROL_US_MASK) == cls.CONTROL_S_VAL:
            # This is a S frame - TODO
            #return AX25SupervisoryFrame.decode(header, control, data)
            return AX25RawFrame(
                    destination=header.destination,
                    source=header.source,
                    repeaters=header.repeaters,
                    cr=header.cr,
                    payload=data
            )
        elif (control & cls.CONTROL_US_MASK) == cls.CONTROL_U_VAL:
            # This is a U frame
            return AX25UnnumberedFrame.decode(header, control, data)
        else:
            raise ValueError('Unrecognised frame control field: 0x%02x' \
                    % control)

    def __init__(self, destination, source, repeaters=None, cr=False):
        self._header = AX25FrameHeader(destination, source, repeaters, cr)

    def _encode(self):
        """
        Generate the encoded AX.25 frame, minus the frame-check sequence.
        """
        # Send the addressing header
        for byte in self.header:
            yield byte

        # Send the control byte
        yield self._control

    def __bytes__(self):
        """
        Encode the AX.25 frame
        """
        frame_data = bytes(self._encode())
        # Compute FCS
        fcs = FCS_STRUCT.pack(gen_fcs(frame_data))
        # Append
        return frame_data + fcs

    def __str__(self):
        return str(self._header)

    @property
    def header(self):
        return self._header

    @property
    def frame_payload(self):
        """
        Return the bytes in the frame payload (following the control byte)
        """
        return b''


class AX25RawFrame(AX25Frame):
    """
    A representation of a raw AX.25 frame.
    """

    def __init__(self, destination, source, repeaters=None,
            cr=False, payload=None):
        self._header = AX25FrameHeader(destination, source, repeaters, cr)
        self._payload = payload or b''

    def _encode(self):
        # Send the header
        for byte in super(AX25RawFrame, self)._encode():
            yield byte

        # Send the payload
        for byte in self._payload:
            yield byte

    @property
    def payload(self):
        return self._payload


class AX25UnnumberedFrame(AX25Frame):
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
                AX25FrameRejectFrame
        ):
            if modifier == subclass.MODIFIER:
                return subclass.decode(header, control, data)

        # If we're still here, clearly this is a plain U frame.
        if data:
            raise ValueError('Unnumbered frames (other than UI and '\
                            'FRMR) do not have payloads')

        return cls(
                destination=header.destination,
                source=header.source,
                repeaters=header.repeaters,
                cr=header.cr,
                modifier=modifier,
                pf=bool(control & cls.POLL_FINAL)
        )

    def __init__(self, destination, source, modifier,
            repeaters=None, pf=False, cr=False):
        super(AX25UnnumberedFrame, self).__init__(
                destination=destination, source=source,
                repeaters=repeaters, cr=cr)
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


class AX25UnnumberedInformationFrame(AX25UnnumberedFrame):
    """
    A representation of an un-numbered information frame.
    """
    MODIFIER = 0b00000011

    @classmethod
    def decode(cls, header, control, data):
        if not data:
            raise ValueError('Payload of UI must be at least one byte')
        return cls(
                destination=header.destination,
                source=header.source,
                repeaters=header.repeaters,
                cr=header.cr,
                pf=bool(control & cls.POLL_FINAL),
                pid=data[0],
                payload=data[1:]
        )

    def __init__(self, destination, source, pid, payload,
            repeaters=None, pf=False, cr=False):
        super(AX25UnnumberedInformationFrame, self).__init__(
                destination=destination, source=source,
                repeaters=repeaters, cr=cr, pf=pf,
                modifier=self.MODIFIER)
        self._pid = int(pid) & 0xff
        self._payload = bytes(payload)

    def _encode(self):
        for byte in super(AX25UnnumberedInformationFrame, self)._encode():
            yield byte

        yield self._pid

        for byte in self._payload:
            yield byte

    @property
    def pid(self):
        return self._pid

    @property
    def payload(self):
        return self._payload

    def __str__(self):
        return '%s: PID=0x%02x Payload=%r' % (
                self.header,
                self.pid,
                self.payload)


class AX25FrameRejectFrame(AX25UnnumberedFrame):
    """
    A representation of a Frame Reject (FRMR) frame.

    Not much effort has been made to decode the meaning of these bits.
    """

    MODIFIER = 0b00000011
    W_MASK   = 0b00000001
    X_MASK   = 0b00000010
    Y_MASK   = 0b00000100
    Z_MASK   = 0b00001000
    VR_MASK  = 0b11100000
    VR_POS   = 5
    CR_MASK  = 0b00010000
    VS_MASK  = 0b00001110
    VS_POS   = 1


    @classmethod
    def decode(cls, header, control, data):
        if len(data) != 3:
            raise ValueError('Payload of FRMR must be 3 bytes')

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
                pf=bool(control & cls.POLL_FINAL),
                w=w, x=x, y=y, z=z,
                vr=vr, frmr_cr=cr, vs=vs,
                frmr_control=frmr_control
        )

    def __init__(self, destination, source, w, x, y, z,
            vr, frmr_cr, vs, frmr_control,
            repeaters=None, pf=False, cr=False):
        super(AX25FrameRejectFrame, self).__init__(
                destination=destination, source=source,
                repeaters=repeaters, cr=cr, pf=pf,
                modifier=self.MODIFIER)

        self._w = bool(w)
        self._x = bool(x)
        self._y = bool(y)
        self._z = bool(z)
        self._frmr_cr = bool(frmr_cr)
        self._frmr_control = int(frmr_control)
        self._vr = int(vr)
        self._vs = int(vs)

    def _encode(self):
        for byte in super(AX25FrameRejectFrame, self)._encode():
            yield byte

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
            raise ValueError('Too few addresses')

        return (cls(
            destination=addresses[0],
            source=addresses[1],
            repeaters=addresses[2:],
            cr=addresses[0].ch
        ), data)

    def __init__(self, destination, source, repeaters=None,
            cr=False):
        self._cr = bool(cr)
        self._destination = destination
        self._source = source
        self._repeaters = repeaters or None

    def _encode(self):
        """
        Generate an encoded AX.25 frame header
        """
        # Extension bit should be 0
        # CH bit should be 1 for command, 0 for response
        self._destination.extension = False
        self._destination.ch = self._cr
        for byte in self._destination:
            yield byte

        # Extension bit should be 0 if digipeaters follow, 1 otherwise
        # CH bit should be 0 for command, 1 for response
        self._source.extension = bool(self._repeaters)
        self._source.ch = not self._cr
        for byte in self._source:
            yield byte

        # Digipeaters
        if self._repeaters:
            # Very last should have extension = 1, others extension 0.
            # Leave the CH bits untouched.
            for rpt in self._repeaters[:-1]:
                rpt.extension = False
            self._repeaters[-1].extension = True

            for rpt in self._repeaters:
                for byte in rpt:
                    yield byte

    def __str__(self):
        """
        Dump the frame header in human-readable form.
        """
        return '%s>%s%s' % (
                self._source,
                self._destination,
                ' v %s' % ','.join([
                    str(r)
                    for r in (self._repeaters or [])
                ])
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
        return self._cr


class AX25Address(object):
    """
    A representation of an AX.25 address (callsign + SSID)
    """
    @classmethod
    def decode(cls, data):
        """
        Decode an AX.25 address from a frame.
        """
        callsign = bytes([
            b >> 1
            for b in data[0:6]
        ]).decode('US-ASCII').strip()
        ssid        = (data[7]          & 0b00011110) >> 1
        ch          = bool(data[7]      & 0b10000000)
        res1        = bool(data[7]      & 0b01000000)
        res0        = bool(data[7]      & 0b00100000)
        extension   = bool(data[7]      & 0b00000001)
        return cls(callsign, ssid, ch, res0, res1, extension)

    def __init__(self, callsign, ssid=0,
            ch=False, res0=False, res1=False, extension=False):
        self._callsign  = str(callsign).upper()
        self._ssid      = int(ssid) & 0b00001111
        self._ch        = bool(ch)
        self._res0      = bool(res0)
        self._res1      = bool(res1)
        self._extension = bool(extension)

    def _encode(self):
        """
        Generate the encoded AX.25 address.
        """
        for byte in self._callsign[0:6].ljust(6).encode('US-ASCII'):
            yield byte << 1

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
        address = ''
        if self.ch:
            address += '*'

        address += self.callsign
        if self.ssid > 0:
            address += '-%d' % self.ssid
        return address

    @property
    def callsign(self):
        return self._callsign

    @property
    def ssid(self):
        return self._ssid

    @property
    def extension(self):
        return self._extension

    @extension.setter
    def extension(self, value):
        self._extension = bool(value)

    @property
    def res0(self):
        return self._res0

    @property
    def res1(self):
        return self._res1

    @property
    def ch(self):
        return self._ch

    @ch.setter
    def ch(self, value):
        self._ch = bool(value)

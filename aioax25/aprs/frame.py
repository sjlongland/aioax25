#!/usr/bin/env python3

"""
APRS framing.
"""

from ..frame import AX25UnnumberedInformationFrame
from .datatype import APRSDataType


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

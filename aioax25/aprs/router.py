#!/usr/bin/env python3

"""
APRS messaging router.
"""

from .message import APRSMessageFrame
from ..router import Router


class APRSRouter(Router):
    """
    Route a APRS message frame according to the addressee field, if any.
    """
    def _get_destination(self, frame):
        if isinstance(frame, APRSMessageFrame):
            return frame.addressee
        else:
            return super(APRSRouter, self)._get_destination(frame)

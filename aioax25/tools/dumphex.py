#!/usr/bin/env python3

"""
Very crude AX.25 KISS packet dump dissector.

This code takes the KISS traffic seen through `socat -x` (so it could be a
real serial port, a virtual one on a VM, or network sockets), and dumps the
traffic it saw to the output.

Usage:
    python3 -m aioax25.tools.dumphex <socat-dump> > <dissected>
"""

from aioax25.kiss import BaseKISSDevice, KISSDeviceState, KISSCmdData
from aioax25.frame import AX25Frame
from binascii import a2b_hex
from argparse import ArgumentParser
import logging
import asyncio
import re


SOCAT_HEX_RE = re.compile(r"^ [0-9a-f]{2}[0-9a-f ]*\n*$")
NON_HEX_RE = re.compile(r"[^0-9a-f]")


class FileKISSDevice(BaseKISSDevice):
    def __init__(self, filename, **kwargs):
        super(FileKISSDevice, self).__init__(**kwargs)
        self._filename = filename
        self._read_finished = False
        self._frames = []
        self._future = asyncio.Future()

    async def dump(self):
        self.open()
        await self._future
        self.close()
        return self._frames

    def _open(self):
        with open(self._filename, "r") as f:
            self._log.info("Reading frames from %r", self._filename)
            self._state = KISSDeviceState.OPEN
            for line in f:
                match = SOCAT_HEX_RE.match(line)
                if match:
                    self._log.debug("Parsing %r", line)
                    self._receive(a2b_hex(NON_HEX_RE.sub("", line)))
                else:
                    self._log.debug("Ignoring %r", line)

            self._log.info("Read %r", self._filename)
            self._read_finished = True

    def _receive_frame(self):
        super(FileKISSDevice, self)._receive_frame()

        if not self._read_finished:
            return

        if self._future.done():
            return

        if len(self._rx_buffer) < 2:
            self._log.info("Buffer is now empty")
            self._future.set_result(None)

    def _send_raw_data(self, data):
        pass

    def _dispatch_rx_frame(self, frame):
        self._frames.append(frame)

    def _close(self):
        self._state = KISSDeviceState.CLOSED


async def main():
    ap = ArgumentParser()
    ap.add_argument("hexfile", nargs="+")

    args = ap.parse_args()

    logging.basicConfig(level=logging.DEBUG)

    for filename in args.hexfile:
        kissdev = FileKISSDevice(filename)
        frames = await kissdev.dump()

        for frame in frames:
            print(frame)
            if isinstance(frame, KISSCmdData):
                axframe = AX25Frame.decode(frame.payload, modulo128=False)
                print(axframe)


if __name__ == "__main__":
    asyncio.run(main())

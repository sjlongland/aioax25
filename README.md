# `aioax25`: AX.25 and APRS library in `asyncio`

[![Build Status](https://travis-ci.org/sjlongland/aioax25.svg?branch=master)](https://travis-ci.org/sjlongland/aioax25)
[![Coverage Status](https://coveralls.io/repos/github/sjlongland/aioax25/badge.svg?branch=master)](https://coveralls.io/github/sjlongland/aioax25?branch=master)

The aim of this project is to implement a simple-to-understand asynchronous
AX.25 library built on `asyncio` and `pyserial`, implementing a AX.25 and APRS
stack in pure Python.

## What works

* We can put a Kantronics KPC-3 TNC into KISS mode automatically
* Multi-port KISS TNCs (tested with
  [Direwolf](https://github.com/wb2osz/direwolf))
* We can receive AX.25 UI frames
* We can send AX.25 UI frames

## What doesn't work

* Connecting to AX.25 nodes
* Accepting connections from AX.25 nodes

## What isn't tested

* Platforms other than GNU/Linux

## Current plans

Right now, I intend to get enough going for APRS operation, as that is my
immediate need now.  Hence the focus on UI frames.

I intend to write a core class that will take care of some core AX.25 message
handling work and provide the basis of what's needed to implement APRS.

After that, some things I'd like to tackle in no particular order:

* Connected mode operation
* NET/ROM support

Supported platforms will be GNU/Linux, and possibly BSD variants.  I don't
have access to recent Apple hardware (my 2008-era MacBook will not run
contemporary MacOS X) so I'm unable to test this software there, but it
_should_ work nonetheless.

It might work on Windows -- most probably using Cygwin or Subsystem for Linux.
While I do have a Windows 7 machine handy, life's too short to muck around
with an OS that can't decide if it's pretending to be Linux, VMS or CP/M.
There's an abundance of AX.25 stacks and tools for that platform, I'll accept
patches here on the proviso they don't break things or make the code
unmaintainable.

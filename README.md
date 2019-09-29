# `aioax25`: AX.25 and APRS library in `asyncio`

[![Build Status](https://travis-ci.org/sjlongland/aioax25.svg?branch=master)](https://travis-ci.org/sjlongland/aioax25)
[![Coverage Status](https://coveralls.io/repos/github/sjlongland/aioax25/badge.svg?branch=master)](https://coveralls.io/github/sjlongland/aioax25?branch=master)

The aim of this project is to implement a simple-to-understand asynchronous
AX.25 library built on `asyncio` and `pyserial`, implementing a AX.25 and APRS
stack in pure Python.

## What works

* We can put a Kantronics KPC-3 TNC into KISS mode automatically
* Multi-port KISS TNCs (tested with
  [Direwolf](https://github.com/wb2osz/direwolf) and the
  [NWDR UDRC-II](https://nw-digital-radio.groups.io/g/udrc/wiki/home))
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

## Usage

This is a rough guide regarding how to use `aioax25` in your programs.

### Create a KISS device interface and ports

Right now we only support serial KISS interfaces (patches for TCP-based
interfaces are welcome).  Import `SerialKISSDevice` from `aioax25.kiss`, then
create an instance as shown:

```python
    kissdev = SerialKISSDevice(
        device='/dev/ttyS4', baudrate=9600,
        log=logging.getLogger('your.kiss.log')
    )
```

Some optional parameters:
 * `reset_on_close`: When asked to close the device, try to issue a `c0 ff c0`
   reset sequence to the TNC to put it back into CMD mode.
 * `send_block_size`, `send_block_delay`: If a KISS frame is larger than
   this size, break the transmissions out the serial port into chunks of
   the given size, and wait `send_block_delay` seconds between each chunk.
   (If your TNC has a small buffer, this may help.)

This represents the KISS TNC itself, with its ports accessible using the usual
`__getitem__` syntax:

```python
    kissport0 = kissdev[0]
    kissport1 = kissdev[1]
```

These KISS port interfaces just spit out the content of raw AX.25 frames via
their `received` signals and accept raw AX.25 frames via the `send` method.
Any object passed to `send` is wrapped in a `bytes` call -- this will
implicitly call the `__bytes__` method on the object you pass in.

### Setting up an AX.25 Interface

The AX.25 interface is a logical routing and queueing layer which decodes the
data received from a KISS port and routes it according to the destination
call-sign.

`AX25Interface` is found in the `aioax25.interface` package.  Import that, then
do the following to set up your interface:

```python
   ax25int = AX25Interface(
       kissport=kissdev[0],     # or whatever port number you need
       log=logging.getLogger('your.ax25.log')
   )
```

Some optional parameters:
 * `cts_delay`, `cts_rand`: The number of seconds to wait after making a
   transmission/receiving a transmission, before we send another transmission.
   The delay time is `cts_delay + (random.random() * cts_rand)`, the idea
   being to avoid doubling when two stations attempt transmission.

The `AX25Interface` is a subclass of `Router` (see `aioax25.router`), which
exposes the following methods and properties:

 * `received_msg`: This is a `Signal` object which is fired for every AX.25
   frame received.  Slots are expected to take two keyword arguments:
   `interface` (the interface that received the frame) and `frame` (the
   AX.25 frame itself).

 * `bind(callback, callsign, ssid=0, regex=False)`: This method allows you to
   bind a call-back function to receive AX.25 frames whose `destination` field
   is addressed to the call-sign and SSID specified.  The call-sign may be a
   regular expression if `regex=True`.  This will be compiled and matched
   against all incoming traffic.  Regardless of the value of `regex`, the
   `callsign` parameter _must_ be a string.

 * `unbind(callback, callsign, ssid=0, regex=False)`: This method un-binds a
   previously bound call-back method from receiving the nominated traffic.

Additionally, for transmitting frames, `AX25Interface` adds the following:

 * `transmit(frame, callback=None)`: This method allows you to transmit
   arbitrary AX.25 frames.  They are assumed to be instances of `AX25Frame`
   (from `aioax25.frame`).  The `callback`, if given, will be called once the
   frame is sent with the following keyword arguments: `interface` (the
   `AX25Interface` that sent the frame), `frame` (the frame that was sent).

 * `cancel_transmit(frame)`: This cancels a pending transmission of a frame.
   If the frame has been sent, this has no effect.

## APRS Traffic handling

The `AX25Interface` just deals in AX.25 traffic, and does not provide any
special handling of APRS UI frames.  For this, one may look at `APRSInterface`.

Import this from `aioax25.aprs`.  It too, is a subclass of `Router`, and so
`bind`, `unbind` and `received_msg` are there -- the messages received will
be instances of `APRSFrame` (see `aioax25.aprs.frame`), otherwise the behaviour
is identical.

```python
   aprsint = APRSInterface(
       ax25int=ax25int,         # Your AX25Interface object
       mycall='VK4MSL-9',       # Your call-sign and SSID
       log=logging.getLogger('your.aprs.log')
   )
```

Other optional parameters:
 * `retransmit_count`, `retransmit_timeout_base`, `retransmit_timeout_rand`,
   `retransmit_timeout_scale`: These control the timing of retransmissions
   when sending _confirmable_ APRS messages.  Before transmission, a time-out
   is computed as `timeout = retransmit_timeout_base + (random.random() *
   retransmit_timeout_rand)`, and a retry counter is initialised to
   `retransmit_count`.  On each re-transmission, the retry counter is
   decremented and the timeout is multiplied by `retransmit_timeout_scale`.
 * `aprs_destination`: This sets the destination call-sign used for APRS
   traffic.  Right now, we use the experimental call of `APZAIO` for all
   traffic except direct messages (which instead are sent directly to the
   station addressed).
 * `aprs_path` specifies the digipeater path to use when sending APRS traffic.
 * `listen_destinations` is a list of AX.25 destinations.  Behind the scenes,
   these are values passed to `Router.bind`, and thus are given as `dict`s of
   the form: `{callsign: "CALL", regex: True/False, ssid: None/int}`.
 * `listen_altnets` is an additional list of AX.25 destinations, given using
   the same scheme as `listen_destinations`.
 * `msgid_modulo` sets the modulo value used when generating a message ID.
   The default value (1000) results in a message ID that starts at 1 and wraps
   around at 999.
 * `deduplication_expiry` sets the number of seconds we store message hashes
   for de-duplication purposes.  The default is 28 seconds.

To send APRS messages, there is `send_message` and `send_response`:

 * `send_message(addressee, path=None, oneshot=False, replyack=False)`:
   This sends an APRS message to the addressed station.  If `path` is `None`,
   then the `aprs_path` is used.  If `oneshot=True`, then the message is sent
   without a message ID, no ACK/REJ is expected and no retransmissions will be
   made, the method returns `None`.  Otherwise, a `APRSMessageHandler` (from
   `aioax25.aprs.message`) is returned.
   * If `replyack` is set to `True`, then the message will advertise
     [reply-ack](http://www.aprs.org/aprs11/replyacks.txt) capability to
     the recipient.  Not all APRS implementations support this.
   * If `replyack` references an incoming message which itself has `replyack`
     set (either to `True` or to a previous message ID), then the outgoing
     message will have a reply-ack suffix appended to "ack" the given message.
   * The default of `replyack=False` disables all reply-ack capability (an
     incoming reply-ack message will still be treated as an ACK however).
 * `send_response(message, ack=True)`: This is used when you have received
   a message from another station -- passing that message to this function
   will send a `ACK` or `REJ` message to that station.

### The `APRSMessageHandler` class

The `APRSMessageHandler` class implements the APRS message retransmission
logic.  The objects have a `done` signal which is emitted upon any of the
following events:

 * Message time-out (no ACK/REJ received) (`state=HandlerState.TIMEOUT`)
 * Message was cancelled (via the `cancel()` method)
   (`state=HandlerState.CANCEL`)
 * An ACK or REJ frame was received (`state=HandlerState.SUCCESS` or
   `state=HandlerState.REJECT`)

The signal will call call-back functions with the following keyword arguments:
 * `handler`: The `APRSMessageHandler` object emitting the signal
 * `state`: The state of the `APRSMessageHandler` object.

### APRS Digipeating

`aioax25` includes a module that implements basic digipeating for APRS
including handling of the `WIDEn-N` SSIDs.  The implementation treats `WIDE`
like `TRACE`: inserting the station's own call-sign in the path (which I
believe is more compliant with the [Amateur License Conditions
Determination](https://www.legislation.gov.au/Details/F2016C00286) in that it
ensures each digipeater "identifies" itself).

The `aioax25.aprs.uidigi` module can be configured to digipeat for other
aliases such as the legacy `WIDE` and `RELAY`, or any alias of your choosing.

It is capable of handling multiple interfaces, but will repeat incoming
messages on the interface they were received from *ONLY*.  (i.e. if you connect
a 2m interface and a HF interface, it will *NOT* digipeat from HF to 2m).

Set-up is pretty simple:

```
from aioax25.aprs.uidigi import APRSDigipeater

# Given an APRSInterface class (aprsint)
# Create a digipeater instance
digipeater = APRSDigipeater()

# Connect your interface
digipeater.connect(aprsint)

# Optionally add any aliases you want handled
digipeater.addaliases('WIDE', 'GATE')
```

You're now digipeating.  The digipeater will automatically handle `WIDEn-N` and
`TRACEn-N`, and in the above example, will also digipeat for `WIDE`, `GATE`.

#### Preventing message loops on busy networks

If you have a *lot* of digipeaters in close proximity (say about 6) and there's
a lot of traffic, you can get the situation where a message queued up to be
digipeated sits in the transmit queue longer than the 28 seconds needed for
other digipeaters to "forget" the message.

This leads to a network with the memory of an elephant, it almost never forgets
a message because the digipeats come more than 30 seconds *after* the original.

The `APRSDigipeater` class constructor can take a single parameter,
`digipeater_timeout`, which sets an expiry (default of 5 seconds) on queued
digipeat messages.  If a message is not sent by the time this timeout expires,
the message is quietly dropped, preventing the memory effect.

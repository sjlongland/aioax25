# `aioax25` Change Log

`aioax25` roughly follows Semantic Versioning, although right now it's
officially in "development" and so nothing is actually locked down API-wise at
this time.  Notable changes will be mentioned here.

---

## Release 0.0.10 (2021-05-18)

[Support for TCP-based KISS sockets](https://github.com/sjlongland/aioax25/pull/7).
Many thanks to Walter for this contribution.

## Release 0.0.9 (2021-01-23)

- Fixed buggy APRS message serialisation (payload of
  `MYCALL      :message{123}None`) when reply-ACK was disabled.
- Always use fixed APRS path in replies as some digipeaters do not do AX.25
  digipeating and will therefore *NOT* digipeat a message unless they see
  `WIDEn-N` in the digipeater path.
- Test compatibility with Python 3.7 and 3.8.

## Release 0.0.8 (2019-08-29)

Add support for APRS Reply-ACK message (for compatibility with Xastir).

## Release 0.0.7 (2019-07-09)

Send KISS initialisation sequence slower to ensure the console on TNCs like the
Kantronics KPC-3 don't miss anything.

## Release 0.0.6 (2019-07-09)

Prevent APRS digipeater from digipeating old (stale) messages.

## Release 0.0.5 (2019-06-29)

Fix handling of APRS message ACK/REJ.

## Release 0.0.4 (2019-06-29)

APRS MIC-e fixes, and related bugfixes for APRS digipeater.

## Release 0.0.3 (2019-06-29)

Further APRS digipeater enhancements.

## Release 0.0.2 (2019-06-22)

Addition of APRS digipeating.

## Release 0.0.1 (2019-05-12)

Initial release of `aioax25`, publish on pypi.

#!/usr/bin/env python3

from aioax25.frame import (
    AX25Frame,
    AX25ExchangeIdentificationFrame,
    AX25XIDRawParameter,
    AX25XIDParameterIdentifier,
    AX25XIDClassOfProceduresParameter,
    AX25XIDHDLCOptionalFunctionsParameter,
    AX25XIDIFieldLengthReceiveParameter,
    AX25XIDRetriesParameter,
)

from ..hex import from_hex, hex_cmp


def test_encode_xid():
    """
    Test that we can encode a XID frame.
    """
    frame = AX25ExchangeIdentificationFrame(
        destination="VK4BWI",
        source="VK4MSL",
        cr=True,
        fi=0x82,
        gi=0x80,
        parameters=[
            # Typical parameters we'd expect to see
            AX25XIDClassOfProceduresParameter(half_duplex=True),
            AX25XIDHDLCOptionalFunctionsParameter(
                srej=True, rej=True, modulo128=True
            ),
            AX25XIDIFieldLengthReceiveParameter(1024),
            AX25XIDRetriesParameter(5),
            # Arbitrary parameters for testing
            AX25XIDRawParameter(pi=0x12, pv=bytes([0x34, 0x56])),
            AX25XIDRawParameter(pi=0x34, pv=None),
        ],
    )
    hex_cmp(
        bytes(frame),
        "ac 96 68 84 ae 92 e0"  # Destination
        "ac 96 68 9a a6 98 61"  # Source
        "af"  # Control
        "82"  # Format indicator
        "80"  # Group Ident
        "00 16"  # Group length
        # First parameter: CoP
        "02"  # Parameter ID
        "02"  # Length
        "00 21"  # Value
        # Second parameter: HDLC Optional Functions
        "03"  # Parameter ID
        "03"  # Length
        "86 a8 02"  # Value
        # Third parameter: I field receive size
        "06" "02" "04 00"
        # Fourth parameter: retries
        "0a" "01" "05"
        # Fifth parameter: custom
        "12" "02" "34 56"
        # Sixth parameter: custom, no length set
        "34" "00",
    )


def test_decode_xid():
    """
    Test that we can decode a XID frame.
    """
    frame = AX25Frame.decode(
        from_hex(
            "ac 96 68 84 ae 92 e0"  # Destination
            "ac 96 68 9a a6 98 61"  # Source
            "af"  # Control
            "82"  # FI
            "80"  # GI
            "00 0c"  # GL
            # Some parameters
            "11 01 aa"
            "12 01 bb"
            "13 02 11 22"
            "14 00"
        )
    )
    assert isinstance(frame, AX25ExchangeIdentificationFrame)
    assert frame.fi == 0x82
    assert frame.gi == 0x80
    assert len(frame.parameters) == 4

    param = frame.parameters[0]
    assert param.pi == 0x11
    assert param.pv == b"\xaa"

    param = frame.parameters[1]
    assert param.pi == 0x12
    assert param.pv == b"\xbb"

    param = frame.parameters[2]
    assert param.pi == 0x13
    assert param.pv == b"\x11\x22"

    param = frame.parameters[3]
    assert param.pi == 0x14
    assert param.pv is None


def test_decode_xid_fig46():
    """
    Test that we can decode the XID example from AX.25 2.2 figure 4.6.
    """
    frame = AX25Frame.decode(
        from_hex(
            "9c 94 6e a0 40 40 e0"  # Destination
            "9c 6e 98 8a 9a 40 61"  # Source
            "af"  # Control
            "82"  # FI
            "80"  # GI
            "00 17"  # GL
            "02 02 00 20"
            "03 03 86 a8 02"
            "06 02 04 00"
            "08 01 02"
            "09 02 10 00"
            "0a 01 03"
        )
    )
    assert len(frame.parameters) == 6

    param = frame.parameters[0]
    assert param.pi == AX25XIDParameterIdentifier.ClassesOfProcedure
    assert param.pv == b"\x00\x20"

    param = frame.parameters[1]
    assert param.pi == AX25XIDParameterIdentifier.HDLCOptionalFunctions
    assert param.pv == b"\x86\xa8\x02"

    param = frame.parameters[2]
    assert param.pi == AX25XIDParameterIdentifier.IFieldLengthReceive
    assert param.pv == b"\x04\x00"

    param = frame.parameters[3]
    assert param.pi == AX25XIDParameterIdentifier.WindowSizeReceive
    assert param.pv == b"\x02"

    param = frame.parameters[4]
    assert param.pi == AX25XIDParameterIdentifier.AcknowledgeTimer
    assert param.pv == b"\x10\x00"

    param = frame.parameters[5]
    assert param.pi == AX25XIDParameterIdentifier.Retries
    assert param.pv == b"\x03"


def test_decode_xid_truncated_header():
    """
    Test that decoding a XID with truncated header fails.
    """
    try:
        AX25Frame.decode(
            from_hex(
                "ac 96 68 84 ae 92 e0"  # Destination
                "ac 96 68 9a a6 98 61"  # Source
                "af"  # Control
                "82"  # FI
                "80"  # GI
                "00"  # Incomplete GL
            )
        )
        assert False, "This should not have worked"
    except ValueError as e:
        assert str(e) == "Truncated XID header"


def test_decode_xid_truncated_payload():
    """
    Test that decoding a XID with truncated payload fails.
    """
    try:
        AX25Frame.decode(
            from_hex(
                "ac 96 68 84 ae 92 e0"  # Destination
                "ac 96 68 9a a6 98 61"  # Source
                "af"  # Control
                "82"  # FI
                "80"  # GI
                "00 05"  # GL
                "11"  # Incomplete payload
            )
        )
        assert False, "This should not have worked"
    except ValueError as e:
        assert str(e) == "Truncated XID data"


def test_decode_xid_truncated_param_header():
    """
    Test that decoding a XID with truncated parameter header fails.
    """
    try:
        AX25Frame.decode(
            from_hex(
                "ac 96 68 84 ae 92 e0"  # Destination
                "ac 96 68 9a a6 98 61"  # Source
                "af"  # Control
                "82"  # FI
                "80"  # GI
                "00 01"  # GL
                "11"  # Incomplete payload
            )
        )
        assert False, "This should not have worked"
    except ValueError as e:
        assert str(e) == "Insufficient data for parameter"


def test_decode_xid_truncated_param_value():
    """
    Test that decoding a XID with truncated parameter value fails.
    """
    try:
        AX25Frame.decode(
            from_hex(
                "ac 96 68 84 ae 92 e0"  # Destination
                "ac 96 68 9a a6 98 61"  # Source
                "af"  # Control
                "82"  # FI
                "80"  # GI
                "00 04"  # GL
                "11 06 22 33"  # Incomplete payload
            )
        )
        assert False, "This should not have worked"
    except ValueError as e:
        assert str(e) == "Parameter is truncated"


def test_copy_xid():
    """
    Test that we can copy a XID frame.
    """
    frame = AX25ExchangeIdentificationFrame(
        destination="VK4BWI",
        source="VK4MSL",
        cr=True,
        fi=0x82,
        gi=0x80,
        parameters=[
            AX25XIDRawParameter(pi=0x12, pv=bytes([0x34, 0x56])),
            AX25XIDRawParameter(pi=0x34, pv=None),
        ],
    )
    framecopy = frame.copy()
    assert framecopy is not frame
    hex_cmp(
        bytes(framecopy),
        "ac 96 68 84 ae 92 e0"  # Destination
        "ac 96 68 9a a6 98 61"  # Source
        "af"  # Control
        "82"  # Format indicator
        "80"  # Group Ident
        "00 06"  # Group length
        # First parameter
        "12"  # Parameter ID
        "02"  # Length
        "34 56"  # Value
        # Second parameter
        "34"  # Parameter ID
        "00",  # Length (no value)
    )


def test_decode_cop_param():
    """
    Test we can decode a Class Of Procedures parameter.
    """
    param = AX25XIDClassOfProceduresParameter.decode(from_hex("80 20"))
    assert param.half_duplex == True
    assert param.full_duplex == False
    assert param.unbalanced_nrm_pri == False
    assert param.unbalanced_nrm_sec == False
    assert param.unbalanced_arm_pri == False
    assert param.unbalanced_arm_sec == False
    assert param.reserved == 256


def test_copy_cop_param():
    """
    Test we can copy a Class Of Procedures parameter.
    """
    param = AX25XIDClassOfProceduresParameter(
        full_duplex=False,
        half_duplex=True,
        reserved=193,  # See that it is preserved
    )
    copyparam = param.copy()
    assert param is not copyparam

    # Ensure all parameters match
    assert param.full_duplex == copyparam.full_duplex
    assert param.half_duplex == copyparam.half_duplex
    assert param.unbalanced_nrm_pri == copyparam.unbalanced_nrm_pri
    assert param.unbalanced_nrm_sec == copyparam.unbalanced_nrm_sec
    assert param.unbalanced_arm_pri == copyparam.unbalanced_arm_pri
    assert param.unbalanced_arm_sec == copyparam.unbalanced_arm_sec
    assert param.balanced_abm == copyparam.balanced_abm
    assert param.reserved == copyparam.reserved


def test_encode_cop_param():
    """
    Test we can encode a Class Of Procedures parameter.
    """
    param = AX25XIDClassOfProceduresParameter(
        reserved=232,  # 15-7 = 232
        full_duplex=True,  # 6 = 1
        half_duplex=False,  # 5 = 0
        unbalanced_nrm_pri=True,  # 1 = 1
    )

    # Expecting:
    #   0111 0100 0100 0011

    hex_cmp(param.pv, from_hex("74 43"))


def test_decode_hdlcfunc_param():
    """
    Test we can decode a HDLC Optional Functions parameter.
    """
    param = AX25XIDHDLCOptionalFunctionsParameter.decode(from_hex("86 a8 82"))
    # Specifically called out in the example (AX.25 2.2 spec Figure 4.6)
    assert param.srej == True
    assert param.rej == True
    assert param.extd_addr == True
    assert param.fcs16 == True
    assert param.modulo128 == True
    assert param.sync_tx == True
    # Changed by us to test round-tripping
    assert param.reserved2 == 2
    # Modulo128 is on, so we expect this off
    assert param.modulo8 == False
    # Expected defaults
    assert param.srej_multiframe == False
    assert param.start_stop_transp == False
    assert param.start_stop_flow_ctl == False
    assert param.sync_tx == True
    assert param.fcs32 == False
    assert param.rd == False
    assert param.test == True
    assert param.rset == False
    assert param.delete_i_cmd == False
    assert param.delete_i_resp == False
    assert param.basic_addr == False
    assert param.up == False
    assert param.sim_rim == False
    assert param.ui == False
    assert param.reserved1 == False


def test_copy_hdlcfunc_param():
    """
    Test we can copy a HDLC Optional Functions parameter.
    """
    param = AX25XIDHDLCOptionalFunctionsParameter(
        modulo128=False,
        modulo8=True,
        rej=True,
        srej=False,
        rset=True,
        test=False,
        fcs32=True,
        reserved1=True,
        reserved2=1,
    )
    copyparam = param.copy()
    assert param is not copyparam

    # Ensure all parameters match
    assert param.modulo128 == copyparam.modulo128
    assert param.modulo8 == copyparam.modulo8
    assert param.srej == copyparam.srej
    assert param.rej == copyparam.rej
    assert param.srej_multiframe == copyparam.srej_multiframe
    assert param.start_stop_transp == copyparam.start_stop_transp
    assert param.start_stop_flow_ctl == copyparam.start_stop_flow_ctl
    assert param.start_stop_tx == copyparam.start_stop_tx
    assert param.sync_tx == copyparam.sync_tx
    assert param.fcs32 == copyparam.fcs32
    assert param.fcs16 == copyparam.fcs16
    assert param.rd == copyparam.rd
    assert param.test == copyparam.test
    assert param.rset == copyparam.rset
    assert param.delete_i_cmd == copyparam.delete_i_cmd
    assert param.delete_i_resp == copyparam.delete_i_resp
    assert param.extd_addr == copyparam.extd_addr
    assert param.basic_addr == copyparam.basic_addr
    assert param.up == copyparam.up
    assert param.sim_rim == copyparam.sim_rim
    assert param.ui == copyparam.ui
    assert param.reserved2 == copyparam.reserved2
    assert param.reserved1 == copyparam.reserved1


def test_encode_hdlcfunc_param():
    """
    Test we can encode a HDLC Optional Functions parameter.
    """
    param = AX25XIDHDLCOptionalFunctionsParameter(
        modulo128=True,
        modulo8=False,
        srej=True,
        rej=False,
        # Some atypical values
        ui=True,
        fcs32=True,
        reserved2=2,
    )

    hex_cmp(param.pv, from_hex("8c a8 83"))


def test_encode_retries_param():
    """
    Test we can encode a Retries parameter.
    """
    param = AX25XIDRetriesParameter(96)

    hex_cmp(param.pv, from_hex("60"))


def test_decode_retries_param():
    """
    Test we can decode a Retries parameter.
    """
    param = AX25XIDRetriesParameter.decode(from_hex("10"))
    assert param.value == 16


def test_copy_retries_param():
    """
    Test we can copy a Retries parameter.
    """
    param = AX25XIDRetriesParameter(38)
    copyparam = param.copy()
    assert param is not copyparam

    # Ensure all parameters match
    assert param.value == copyparam.value

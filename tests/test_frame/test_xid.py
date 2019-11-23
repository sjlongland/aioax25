#!/usr/bin/env python3

from aioax25.frame import AX25Frame, \
        AX25ExchangeIdentificationFrame, AX25XIDRawParameter, \
        AX25XIDParameterIdentifier, AX25XIDClassOfProceduresParameter, \
        AX25XIDHDLCOptionalFunctionsParameter, \
        AX25XIDIFieldLengthReceiveParameter, \
        AX25XIDRetriesParameter

from nose.tools import eq_
from ..hex import from_hex, hex_cmp

def test_encode_xid():
    """
    Test that we can encode a XID frame.
    """
    frame = AX25ExchangeIdentificationFrame(
            destination='VK4BWI',
            source='VK4MSL',
            cr=True,
            fi=0x82, gi=0x80,
            parameters=[
                # Typical parameters we'd expect to see
                AX25XIDClassOfProceduresParameter(
                    half_duplex=True
                ),
                AX25XIDHDLCOptionalFunctionsParameter(
                    srej=True, rej=True,
                    modulo128=True
                ),
                AX25XIDIFieldLengthReceiveParameter(1024),
                AX25XIDRetriesParameter(5),
                # Arbitrary parameters for testing
                AX25XIDRawParameter(
                    pi=0x12, pv=bytes([0x34, 0x56])
                ),
                AX25XIDRawParameter(
                    pi=0x34, pv=None
                )
            ]
    )
    hex_cmp(bytes(frame),
            'ac 96 68 84 ae 92 e0'                          # Destination
            'ac 96 68 9a a6 98 61'                          # Source
            'af'                                            # Control
            '82'                                            # Format indicator
            '80'                                            # Group Ident
            '00 16'                                         # Group length
            # First parameter: CoP
            '02'                                            # Parameter ID
            '02'                                            # Length
            '00 21'                                         # Value
            # Second parameter: HDLC Optional Functions
            '03'                                            # Parameter ID
            '03'                                            # Length
            '86 a8 02'                                      # Value
            # Third parameter: I field receive size
            '06'
            '02'
            '04 00'
            # Fourth parameter: retries
            '0a'
            '01'
            '05'
            # Fifth parameter: custom
            '12'
            '02'
            '34 56'
            # Sixth parameter: custom, no length set
            '34'
            '00'
    )


def test_decode_xid():
    """
    Test that we can decode a XID frame.
    """
    frame = AX25Frame.decode(
            from_hex(
                'ac 96 68 84 ae 92 e0'                      # Destination
                'ac 96 68 9a a6 98 61'                      # Source
                'af'                                        # Control
                '82'                                        # FI
                '80'                                        # GI
                '00 0c'                                     # GL
                # Some parameters
                '11 01 aa'
                '12 01 bb'
                '13 02 11 22'
                '14 00'
            )
    )
    assert isinstance(frame, AX25ExchangeIdentificationFrame)
    eq_(frame.fi, 0x82)
    eq_(frame.gi, 0x80)
    eq_(len(frame.parameters), 4)

    param = frame.parameters[0]
    eq_(param.pi, 0x11)
    eq_(param.pv, b'\xaa')

    param = frame.parameters[1]
    eq_(param.pi, 0x12)
    eq_(param.pv, b'\xbb')

    param = frame.parameters[2]
    eq_(param.pi, 0x13)
    eq_(param.pv, b'\x11\x22')

    param = frame.parameters[3]
    eq_(param.pi, 0x14)
    assert param.pv is None


def test_decode_xid_fig46():
    """
    Test that we can decode the XID example from AX.25 2.2 figure 4.6.
    """
    frame = AX25Frame.decode(
            from_hex(
                '9c 94 6e a0 40 40 e0'                      # Destination
                '9c 6e 98 8a 9a 40 61'                      # Source
                'af'                                        # Control
                '82'                                        # FI
                '80'                                        # GI
                '00 17'                                     # GL
                '02 02 00 20'
                '03 03 86 a8 02'
                '06 02 04 00'
                '08 01 02'
                '09 02 10 00'
                '0a 01 03'
            )
    )
    eq_(len(frame.parameters), 6)

    param = frame.parameters[0]
    eq_(param.pi, AX25XIDParameterIdentifier.ClassesOfProcedure)
    eq_(param.pv, b'\x00\x20')

    param = frame.parameters[1]
    eq_(param.pi, AX25XIDParameterIdentifier.HDLCOptionalFunctions)
    eq_(param.pv, b'\x86\xa8\x02')

    param = frame.parameters[2]
    eq_(param.pi, AX25XIDParameterIdentifier.IFieldLengthReceive)
    eq_(param.pv, b'\x04\x00')

    param = frame.parameters[3]
    eq_(param.pi, AX25XIDParameterIdentifier.WindowSizeReceive)
    eq_(param.pv, b'\x02')

    param = frame.parameters[4]
    eq_(param.pi, AX25XIDParameterIdentifier.AcknowledgeTimer)
    eq_(param.pv, b'\x10\x00')

    param = frame.parameters[5]
    eq_(param.pi, AX25XIDParameterIdentifier.Retries)
    eq_(param.pv, b'\x03')


def test_decode_xid_truncated_header():
    """
    Test that decoding a XID with truncated header fails.
    """
    try:
        AX25Frame.decode(
                from_hex(
                    'ac 96 68 84 ae 92 e0'                  # Destination
                    'ac 96 68 9a a6 98 61'                  # Source
                    'af'                                    # Control
                    '82'                                    # FI
                    '80'                                    # GI
                    '00'                                    # Incomplete GL
                )
        )
        assert False, 'This should not have worked'
    except ValueError as e:
        eq_(str(e), 'Truncated XID header')


def test_decode_xid_truncated_payload():
    """
    Test that decoding a XID with truncated payload fails.
    """
    try:
        AX25Frame.decode(
                from_hex(
                    'ac 96 68 84 ae 92 e0'                  # Destination
                    'ac 96 68 9a a6 98 61'                  # Source
                    'af'                                    # Control
                    '82'                                    # FI
                    '80'                                    # GI
                    '00 05'                                 # GL
                    '11'                                    # Incomplete payload
                )
        )
        assert False, 'This should not have worked'
    except ValueError as e:
        eq_(str(e), 'Truncated XID data')

def test_decode_xid_truncated_param_header():
    """
    Test that decoding a XID with truncated parameter header fails.
    """
    try:
        AX25Frame.decode(
                from_hex(
                    'ac 96 68 84 ae 92 e0'                  # Destination
                    'ac 96 68 9a a6 98 61'                  # Source
                    'af'                                    # Control
                    '82'                                    # FI
                    '80'                                    # GI
                    '00 01'                                 # GL
                    '11'                                    # Incomplete payload
                )
        )
        assert False, 'This should not have worked'
    except ValueError as e:
        eq_(str(e), 'Insufficient data for parameter')

def test_decode_xid_truncated_param_value():
    """
    Test that decoding a XID with truncated parameter value fails.
    """
    try:
        AX25Frame.decode(
                from_hex(
                    'ac 96 68 84 ae 92 e0'                  # Destination
                    'ac 96 68 9a a6 98 61'                  # Source
                    'af'                                    # Control
                    '82'                                    # FI
                    '80'                                    # GI
                    '00 04'                                 # GL
                    '11 06 22 33'                           # Incomplete payload
                )
        )
        assert False, 'This should not have worked'
    except ValueError as e:
        eq_(str(e), 'Parameter is truncated')

def test_copy_xid():
    """
    Test that we can copy a XID frame.
    """
    frame = AX25ExchangeIdentificationFrame(
            destination='VK4BWI',
            source='VK4MSL',
            cr=True,
            fi=0x82, gi=0x80,
            parameters=[
                AX25XIDRawParameter(
                    pi=0x12, pv=bytes([0x34, 0x56])
                ),
                AX25XIDRawParameter(
                    pi=0x34, pv=None
                )
            ]
    )
    framecopy = frame.copy()
    assert framecopy is not frame
    hex_cmp(bytes(framecopy),
            'ac 96 68 84 ae 92 e0'                          # Destination
            'ac 96 68 9a a6 98 61'                          # Source
            'af'                                            # Control
            '82'                                            # Format indicator
            '80'                                            # Group Ident
            '00 06'                                         # Group length
            # First parameter
            '12'                                            # Parameter ID
            '02'                                            # Length
            '34 56'                                         # Value
            # Second parameter
            '34'                                            # Parameter ID
            '00'                                            # Length (no value)
    )

def test_decode_cop_param():
    """
    Test we can decode a Class Of Procedures parameter.
    """
    param = AX25XIDClassOfProceduresParameter.decode(from_hex(
        '80 20'
    ))
    eq_(param.half_duplex, True)
    eq_(param.full_duplex, False)
    eq_(param.unbalanced_nrm_pri, False)
    eq_(param.unbalanced_nrm_sec, False)
    eq_(param.unbalanced_arm_pri, False)
    eq_(param.unbalanced_arm_sec, False)
    eq_(param.reserved, 256)

def test_copy_cop_param():
    """
    Test we can copy a Class Of Procedures parameter.
    """
    param = AX25XIDClassOfProceduresParameter(
            full_duplex=False,
            half_duplex=True,
            reserved=193    # See that it is preserved
    )
    copyparam = param.copy()
    assert param is not copyparam

    # Ensure all parameters match
    eq_(param.full_duplex, copyparam.full_duplex)
    eq_(param.half_duplex, copyparam.half_duplex)
    eq_(param.unbalanced_nrm_pri, copyparam.unbalanced_nrm_pri)
    eq_(param.unbalanced_nrm_sec, copyparam.unbalanced_nrm_sec)
    eq_(param.unbalanced_arm_pri, copyparam.unbalanced_arm_pri)
    eq_(param.unbalanced_arm_sec, copyparam.unbalanced_arm_sec)
    eq_(param.balanced_abm, copyparam.balanced_abm)
    eq_(param.reserved, copyparam.reserved)

def test_encode_cop_param():
    """
    Test we can encode a Class Of Procedures parameter.
    """
    param = AX25XIDClassOfProceduresParameter(
            reserved=232,                                       # 15-7 = 232
            full_duplex=True,                                   # 6 = 1
            half_duplex=False,                                  # 5 = 0
            unbalanced_nrm_pri=True                             # 1 = 1
    )

    # Expecting:
    #   0111 0100 0100 0011

    hex_cmp(param.pv,
            from_hex(
                '74 43'
            )
    )

def test_decode_hdlcfunc_param():
    """
    Test we can decode a HDLC Optional Functions parameter.
    """
    param = AX25XIDHDLCOptionalFunctionsParameter.decode(from_hex(
        '86 a8 82'
    ))
    # Specifically called out in the example (AX.25 2.2 spec Figure 4.6)
    eq_(param.srej, True)
    eq_(param.rej, True)
    eq_(param.extd_addr, True)
    eq_(param.fcs16, True)
    eq_(param.modulo128, True)
    eq_(param.sync_tx, True)
    # Changed by us to test round-tripping
    eq_(param.reserved2, 2)
    # Modulo128 is on, so we expect this off
    eq_(param.modulo8, False)
    # Expected defaults
    eq_(param.srej_multiframe, False)
    eq_(param.start_stop_transp, False)
    eq_(param.start_stop_flow_ctl, False)
    eq_(param.sync_tx, True)
    eq_(param.fcs32, False)
    eq_(param.rd, False)
    eq_(param.test, True)
    eq_(param.rset, False)
    eq_(param.delete_i_cmd, False)
    eq_(param.delete_i_resp, False)
    eq_(param.basic_addr, False)
    eq_(param.up, False)
    eq_(param.sim_rim, False)
    eq_(param.ui, False)
    eq_(param.reserved1, False)

def test_copy_hdlcfunc_param():
    """
    Test we can copy a HDLC Optional Functions parameter.
    """
    param = AX25XIDHDLCOptionalFunctionsParameter(
            modulo128=False, modulo8=True,
            rej=True, srej=False,
            rset=True, test=False, fcs32=True,
            reserved1=True,
            reserved2=1
    )
    copyparam = param.copy()
    assert param is not copyparam

    # Ensure all parameters match
    eq_(param.modulo128, copyparam.modulo128)
    eq_(param.modulo8, copyparam.modulo8)
    eq_(param.srej, copyparam.srej)
    eq_(param.rej, copyparam.rej)
    eq_(param.srej_multiframe, copyparam.srej_multiframe)
    eq_(param.start_stop_transp, copyparam.start_stop_transp)
    eq_(param.start_stop_flow_ctl, copyparam.start_stop_flow_ctl)
    eq_(param.start_stop_tx, copyparam.start_stop_tx)
    eq_(param.sync_tx, copyparam.sync_tx)
    eq_(param.fcs32, copyparam.fcs32)
    eq_(param.fcs16, copyparam.fcs16)
    eq_(param.rd, copyparam.rd)
    eq_(param.test, copyparam.test)
    eq_(param.rset, copyparam.rset)
    eq_(param.delete_i_cmd, copyparam.delete_i_cmd)
    eq_(param.delete_i_resp, copyparam.delete_i_resp)
    eq_(param.extd_addr, copyparam.extd_addr)
    eq_(param.basic_addr, copyparam.basic_addr)
    eq_(param.up, copyparam.up)
    eq_(param.sim_rim, copyparam.sim_rim)
    eq_(param.ui, copyparam.ui)
    eq_(param.reserved2, copyparam.reserved2)
    eq_(param.reserved1, copyparam.reserved1)

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
            reserved2=2
    )

    hex_cmp(param.pv,
            from_hex(
                '8c a8 83'
            )
    )

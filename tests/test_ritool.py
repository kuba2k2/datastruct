#  Copyright (c) Kuba Szczodrzyński 2024-10-11.

import pytest
from base import TestBase, TestData
from test_ritool_structs import *

TEST_DATA = [
    pytest.param(
        TestData(
            data=(
                b"\x30\x31\x41\x4c\x43\x4c\x30\x32\x33\x46\x45\x35\x36\x33\x38\x39"
                b"\x41\x42\x42\x44\x30\x31\x20\x20\x20\x20\x20\x20\x20\x20\x44\x45"
                b"\x41\x44\x42\x45\x45\x46\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30"
                b"\x47\x2d\x30\x31\x30\x47\x2d\x41\x31\x39\x30\x38\x31\x37\x00\xde"
                b"\xad\xbe\xef\xaa\x00\x00\x00\x5e\x00\x01\x20\x20\x20\x20\x00\x00"
                b"\x00\x00\x00\x01\x23\x45\x67\x89\xde\xad\xbe\xef\x00\x00\x00\x00"
                b"\x00\x00\x00\x00\x33\x46\x45\x35\x36\x33\x38\x39\x41\x42\x42\x41"
                b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x8f\xe7\x00\x00"
                b"\x20\x20\x20\x20\x20\x20\x20\x20\x75\x73\x72\x61\x64\x6d\x69\x6e"
                b"\x75\x73\x72\x61\x64\x6d\x69\x6e\x20\x20\x20\x20\x20\x20\x61\x64"
                b"\x6d\x69\x6e\x61\x64\x6d\x69\x6e\x20\x41\x4c\x43\x23\x46\x47\x55"
                b"\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30"
                b"\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30"
                b"\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30"
                b"\x58\x58\x58\x58\x00\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30"
                b"\x30\x30\x30\x30\x30\x31\x00\x00\x00\x00\x00\x00\xe2\xe3\x00\x00"
            ),
            obj_full=RiData(
                format="01",
                mfr_id="ALCL",
                factory_code="02",
                hw_version="3FE56389ABBD",
                ics="01",
                yp_serial_num="        DEADBEEF",
                clei_code="0000000000",
                mnemonic="G-010G-A",
                prog_date="190817",
                mac_address=MAC("00-DE-AD-BE-EF-AA"),
                device_id_pref="0000",
                sw_image="005e",
                onu_mode="0001",
                mnemonic2="    ",
                password="00000000000123456789",
                g894_serial="deadbeef",
                hw_configuration="0000000000000000",
                part_number="3FE56389ABBA",
                spare4="000000000000000000000000",
                checksum="8fe7",
                inservice_reg="0000",
                user_name="        usradmin",
                user_password="usradmin",
                mgnt_user_name="      adminadmin",
                mgnt_user_password=" ALC#FGU",
                ssid1_name="0000000000000000",
                ssid1_password="00000000",
                ssid2_name="0000000000000000",
                ssid2_password="00000000",
                operator_id="XXXX",
                slid="00303030303030303030303030303030",
                country_id="01",
                spare_5="000000000000",
                checksum1="e2e3",
                spare6="0000",
            ),
        ),
        id="ritool_1",
    ),
    pytest.param(
        TestData(
            data=(
                b"\x30\x31\x41\x4c\x43\x4c\x30\x32\x33\x46\x45\x34\x36\x32\x35\x36"
                b"\x41\x41\x41\x42\x30\x31\x20\x20\x20\x20\x20\x20\x20\x20\x44\x45"
                b"\x41\x44\x42\x45\x45\x46\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30"
                b"\x47\x2d\x32\x34\x30\x57\x2d\x43\x31\x39\x30\x33\x32\x39\x00\xde"
                b"\xad\xbe\xef\xaa\x00\x00\x30\x30\x00\x03\x20\x20\x20\x20\x30\x30"
                b"\x30\x30\x30\x30\x30\x30\x30\x30\xde\xad\xbe\xef\x30\x30\x30\x30"
                b"\x30\x30\x30\x30\x33\x46\x45\x34\x36\x32\x35\x37\x41\x41\x41\x42"
                b"\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x6e\xe5\x30\x30"
                b"\x20\x20\x20\x20\x20\x20\x20\x75\x73\x65\x72\x41\x64\x6d\x69\x6e"
                b"\x30\x30\x30\x30\x30\x30\x30\x30\x20\x20\x20\x20\x20\x20\x61\x64"
                b"\x6d\x69\x6e\x61\x64\x6d\x69\x6e\x20\x41\x4c\x43\x23\x46\x47\x55"
                b"\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30"
                b"\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30"
                b"\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30"
                b"\x41\x4c\x43\x4c\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30\x30"
                b"\x30\x30\x30\x30\x65\x75\x30\x30\x30\x30\x30\x30\x1b\xe4\x30\x30"
            ),
            obj_full=RiData(
                format="01",
                mfr_id="ALCL",
                factory_code="02",
                hw_version="3FE46256AAAB",
                ics="01",
                yp_serial_num="        DEADBEEF",
                clei_code="0000000000",
                mnemonic="G-240W-C",
                prog_date="190329",
                mac_address=MAC("00-DE-AD-BE-EF-AA"),
                device_id_pref="0000",
                sw_image="3030",
                onu_mode="0003",
                mnemonic2="    ",
                password="30303030303030303030",
                g894_serial="deadbeef",
                hw_configuration="3030303030303030",
                part_number="3FE46257AAAB",
                spare4="303030303030303030303030",
                checksum="6ee5",
                inservice_reg="3030",
                user_name="       userAdmin",
                user_password="00000000",
                mgnt_user_name="      adminadmin",
                mgnt_user_password=" ALC#FGU",
                ssid1_name="0000000000000000",
                ssid1_password="00000000",
                ssid2_name="0000000000000000",
                ssid2_password="00000000",
                operator_id="ALCL",
                slid="30303030303030303030303030303030",
                country_id="eu",
                spare_5="303030303030",
                checksum1="1be4",
                spare6="3030",
            ),
        ),
        id="ritool_2",
    ),
]


@pytest.mark.parametrize("test", TEST_DATA)
class TestRitool(TestBase):
    pass


del TestBase

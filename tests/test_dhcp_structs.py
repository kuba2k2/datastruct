#  Copyright (c) Kuba Szczodrzyński 2023-9-10.
#  https://github.com/kuba2k2/pynetkit/blob/master/pynetkit/modules/dhcp/structs.py

from dataclasses import dataclass
from datetime import timedelta
from enum import IntEnum, IntFlag
from ipaddress import IPv4Address
from random import randint
from typing import Any

from macaddress import MAC

from datastruct import NETWORK, DataStruct, datastruct
from datastruct.adapters.network import ipv4_field, mac_field
from datastruct.adapters.time import timedelta_field
from datastruct.fields import (
    built,
    cond,
    const,
    field,
    padding,
    repeat,
    subfield,
    switch,
    text,
    varlist,
    vartext,
)


class DhcpPacketType(IntEnum):
    BOOT_REQUEST = 1
    BOOT_REPLY = 2


class DhcpMessageType(IntEnum):
    DISCOVER = 1
    OFFER = 2
    REQUEST = 3
    DECLINE = 4
    ACK = 5
    NAK = 6
    RELEASE = 7
    INFORM = 8
    FORCERENEW = 9
    LEASEQUERY = 10
    LEASEUNASSIGNED = 11
    LEASEUNKNOWN = 12
    LEASEACTIVE = 13
    BULKLEASEQUERY = 14
    LEASEQUERYDONE = 15
    ACTIVELEASEQUERY = 16
    LEASEQUERYSTATUS = 17
    TLS = 18


class DhcpBootpFlags(IntFlag):
    BROADCAST = 1 << 15


class DhcpOptionType(IntEnum):
    SUBNET_MASK = 1
    TIME_OFFSET = 2
    ROUTER = 3
    TIME_SERVERS = 4
    NAME_SERVERS = 5
    DNS_SERVERS = 6
    LOG_SERVERS = 7
    COOKIE_SERVERS = 8
    LPR_SERVERS = 9
    IMPRESS_SERVERS = 10
    RLP_SERVERS = 11
    HOST_NAME = 12
    BOOT_FILE_SIZE = 13
    MERIT_DUMP_FILE = 14
    DOMAIN_NAME = 15
    SWAP_SERVER = 16
    ROOT_PATH = 17
    EXTENSION_FILE = 18
    IP_LAYER_FORWARDING_ = 19
    SRC_ROUTE_ENABLER = 20
    POLICY_FILTER = 21
    MAXIMUM_DG_REASSEMBLY_SIZE = 22
    DEFAULT_IP_TTL = 23
    PATH_MTU_AGING_TIMEOUT = 24
    MTU_PLATEAU_ = 25
    INTERFACE_MTU_SIZE = 26
    ALL_SUBNETS_ARE_LOCAL = 27
    BROADCAST_ADDRESS = 28
    PERFORM_MASK_DISCOVERY = 29
    PROVIDE_MASK_TO_OTHERS = 30
    PERFORM_ROUTER_DISCOVERY = 31
    ROUTER_SOLICITATION_ADDRESS = 32
    STATIC_ROUTING_TABLE = 33
    TRAILER_ENCAPSULATION = 34
    ARP_CACHE_TIMEOUT = 35
    ETHERNET_ENCAPSULATION = 36
    DEFAULT_TCP_TIME_TO_LIVE = 37
    TCP_KEEPALIVE_INTERVAL = 38
    TCP_KEEPALIVE_GARBAGE = 39
    NIS_DOMAIN_NAME = 40
    NIS_SERVER_ADDRESSES = 41
    NTP_SERVERS_ADDRESSES = 42
    VENDOR_SPECIFIC_INFORMATION = 43
    NETBIOS_NAME_SERVER = 44
    NETBIOS_DATAGRAM_DISTRIBUTION_ = 45
    NETBIOS_NODE_TYPE = 46
    NETBIOS_SCOPE = 47
    X_WINDOW_FONT_SERVER = 48
    X_WINDOW_DISPLAY_MANAGER = 49
    REQUESTED_IP_ADDRESS = 50
    IP_ADDRESS_LEASE_TIME = 51
    OPTION_OVERLOAD = 52
    MESSAGE_TYPE = 53
    SERVER_IDENTIFIER = 54
    PARAMETER_REQUEST_LIST = 55
    MESSAGE = 56
    MAXIMUM_MESSAGE_SIZE = 57
    RENEW_TIME_VALUE = 58
    REBINDING_TIME_VALUE = 59
    VENDOR_CLASS_IDENTIFIER = 60
    CLIENT_IDENTIFIER = 61
    NETWARE_IP_DOMAIN_NAME = 62
    NETWARE_IP_SUB_OPTIONS = 63
    NIS_V3_CLIENT_DOMAIN_NAME = 64
    NIS_V3_SERVER_ADDRESS = 65
    TFTP_SERVER_NAME = 66
    BOOT_FILE_NAME = 67
    HOME_AGENT_ADDRESSES = 68
    SIMPLE_MAIL_SERVER_ADDRESSES = 69
    POST_OFFICE_SERVER_ADDRESSES = 70
    NETWORK_NEWS_SERVER_ADDRESSES = 71
    WWW_SERVER_ADDRESSES = 72
    FINGER_SERVER_ADDRESSES = 73
    CHAT_SERVER_ADDRESSES = 74
    STREETTALK_SERVER_ADDRESSES = 75
    STREETTALK_DIRECTORY_ASSISTANCE_ADDRESSES = 76
    USER_CLASS_INFORMATION = 77
    SLP_DIRECTORY_AGENT = 78
    SLP_SERVICE_SCOPE = 79
    RAPID_COMMIT = 80
    FQDN = 81
    RELAY_AGENT_INFORMATION = 82
    INTERNET_STORAGE_NAME_SERVICE = 83
    NOVELL_DIRECTORY_SERVERS = 85
    NOVELL_DIRECTORY_SERVER_TREE_NAME = 86
    NOVELL_DIRECTORY_SERVER_CONTEXT = 87
    BCMCS_CONTROLLER_DOMAIN_NAME_LIST = 88
    BCMCS_CONTROLLER_IPV4_ADDRESS_LIST = 89
    AUTHENTICATION = 90
    CLIENT_SYSTEM = 93
    CLIENT_NETWORK_DEVICE_INTERFACE = 94
    LDAP_USE = 95
    UUID_BASED_CLIENT_IDENTIFIER = 97
    OPEN_GROUP_USER_AUTHENTICATION = 98
    IPV6_ONLY_PREFERRED = 108
    DHCP_CAPTIVE_PORTAL = 114
    DOMAIN_SEARCH = 119
    CLASSLESS_STATIC_ROUTE = 121
    PRIVATE = 224
    PRIVATE_CLASSLESS_STATIC_ROUTE = 249
    PRIVATE_PROXY_AUTODISCOVERY = 252
    END = 255


@dataclass
class DhcpClientIdentifier(DataStruct):
    hardware_type: int = const(1)(field("B"))
    mac_address: MAC = mac_field()


@dataclass
@datastruct(endianness=NETWORK, padding_pattern=b"\x00")
class DhcpOption(DataStruct):
    option: DhcpOptionType = field("B")
    length: int = cond(lambda ctx: ctx.option != 255, if_not=0)(
        built("B", lambda ctx: ctx.sizeof("data"))
    )
    data: Any = cond(lambda ctx: ctx.option != 255, if_not=None)(
        switch(lambda ctx: ctx.option)(
            MESSAGE_TYPE=(DhcpMessageType, field("B")),
            CLIENT_IDENTIFIER=(DhcpClientIdentifier, subfield()),
            MAXIMUM_MESSAGE_SIZE=(int, field("H")),
            INTERFACE_MTU_SIZE=(int, field("H")),
            NETBIOS_NODE_TYPE=(int, field("B")),
            # time values
            IP_ADDRESS_LEASE_TIME=(timedelta, timedelta_field()),
            RENEW_TIME_VALUE=(timedelta, timedelta_field()),
            REBINDING_TIME_VALUE=(timedelta, timedelta_field()),
            # text options
            VENDOR_CLASS_IDENTIFIER=(str, vartext(lambda ctx: ctx.length)),
            HOST_NAME=(str, vartext(lambda ctx: ctx.length)),
            DOMAIN_NAME=(str, vartext(lambda ctx: ctx.length)),
            # IP address options
            REQUESTED_IP_ADDRESS=(IPv4Address, ipv4_field()),
            SERVER_IDENTIFIER=(IPv4Address, ipv4_field()),
            SUBNET_MASK=(IPv4Address, ipv4_field()),
            BROADCAST_ADDRESS=(IPv4Address, ipv4_field()),
            ROUTER=(IPv4Address, ipv4_field()),
            DNS_SERVERS=(IPv4Address, ipv4_field()),
            # other options
            PARAMETER_REQUEST_LIST=(
                list[DhcpOptionType],
                varlist(lambda ctx: ctx.length)(field("B")),
            ),
            default=(bytes, field(lambda ctx: ctx.length)),
        )
    )


@dataclass
@datastruct(endianness=NETWORK, padding_pattern=b"\x00")
class DhcpPacket(DataStruct):
    packet_type: DhcpPacketType = field("B")
    hardware_type: int = const(1)(field("B"))
    hardware_alen: int = const(6)(field("B"))
    hops: int = field("b", default=0)
    transaction_id: int = field("I", default_factory=lambda: randint(0, 0xFFFFFFFF))
    seconds_elapsed: timedelta = timedelta_field("H", default=timedelta(0))
    bootp_flags: DhcpBootpFlags = field("H", default=0)
    client_ip_address: IPv4Address = ipv4_field(default=IPv4Address(0))
    your_ip_address: IPv4Address = ipv4_field(default=IPv4Address(0))
    server_ip_address: IPv4Address = ipv4_field(default=IPv4Address(0))
    gateway_ip_address: IPv4Address = ipv4_field(default=IPv4Address(0))
    client_mac_address: MAC = mac_field()
    _1: ... = padding(10)
    server_host_name: str = text(64, default="")
    boot_file_name: str = text(128, default="")
    magic_cookie: bytes = const(b"\x63\x82\x53\x63")(field(4))
    options: list[DhcpOption] = repeat(
        last=lambda ctx: ctx.P.item.option == 255,
        default_factory=lambda: [DhcpOption(DhcpOptionType.END)],
    )(subfield())

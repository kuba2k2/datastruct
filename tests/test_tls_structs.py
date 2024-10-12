#  Copyright (c) Kuba Szczodrzyński 2024-10-12.
#  https://github.com/kuba2k2/pynetkit/blob/master/pynetkit/modules/proxy/structs.py

from dataclasses import dataclass
from enum import Enum, IntEnum

from datastruct import NETWORK, DataStruct, datastruct
from datastruct.fields import cond, field, padding, repeat, subfield, switch, text


class TlsVersion(IntEnum):
    SSLv3 = 0x300
    TLSv1 = 0x301
    TLSv1_1 = 0x302
    TLSv1_2 = 0x303
    TLSv1_3 = 0x304


@dataclass
@datastruct(endianness=NETWORK, padding_pattern=b"\x00")
class TlsExtension(DataStruct):
    class Type(IntEnum):
        SERVER_NAME = 0
        MAX_FRAGMENT_LENGTH = 1
        CLIENT_CERTIFICATE_URL = 2
        TRUSTED_CA_KEYS = 3
        TRUNCATED_HMAC = 4
        STATUS_REQUEST = 5
        USER_MAPPING = 6
        CLIENT_AUTHZ = 7
        SERVER_AUTHZ = 8
        CERT_TYPE = 9
        SUPPORTED_GROUPS = 10
        EC_POINT_FORMATS = 11
        SRP = 12
        SIGNATURE_ALGORITHMS = 13
        USE_SRTP = 14
        HEARTBEAT = 15
        APPLICATION_LAYER_PROTOCOL_NEGOTIATION = 16
        STATUS_REQUEST_V2 = 17
        SIGNED_CERTIFICATE_TIMESTAMP = 18
        CLIENT_CERTIFICATE_TYPE = 19
        SERVER_CERTIFICATE_TYPE = 20
        PADDING = 21
        ENCRYPT_THEN_MAC = 22
        EXTENDED_MASTER_SECRET = 23
        TOKEN_BINDING = 24
        CACHED_INFO = 25
        TLS_LTS = 26
        COMPRESS_CERTIFICATE = 27
        RECORD_SIZE_LIMIT = 28
        PWD_PROTECT = 29
        PWD_CLEAR = 30
        PASSWORD_SALT = 31
        TICKET_PINNING = 32
        TLS_CERT_WITH_EXTERN_PSK = 33
        DELEGATED_CREDENTIAL = 34
        SESSION_TICKET = 35
        TLMSP = 36
        TLMSP_PROXYING = 37
        TLMSP_DELEGATE = 38
        SUPPORTED_EKT_CIPHERS = 39
        PRE_SHARED_KEY = 41
        EARLY_DATA = 42
        SUPPORTED_VERSIONS = 43
        COOKIE = 44
        PSK_KEY_EXCHANGE_MODES = 45
        CERTIFICATE_AUTHORITIES = 47
        OID_FILTERS = 48
        POST_HANDSHAKE_AUTH = 49
        SIGNATURE_ALGORITHMS_CERT = 50
        KEY_SHARE = 51
        TRANSPARENCY_INFO = 52
        CONNECTION_ID_DEPRECATED = 53
        CONNECTION_ID = 54
        EXTERNAL_ID_HASH = 55
        EXTERNAL_SESSION_ID = 56
        QUIC_TRANSPORT_PARAMETERS = 57
        TICKET_REQUEST = 58
        DNSSEC_CHAIN = 59
        SEQUENCE_NUMBER_ENCRYPTION_ALGORITHMS = 60
        RRC = 61
        ECH_OUTER_EXTENSIONS = 64768
        ENCRYPTED_CLIENT_HELLO = 65037
        RENEGOTIATION_INFO = 65281

    @dataclass
    @datastruct(endianness=NETWORK, padding_pattern=b"\x00")
    class ServerName(DataStruct):
        @dataclass
        @datastruct(endianness=NETWORK, padding_pattern=b"\x00")
        class Name(DataStruct):
            type: int = field("B")
            length: int = field("H")
            value: str = text(lambda ctx: ctx.length)

        names_length: int = field("H")
        names: list[Name] = repeat(
            length=lambda ctx: ctx.names_length,
        )(subfield())

    type: int = field("H")
    length: int = field("H")
    data: bytes | ServerName = switch(lambda ctx: bool(ctx.length) and ctx.type)(
        _0=(ServerName, subfield()),
        default=(bytes, field(lambda ctx: ctx.length)),
    )


@dataclass
@datastruct(endianness=NETWORK, padding_pattern=b"\x00")
class TlsHandshakeHello(DataStruct):
    version: TlsVersion = field("H")
    random: bytes = field(32)
    session_id_length: int = field("B")
    session_id: bytes = field(lambda ctx: ctx.session_id_length)
    cipher_suites_length: int = cond(
        lambda ctx: ctx._.type == TlsHandshake.Type.CLIENT_HELLO,
        if_not=2,
    )(field("H"))
    cipher_suites: list[int] = repeat(
        lambda ctx: ctx.cipher_suites_length // 2,
    )(field("H"))
    compression_methods_length: int = cond(
        lambda ctx: ctx._.type == TlsHandshake.Type.CLIENT_HELLO,
        if_not=1,
    )(field("B"))
    compression_methods: list[int] = repeat(
        lambda ctx: ctx.compression_methods_length,
    )(field("B"))
    extensions_length: int = field("H")
    extensions: list[TlsExtension] = repeat(
        length=lambda ctx: ctx.extensions_length,
    )(subfield())


@dataclass
@datastruct(endianness=NETWORK, padding_pattern=b"\x00")
class TlsHandshakeCertificate(DataStruct):
    @dataclass
    @datastruct(endianness=NETWORK, padding_pattern=b"\x00")
    class Certificate(DataStruct):
        _1: ... = padding(1)
        length: int = field("H")
        data: bytes = field(lambda ctx: ctx.length)

    _1: ... = padding(1)
    certificates_length: int = field("H")
    certificates: list[Certificate] = repeat(
        length=lambda ctx: ctx.certificates_length,
    )(subfield())


@dataclass
@datastruct(endianness=NETWORK, padding_pattern=b"\x00")
class TlsHandshake(DataStruct):
    class Type(Enum):
        CLIENT_HELLO = 1
        SERVER_HELLO = 2
        CERTIFICATE = 11

        @classmethod
        def _missing_(cls, value):
            unknown = object.__new__(TlsHandshake.Type)
            unknown._name_ = f"UNKNOWN_{value}"
            unknown._value_ = value
            return unknown

    type: Type = field("B")
    _1: ... = padding(1)
    length: int = field("H")
    data: bytes | TlsHandshakeHello | TlsHandshakeCertificate = switch(
        lambda ctx: ctx.type
    )(
        CLIENT_HELLO=(TlsHandshakeHello, subfield()),
        SERVER_HELLO=(TlsHandshakeHello, subfield()),
        CERTIFICATE=(TlsHandshakeCertificate, subfield()),
        default=(bytes, field(lambda ctx: ctx.length)),
    )


@dataclass
@datastruct(endianness=NETWORK, padding_pattern=b"\x00")
class TlsRecord(DataStruct):
    class Type(IntEnum):
        CHANGE_CIPHER_SPEC = 20
        ALERT = 21
        HANDSHAKE = 22
        APPLICATION_DATA = 23

    type: Type = field("B")
    version: TlsVersion = field("H")
    length: int = field("H")
    data: bytes | TlsHandshake = switch(lambda ctx: ctx.type)(
        HANDSHAKE=(TlsHandshake, subfield()),
        default=(bytes, field(lambda ctx: ctx.length)),
    )

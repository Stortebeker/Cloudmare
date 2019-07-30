# Copyright (C) 2001-2007, 2009-2011 Nominum, Inc.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose with or without fee is hereby granted,
# provided that the above copyright notice and this permission notice
# appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND NOMINUM DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL NOMINUM BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""DNS TSIG support."""

import hashlib
import hmac
import struct

import thirdparty.dns.exception
import thirdparty.dns.hash
import thirdparty.dns.rdataclass
import thirdparty.dns.name

class BadTime(thirdparty.dns.exception.DNSException):

    """The current time is not within the TSIG's validity time."""


class BadSignature(thirdparty.dns.exception.DNSException):

    """The TSIG signature fails to verify."""


class PeerError(thirdparty.dns.exception.DNSException):

    """Base class for all TSIG errors generated by the remote peer"""


class PeerBadKey(PeerError):

    """The peer didn't know the key we used"""


class PeerBadSignature(PeerError):

    """The peer didn't like the signature we sent"""


class PeerBadTime(PeerError):

    """The peer didn't like the time we sent"""


class PeerBadTruncation(PeerError):

    """The peer didn't like amount of truncation in the TSIG we sent"""

# TSIG Algorithms

HMAC_MD5 = thirdparty.dns.name.from_text("HMAC-MD5.SIG-ALG.REG.INT")
HMAC_SHA1 = thirdparty.dns.name.from_text("hmac-sha1")
HMAC_SHA224 = thirdparty.dns.name.from_text("hmac-sha224")
HMAC_SHA256 = thirdparty.dns.name.from_text("hmac-sha256")
HMAC_SHA384 = thirdparty.dns.name.from_text("hmac-sha384")
HMAC_SHA512 = thirdparty.dns.name.from_text("hmac-sha512")

_hashes = {
    HMAC_SHA224: hashlib.sha224,
    HMAC_SHA256: hashlib.sha256,
    HMAC_SHA384: hashlib.sha384,
    HMAC_SHA512: hashlib.sha512,
    HMAC_SHA1: hashlib.sha1,
    HMAC_MD5: hashlib.md5,
}

default_algorithm = HMAC_MD5

BADSIG = 16
BADKEY = 17
BADTIME = 18
BADTRUNC = 22


def sign(wire, keyname, secret, time, fudge, original_id, error,
         other_data, request_mac, ctx=None, multi=False, first=True,
         algorithm=default_algorithm):
    """Return a (tsig_rdata, mac, ctx) tuple containing the HMAC TSIG rdata
    for the input parameters, the HMAC MAC calculated by applying the
    TSIG signature algorithm, and the TSIG digest context.
    @rtype: (string, string, hmac.HMAC object)
    @raises ValueError: I{other_data} is too long
    @raises NotImplementedError: I{algorithm} is not supported
    """

    if isinstance(other_data, str):
        other_data = other_data.encode()
    (algorithm_name, digestmod) = get_algorithm(algorithm)
    if first:
        ctx = hmac.new(secret, digestmod=digestmod)
        ml = len(request_mac)
        if ml > 0:
            ctx.update(struct.pack('!H', ml))
            ctx.update(request_mac)
    id = struct.pack('!H', original_id)
    ctx.update(id)
    ctx.update(wire[2:])
    if first:
        ctx.update(keyname.to_digestable())
        ctx.update(struct.pack('!H', thirdparty.dns.rdataclass.ANY))
        ctx.update(struct.pack('!I', 0))
    upper_time = (time >> 32) & 0xffff
    lower_time = time & 0xffffffff
    time_mac = struct.pack('!HIH', upper_time, lower_time, fudge)
    pre_mac = algorithm_name + time_mac
    ol = len(other_data)
    if ol > 65535:
        raise ValueError('TSIG Other Data is > 65535 bytes')
    post_mac = struct.pack('!HH', error, ol) + other_data
    if first:
        ctx.update(pre_mac)
        ctx.update(post_mac)
    else:
        ctx.update(time_mac)
    mac = ctx.digest()
    mpack = struct.pack('!H', len(mac))
    tsig_rdata = pre_mac + mpack + mac + id + post_mac
    if multi:
        ctx = hmac.new(secret, digestmod=digestmod)
        ml = len(mac)
        ctx.update(struct.pack('!H', ml))
        ctx.update(mac)
    else:
        ctx = None
    return (tsig_rdata, mac, ctx)


def hmac_md5(wire, keyname, secret, time, fudge, original_id, error,
             other_data, request_mac, ctx=None, multi=False, first=True,
             algorithm=default_algorithm):
    return sign(wire, keyname, secret, time, fudge, original_id, error,
                other_data, request_mac, ctx, multi, first, algorithm)


def validate(wire, keyname, secret, now, request_mac, tsig_start, tsig_rdata,
             tsig_rdlen, ctx=None, multi=False, first=True):
    """Validate the specified TSIG rdata against the other input parameters.
    @raises FormError: The TSIG is badly formed.
    @raises BadTime: There is too much time skew between the client and the
    server.
    @raises BadSignature: The TSIG signature did not validate
    @rtype: hmac.HMAC object"""

    (adcount,) = struct.unpack("!H", wire[10:12])
    if adcount == 0:
        raise thirdparty.dns.exception.FormError
    adcount -= 1
    new_wire = wire[0:10] + struct.pack("!H", adcount) + wire[12:tsig_start]
    current = tsig_rdata
    (aname, used) = thirdparty.dns.name.from_wire(wire, current)
    current = current + used
    (upper_time, lower_time, fudge, mac_size) = \
        struct.unpack("!HIHH", wire[current:current + 10])
    time = (upper_time << 32) + lower_time
    current += 10
    mac = wire[current:current + mac_size]
    current += mac_size
    (original_id, error, other_size) = \
        struct.unpack("!HHH", wire[current:current + 6])
    current += 6
    other_data = wire[current:current + other_size]
    current += other_size
    if current != tsig_rdata + tsig_rdlen:
        raise thirdparty.dns.exception.FormError
    if error != 0:
        if error == BADSIG:
            raise PeerBadSignature
        elif error == BADKEY:
            raise PeerBadKey
        elif error == BADTIME:
            raise PeerBadTime
        elif error == BADTRUNC:
            raise PeerBadTruncation
        else:
            raise PeerError('unknown TSIG error code %d' % error)
    time_low = time - fudge
    time_high = time + fudge
    if now < time_low or now > time_high:
        raise BadTime
    (junk, our_mac, ctx) = sign(new_wire, keyname, secret, time, fudge,
                                original_id, error, other_data,
                                request_mac, ctx, multi, first, aname)
    if our_mac != mac:
        raise BadSignature
    return ctx


def get_algorithm(algorithm):
    """Returns the wire format string and the hash module to use for the
    specified TSIG algorithm
    @rtype: (string, hash constructor)
    @raises NotImplementedError: I{algorithm} is not supported
    """

    if isinstance(algorithm, str):
        algorithm = thirdparty.dns.name.from_text(algorithm)

    try:
        return (algorithm.to_digestable(), _hashes[algorithm])
    except KeyError:
        raise NotImplementedError("TSIG algorithm " + str(algorithm) +
                                  " is not supported")


def get_algorithm_and_mac(wire, tsig_rdata, tsig_rdlen):
    """Return the tsig algorithm for the specified tsig_rdata
    @raises FormError: The TSIG is badly formed.
    """
    current = tsig_rdata
    (aname, used) = thirdparty.dns.name.from_wire(wire, current)
    current = current + used
    (upper_time, lower_time, fudge, mac_size) = \
        struct.unpack("!HIHH", wire[current:current + 10])
    current += 10
    mac = wire[current:current + mac_size]
    current += mac_size
    if current > tsig_rdata + tsig_rdlen:
        raise thirdparty.dns.exception.FormError
    return (aname, mac)
# ------------------------------------
# URL Template Helpers
# ------------------------------------

def decode_id32_to_int(id32_str):
    """
    Decode a base32hex string (no padding, per spec §5.3.3) to an integer.

    Base32hex uses alphabet 0-9, A-V (RFC 4648 §7).
    Examples: '04' -> 1,  '08' -> 2,  '0C' -> 3,  '0G' -> 4
    """
    alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUV'
    id32_str = id32_str.upper()
    n_chars = len(id32_str)
    value = 0
    for c in id32_str:
        value = value * 32 + alphabet.index(c)
    # Strip trailing padding bits that were added during encoding.
    # Encoding pads the last group to 5 bits; we strip those extra bits here.
    n_bits = 5 * n_chars
    padding_bits = n_bits % 8
    if padding_bits:
        value >>= (8 - padding_bits)
    return value


def id32_no_strip(entry_id_int):
    """
    Encode an integer as base32hex WITHOUT stripping leading zero bytes.

    The spec (conform-entry-id-must-be-converted) requires leading zeros to be
    stripped. This helper deliberately omits that step, producing the 'wrong'
    encoding used in negative tests that verify clients strip leading zeros.
    Example: integer 1 -> big-endian [0x00, 0x00, 0x00, 0x01] -> '0000008'
             (correct encoding strips to [0x01] -> '04')
    """
    # Always use 4 bytes (big-endian 32-bit), no stripping
    b = entry_id_int.to_bytes(4, 'big')
    alphabet = '0123456789ABCDEFGHIJKLMNOPQRSTUV'
    result = ''
    bits = 0
    num_bits = 0
    for byte in b:
        bits = (bits << 8) | byte
        num_bits += 8
        while num_bits >= 5:
            num_bits -= 5
            result += alphabet[(bits >> num_bits) & 0x1F]
    if num_bits > 0:
        result += alphabet[(bits << (5 - num_bits)) & 0x1F]
    return result
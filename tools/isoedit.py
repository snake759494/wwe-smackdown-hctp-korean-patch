"""ISO9660 + UDF 브리지에서 파일 위치·크기 바꾸기 (데이터는 호출자가 씀)."""
import struct, os, sys
sys.path.insert(0, os.path.dirname(__file__)); import iso
SEC = 2048
UDF_PART = 272
FE_RANGE = range(270, 396)
def _crc16(data):
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else crc << 1
            crc &= 0xffff
    return crc
def _fix_tag(buf, off, body_len):
    struct.pack_into('<H', buf, off + 8, _crc16(bytes(buf[off + 16:off + 16 + body_len])))
    struct.pack_into('<H', buf, off + 10, body_len)
    buf[off + 4] = sum(buf[off + i] for i in range(16) if i != 4) & 0xff
def _both(v): return struct.pack('<I', v) + struct.pack('>I', v)
def relocate(f, isop, path, new_lba, new_size):
    ent = {p: (l, s, r) for p, l, s, r in iso.walk(isop)}
    old, osz, rec = ent[path]
    f.seek(rec + 2); f.write(_both(new_lba) + _both(new_size))
    for lba in FE_RANGE:
        f.seek(lba * SEC); e = bytearray(f.read(SEC))
        if struct.unpack_from('<H', e, 0)[0] != 261: continue
        l_ea, l_ad = struct.unpack_from('<II', e, 168)
        ad = 176 + l_ea
        if l_ad < 8: continue
        if struct.unpack_from('<I', e, ad + 4)[0] + UDF_PART != old: continue
        ads = []; rem = new_size; p0 = new_lba - UDF_PART
        while True:
            n = min(rem, 0x3FFFF800); ads.append(struct.pack('<II', n, p0)); rem -= n; p0 += n // SEC
            if rem <= 0: break
        e[ad:ad + l_ad] = bytes(l_ad); e[ad:ad + len(ads) * 8] = b''.join(ads)
        struct.pack_into('<I', e, 172, len(ads) * 8)
        struct.pack_into('<Q', e, 56, new_size)
        struct.pack_into('<Q', e, 64, (new_size + SEC - 1) // SEC)
        _fix_tag(e, 0, 176 + l_ea + len(ads) * 8 - 16)
        f.seek(lba * SEC); f.write(e)
        return
    raise KeyError('UDF FE not found: ' + path)
def set_volume_size(f, nsec):
    f.seek(16 * SEC); p = bytearray(f.read(SEC)); p[80:88] = _both(nsec); f.seek(16 * SEC); f.write(p)
    for lba in (34, 50):
        f.seek(lba * SEC); e = bytearray(f.read(SEC))
        if struct.unpack_from('<H', e, 0)[0] == 5:
            struct.pack_into('<I', e, 192, nsec - 1 - UDF_PART)
            _fix_tag(e, 0, struct.unpack_from('<H', e, 10)[0])
            f.seek(lba * SEC); f.write(e)

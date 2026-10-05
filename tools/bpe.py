"""Yukes PAC BPE format"""
import struct

def bpe_decode(d):
    assert d[:4] == b'BPE '
    _, csz, usz = struct.unpack_from('<III', d, 4)
    p = 16; end = 16 + csz; out = bytearray()
    while p < end and len(out) < usz:
        left = list(range(256)); right = [0] * 256
        c = 0
        while True:
            cnt = d[p]; p += 1
            if cnt > 127:
                c += cnt - 127; cnt = 0
            if c == 256: break
            for _ in range(cnt + 1):
                left[c] = d[p]; p += 1
                if left[c] != c:
                    right[c] = d[p]; p += 1
                c += 1
            if c == 256: break
        size = d[p] | d[p + 1] << 8; p += 2
        stack = []
        blk = d[p:p + size]; p += size
        for ch in blk:
            stack.append(ch)
            while stack:
                x = stack.pop()
                if left[x] == x: out.append(x)
                else:
                    stack.append(right[x]); stack.append(left[x])
    return bytes(out)

def pac_entries(d):
    """'PAC ' 묶음 → [(id, bytes)]"""
    assert d[:4] == b'PAC '
    n = struct.unpack_from('<I', d, 4)[0]
    base = 8 + n * 8
    res = []
    for i in range(n):
        e = d[8 + i * 8: 16 + i * 8]
        id_ = e[0] | e[1] << 8; off = e[2] | e[3] << 8 | e[4] << 16; sz = e[5] | e[6] << 8 | e[7] << 16
        res.append((id_, d[base + off: base + off + sz]))
    return res

def unpack(b):
    return bpe_decode(b) if b[:4] == b'BPE ' else b

def dpac_dir(d, rec=False):
    """DPAC -> [(path, offset, size)] ; offset = 0x4000 + sector*0x800"""
    assert d[:4] == b'DPAC'
    n = struct.unpack_from('<I', d, 4)[0]
    raw = []
    for k in range(n):
        p = 0x800 + k * 8
        name = d[p:p + 4]
        if name == bytes(4): break
        a, b = struct.unpack_from('<HH', d, p + 4)
        raw.append((name.decode('latin1').strip(), a, b))
    ents = []; grp = [raw[0][0]]
    for k in range(1, len(raw)):
        nm, a, b = raw[k]
        if k + 1 < len(raw) and raw[k + 1][1] == b and a < 0x40 and b != a:
            grp = [raw[0][0], nm]; continue
        ents.append(['/'.join(grp + [nm]), 0x4000 + a * 0x800, 0, 0x800 + k * 8])
    offs = sorted(set(e[1] for e in ents)) + [len(d)]
    for e in ents:
        e[2] = offs[offs.index(e[1]) + 1] - e[1]
    return [tuple(e[:3]) for e in ents] if not rec else [tuple(e) for e in ents]


def bpe_store(raw, block=4000):
    """무압축 BPE (모든 코드 리터럴)."""
    out = bytearray()
    for i in range(0, len(raw), block):
        blk = raw[i:i + block]
        out += bytes([0xFF, 0x80, 0xFE]) + struct.pack('<H', len(blk)) + blk
    return b'BPE ' + struct.pack('<III', 0x100, len(out), len(raw)) + bytes(out)


def bpe_compress(raw, block=4000):
    """Gage BPE 압축 (원본과 같은 형식)."""
    out = bytearray()
    for i in range(0, len(raw), block):
        out += _bpe_block(bytearray(raw[i:i + block]))
    return b'BPE ' + struct.pack('<III', 0x100, len(out), len(raw)) + bytes(out)


def _bpe_block(buf):
    from collections import Counter
    left = list(range(256)); right = [0] * 256
    used = set(buf)
    free = [c for c in range(255, -1, -1) if c not in used]
    while free and len(buf) > 2:
        cnt = Counter(zip(buf, buf[1:]))
        (a, b), n = cnt.most_common(1)[0]
        if n < 4: break
        code = free.pop(0)
        nb = bytearray(); j = 0; L = len(buf)
        while j < L:
            if j + 1 < L and buf[j] == a and buf[j + 1] == b:
                nb.append(code); j += 2
            else:
                nb.append(buf[j]); j += 1
        buf = nb; left[code] = a; right[code] = b
    # 짝 표 기록: 디코더와 같은 규칙
    out = bytearray(); c = 0
    def entry(q):
        out.append(left[q])
        if left[q] != q: out.append(right[q])
    while c < 256:
        if left[c] == c:
            r = 0
            while c + r < 256 and left[c + r] == c + r and r < 128: r += 1
            out.append(127 + r); c += r
            if c == 256: break
            entry(c); c += 1
            continue
        k = 0
        while c + k < 256 and k < 128:
            if left[c + k] == c + k and (c + k + 1 >= 256 or left[c + k + 1] == c + k + 1): break
            k += 1
        out.append(k - 1)
        for q in range(c, c + k): entry(q)
        c += k
    out += struct.pack('<H', len(buf)) + buf
    return bytes(out)


def pac_build(ents, align=16):
    """[(id, bytes)] → 'PAC ' 묶음."""
    n = len(ents); base = 8 + n * 8
    hdr = bytearray(b'PAC ' + struct.pack('<I', n)); body = bytearray(); pos = base
    for i, b in ents:
        pad = (-pos) % align
        body += bytes(pad); pos += pad
        off = pos - base
        hdr += struct.pack('<H', i) + off.to_bytes(3, 'little') + len(b).to_bytes(3, 'little')
        body += b; pos += len(b)
    pad = (-pos) % 16
    return bytes(hdr + body + bytes(pad))


def dpac_replace(d, path, new):
    """DPAC 항목 하나를 파일 끝(0x800 정렬)에 새로 두고 디렉터리 갱신."""
    d = bytearray(d)
    ent = [e for e in dpac_dir(d, True) if e[0] == path]
    assert len(ent) == 1, path
    _, off, sz, recpos = ent[0]
    if len(new) <= sz:
        d[off:off + sz] = new + bytes(sz - len(new))
        struct.pack_into('<H', d, recpos + 6, (len(new) + 255) // 256)
        return bytes(d)
    pos = (len(d) + 0x7ff) & ~0x7ff
    d += bytes(pos - len(d)) + new
    d += bytes((-len(d)) % 0x800)
    sec = (pos - 0x4000) // 0x800
    assert sec < 0x10000
    struct.pack_into('<HH', d, recpos + 4, sec, (len(new) + 255) // 256)
    return bytes(d)


def replace_leaves(b, repl, path=()):
    """BPE/PAC 를 재귀로 풀어 repl{경로튜플: 새바이트} 를 바꾸고 같은 구조로 다시 묶는다."""
    if path in repl: return repl[path]
    if not any(k[:len(path)] == path and len(k) > len(path) for k in repl): return b
    comp = b[:4] == b'BPE '
    u = bpe_decode(b) if comp else b
    assert u[:4] == b'PAC ', path
    ents = [(i, replace_leaves(x, repl, path + (i,))) for i, x in pac_entries(u)]
    nb = pac_build(ents)
    return bpe_compress(nb) if comp else nb

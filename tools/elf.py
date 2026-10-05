import struct
class Elf:
    def __init__(s, path):
        s.d = d = open(path, 'rb').read()
        s.phoff, s.shoff = struct.unpack_from('<II', d, 0x1c)
        s.phnum, = struct.unpack_from('<H', d, 0x2c); s.shnum, s.shstrndx = struct.unpack_from('<HH', d, 0x30)
        s.ph = [struct.unpack_from('<8I', d, s.phoff + i * 32) for i in range(s.phnum)]
        s.sh = [struct.unpack_from('<10I', d, s.shoff + i * 40) for i in range(s.shnum)]
        st = s.sh[s.shstrndx]
        s.secs = {}
        for h in s.sh:
            n = d[st[4] + h[0]:d.index(b'\0', st[4] + h[0])].decode()
            s.secs[n] = h
    def syms(s):
        if '.symtab' not in s.secs: return []
        h = s.secs['.symtab']; strh = s.sh[h[6]]
        out = []
        for i in range(h[5] // 16):
            nm, val, sz, info, oth, shn = struct.unpack_from('<IIIBBH', s.d, h[4] + i * 16)
            out.append((s.d[strh[4] + nm:s.d.index(b'\0', strh[4] + nm)].decode('latin1'), val, sz, info))
        return out
    def v2o(s, va):
        for p in s.ph:
            if p[0] == 1 and p[3] <= va < p[3] + p[4]: return va - p[3] + p[1]
    def o2v(s, off):
        for p in s.ph:
            if p[0] == 1 and p[1] <= off < p[1] + p[4]: return off - p[1] + p[3]

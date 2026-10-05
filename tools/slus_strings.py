"""SLUS_207.87 의 문자열과 참조(데이터 포인터, 코드 lui/addiu) 추출 → work/slus_strings.json"""
import struct, re, json, os, sys
from elf import Elf

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
CODE = [(0x100000, 0x4096D4), (0x479380, 0x47A94C)]
DATA = [(0x4096D4, 0x479380), (0x47A94C, 0x489880)]


def in_ranges(v, rr): return any(a <= v < b for a, b in rr)


def scan(path=os.path.join(ROOT, 'work', 'ext', 'SLUS_207.87')):
    e = Elf(path); d = e.d
    o2v = lambda o: o - 0x80 + 0x100000
    v2o = lambda v: v - 0x100000 + 0x80
    # 1) 문자열 후보
    strs = {}
    for a, b in DATA:
        blob = d[v2o(a):v2o(b)]
        for m in re.finditer(rb'(?<=\x00)[\x09\x0a\x20-\x7e]+\x00', blob):
            va = a + m.start()
            strs[va] = m.group()[:-1]
    # 2) 데이터 포인터
    dref = {}
    for a, b in DATA:
        for va in range(a & ~3, b, 4):
            w = struct.unpack_from('<I', d, v2o(va))[0]
            if a <= w < 0x489880 and in_ranges(w, DATA):
                dref.setdefault(w, []).append(va)
    # 3) 코드 lui/addiu(ori) 쌍
    cref = {}
    for a, b in CODE:
        n = (b - a) // 4
        words = struct.unpack_from('<%dI' % n, d, v2o(a))
        for i, w in enumerate(words):
            if w >> 26 != 0xF: continue
            r = (w >> 16) & 31; hi = w & 0xFFFF
            for j in range(i + 1, min(n, i + 48)):
                x = words[j]; op = x >> 26
                rs = (x >> 21) & 31; rt = (x >> 16) & 31
                if op in (9, 13) and rs == r:            # addiu / ori
                    imm = x & 0xFFFF
                    v = (hi << 16) + (imm - 0x10000 if (op == 9 and imm & 0x8000) else imm)
                    if in_ranges(v, DATA): cref.setdefault(v, []).append((a + i * 4, a + j * 4))
                    if rt == r: break
                    continue
                if op in (32, 33, 35, 36, 37, 40, 41, 43, 55, 63) and rs == r:   # 메모리 접근 base
                    if op in (32, 33, 35, 36, 37, 55) and rt == r: break
                    continue
                # r 을 덮어쓰는 명령이면 중단
                if op == 0:
                    rd = (x >> 11) & 31
                    if rd == r and (x & 0x3F) not in (8, 9, 0x18, 0x19, 0x1A, 0x1B): break
                elif op == 0xF and rt == r: break
                elif op in (8, 9, 10, 11, 12, 13, 14, 24, 25, 32, 33, 35, 36, 37, 39, 55, 30) and rt == r: break
                if x == 0x03E00008: break                 # jr ra
    return e, strs, dref, cref


if __name__ == '__main__':
    e, strs, dref, cref = scan()
    keys = sorted(strs)
    out = []
    for k, va in enumerate(keys):
        s = strs[va]
        end = va + len(s) + 1
        # 덮어쓸 수 있는 끝: 다음 문자열/참조 주소 전까지의 0 영역
        nxt = keys[k + 1] if k + 1 < len(keys) else end
        lim = end
        dd = e.d
        while lim < nxt and dd[lim - 0x100000 + 0x80] == 0 and lim not in dref and lim not in cref: lim += 1
        inner_refs = sorted(v for v in list(dref) + list(cref) if va < v < end)
        out.append(dict(va=va, text=s.decode('latin1'), span=lim - va, data=dref.get(va, []),
                        code=cref.get(va, []), inner=inner_refs))
    json.dump(out, open(os.path.join(ROOT, 'work', 'slus_strings.json'), 'w'), indent=0)
    nref = sum(1 for o in out if o['data'] or o['code'])
    print(len(out), '개, 참조 있음', nref)

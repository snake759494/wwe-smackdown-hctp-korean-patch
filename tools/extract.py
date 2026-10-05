"""번역 대상 추출 → work/src/*.json (주입 정보 포함) + work/batches/*.json (번역 묶음)"""
import os, re, json, struct, sys
import bpe

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
EXT = os.path.join(ROOT, 'work', 'ext')
SRC = os.path.join(ROOT, 'work', 'src'); os.makedirs(SRC, exist_ok=True)
BAT = os.path.join(ROOT, 'work', 'batches'); os.makedirs(BAT, exist_ok=True)


def width(s):
    """대략 화면 폭(대문자=1, 그 외 ASCII=0.75, 한글=1)."""
    w = 0
    for c in s:
        if '가' <= c <= '힣': w += 1
        elif c.isupper() or c in 'MW@%&': w += 1
        elif c == '\n': continue
        else: w += 0.75
    return round(w, 1)


# ---------------- SLUS ----------------
SKIP_RX = re.compile(r'(/|\\|\.(afs|pac|bin|irx|sfd|h)\b|%0|%[0-9]*[fxX]|[Ee]rr|ERR|sce[A-Z]|\bMc |CMc|::|TLB|DMA|Ver\.|Build:|^[a-z0-9_]+$|^[A-Z0-9_]+[0-9][A-Z0-9_]*$|^\W*$)')
FORCE = {0x457a70, 0x457a90, 0x457ab0, 0x457ad0, 0x457af0, 0x457db0, 0x458028, 0x458030, 0x458048, 0x458050,
         0x458058, 0x458060, 0x458068, 0x458070, 0x458078, 0x459318, 0x45a6e8, 0x45a6f0, 0x4583f8, 0x458458,
         0x458478, 0x4584d8, 0x458578, 0x458588, 0x4588e0, 0x458a30, 0x458a38, 0x458a40, 0x458a48, 0x45a0f0,
         0x45a0f8, 0x458a50, 0x458aa0, 0x458c98, 0x458f98, 0x458fa8, 0x458fb0, 0x459000, 0x459060, 0x459200,
         0x459338, 0x459340, 0x45a460, 0x45a468, 0x45a470, 0x45a478, 0x45a4b0, 0x45a4b8, 0x45a500, 0x45a508,
         0x45a510, 0x45a518, 0x45a520, 0x45a528, 0x45a530, 0x45a538, 0x45a570, 0x45a600, 0x45a648, 0x45ff10,
         0x4600a0, 0x4607b0, 0x46c970}
def slus_items():
    o = json.load(open(os.path.join(ROOT, 'work', 'slus_strings.json')))
    out = []
    for x in o:
        va = x['va']; t = x['text']
        if not (0x4574A0 <= va < 0x471000): continue
        if not (x['data'] or x['code']): continue
        if SKIP_RX.search(t) and va not in FORCE: continue
        if not re.search(r'[A-Za-z]{2}', t): continue
        out.append(dict(id='s%x' % va, en=t, va=va, span=x['span'], data=x['data'], code=x['code'],
                        w=width(t), kind=('D' if x['data'] else '') + ('C' if x['code'] else '')))
    return out


# ---------------- MISC STDE/TTDE ----------------
def misc_blocks():
    d = open(os.path.join(EXT, 'MISC.PAC'), 'rb').read()
    res = {}
    for name in ('STDE', 'TTDE'):
        rec = d.index(name.encode(), 0x800, 0x4000)
        a, b = struct.unpack_from('<HH', d, rec + 4)
        off = 0x4000 + a * 0x800; p = name
        n = struct.unpack_from('<H', d, off)[0]; q = off + 2; recs = []
        for k in range(n):
            i, l = struct.unpack_from('<HH', d, q)
            recs.append((i, d[q + 4:q + 4 + l].rstrip(b'\0').decode('latin1'))); q += 4 + l
        res[name] = dict(path=p, off=off, recs=recs)
    return res


# ---------------- PAC 고정 칸 ----------------
def leaf(fn, dp, key=None):
    d = open(os.path.join(EXT, fn), 'rb').read()
    e = [x for x in bpe.dpac_dir(d) if x[0] == dp][0]
    b = d[e[1]:e[1] + e[2]]
    if key is not None: b = bpe.unpack(dict(bpe.pac_entries(b))[key])
    return b


def fields(b, base=0, minlen=2):
    """0으로 채운 고정 칸 안의 문자열: (위치, 문자열, 칸 크기)"""
    out = []
    for m in re.finditer(rb'(?<=\x00)[A-Za-z0-9\'"!][\x20-\x7e]*\x00', b):
        s = m.group()[:-1]
        if len(s) < minlen or not re.search(rb'[A-Za-z]{2}', s): continue
        st = m.start(); e = m.end()
        while e < len(b) and b[e] == 0: e += 1
        out.append((base + st, s.decode('latin1'), e - st))
    return out


PAC_TEXT = [  # (이름, 파일, dpac 경로, PAC 키 또는 None)
    ('CHSL', 'MENU.PAC', 'MENU/CHSL', 0), ('CH31', 'MENU.PAC', 'MENU/CH31', 0), ('CHEU', 'MENU.PAC', 'MENU/CHEU', 0),
    ('COST', 'MENU.PAC', 'MENU/COST', 0), ('CANAME', 'CA.PAC', 'CASM/CABI/NAME', None),
    ('SMDT0', 'STABLE.PAC', 'STBL/SMDT', 0), ('SMDT1', 'STABLE.PAC', 'STBL/SMDT', 1),
] + [('LIST%d' % k, 'MOVES.PAC', 'MOVE/LIST', k) for k in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9)]


def pac_items():
    out = []
    for nm, fn, dp, key in PAC_TEXT:
        try: b = leaf(fn, dp, key)
        except Exception as e:
            print('skip', nm, e); continue
        for pos, s, cap in fields(b):
            out.append(dict(id='%s:%x' % (nm, pos), en=s, file=fn, dpac=dp, key=key, pos=pos, maxb=cap - 1, w=width(s)))
    # 선수 마스터(M.PAC MOT/CHAR/ALL): 이름 278(22) / 별명 300(24) / 호칭 324(23)
    d = open(os.path.join(EXT, 'M.PAC'), 'rb').read()
    e = [x for x in bpe.dpac_dir(d) if x[0] == 'MOT/CHAR/ALL'][0]
    blob = d[e[1]:e[1] + e[2]]
    for key, raw in bpe.pac_entries(blob):
        u = bpe.unpack(raw)
        for pos, cap in ((278, 22), (300, 24), (324, 23)):
            s = u[pos:pos + cap].split(bytes(1))[0].decode('latin1')
            if len(s) < 2 or not re.search(r'[A-Za-z]{2}', s) or u[pos - 1] != 0: continue
            out.append(dict(id='CHAR%d:%x' % (key, pos), en=s, file='M.PAC', dpac='MOT/CHAR/ALL', key=key, pos=pos,
                            maxb=cap - 1, w=width(s)))
    # WAZA: 16 + 64*n, 이름 칸 = 레코드+16, 32바이트 (공백 채움)
    w = leaf('MOVES.PAC', 'MOVE/WAZA')
    n = struct.unpack_from('<I', w, 4)[0]
    for k in range(n):
        p = 16 + k * 64 + 16
        raw = w[p:p + 32]
        s = raw.split(b'\0')[0].decode('latin1')
        if not re.search(r'[A-Za-z]{2}', s): continue
        out.append(dict(id='WAZA:%d' % k, en=s, file='MOVES.PAC', dpac='MOVE/WAZA', key=None, pos=p, maxb=31, w=width(s), waza=1))
    return out


def batches(items, prefix, size, extra=None):
    """번역 묶음: id, en, 제약, 앞뒤 문맥.  같은 영문은 첫 항목만 (제약은 가장 엄격한 값)."""
    seen = {}
    uniq = []
    for x in items:
        k = x['en']
        if k in seen:
            u = seen[k]
            if x.get('maxb') is not None:
                u['maxb'] = min(u['maxb'], x['maxb']) if u.get('maxb') is not None else x['maxb']
            continue
        u = dict(x); seen[k] = u; uniq.append(u)
    items = uniq
    n = 0
    for i in range(0, len(items), size):
        chunk = items[i:i + size]; arr = []
        for j, x in enumerate(chunk):
            g = i + j
            ctx = [items[g - 1]['en'] if g > 0 else '', items[g + 1]['en'] if g + 1 < len(items) else '']
            it = {'id': x['id'], 'en': x['en']}
            if x.get('maxb') is not None: it['maxb'] = x['maxb']
            if x.get('w') is not None: it['w'] = x['w']
            it['ctx'] = ctx
            if extra: extra(x, it)
            arr.append(it)
        json.dump(arr, open(os.path.join(BAT, '%s_%03d.json' % (prefix, n)), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
        n += 1
    return n


if __name__ == '__main__':
    for f in os.listdir(BAT): os.remove(os.path.join(BAT, f))
    s = slus_items()
    for x in s:
        if x['code'] and not x['data']: x['maxb'] = x['span'] - 1
    json.dump(s, open(os.path.join(SRC, 'slus.json'), 'w'), indent=0)
    print('SLUS', len(s), '묶음', batches(s, 'ui', 150))
    mb = misc_blocks()
    allm = []
    for name, info in mb.items():
        pre = 'st' if name == 'STDE' else 'tt'
        items = [dict(id='%s%d' % (pre, k), en=t, rid=i, w=None) for k, (i, t) in enumerate(info['recs'])]
        json.dump(dict(path=info['path'], recs=[(x['rid'], x['en']) for x in items]), open(os.path.join(SRC, name + '.json'), 'w'), indent=0)
        tr = [x for x in items if x['en'] and re.search(r'[A-Za-z]{2}', x['en']) and all(ord(c) < 0x80 for c in x['en'])]
        print(name, len(items), '번역', len(tr), '묶음', batches(tr, pre, 120))
    p = pac_items()
    json.dump(p, open(os.path.join(SRC, 'pac.json'), 'w'), indent=0)
    print('PAC', len(p), '묶음', batches(p, 'pac', 200))

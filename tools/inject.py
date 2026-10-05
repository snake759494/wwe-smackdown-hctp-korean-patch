"""번역 주입: 실행 파일 문자열, MISC 시즌 대사(STDE/TTDE), PAC 고정 칸 목록."""
import os, json, glob, struct, re
import bpe

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
EXT = os.path.join(ROOT, 'work', 'ext')
SRC = os.path.join(ROOT, 'work', 'src')
BAT = os.path.join(ROOT, 'work', 'batches')
KO = os.path.join(ROOT, 'translation', 'ko')
FIX = os.path.join(ROOT, 'translation', 'fix')
V2O = lambda va: va - 0x100000 + 0x80
REPORT = []


RESOLVED = os.path.join(ROOT, 'translation', 'resolved.json')
RES = json.load(open(RESOLVED, encoding='utf-8')) if os.path.exists(RESOLVED) else None


def _load(prefix):
    if RES is not None: return {}, RES
    """묶음 입력(id→en)과 번역(id→ko)으로 en→ko, id→ko 사전."""
    en2ko = {}; id2ko = {}; id2en = {}
    for f in sorted(glob.glob(os.path.join(BAT, prefix + '_*.json'))):
        for it in json.load(open(f, encoding='utf-8')): id2en[it['id']] = it['en']
    for p in sorted(glob.glob(os.path.join(KO, prefix + '_*.json'))):
        for k, v in json.load(open(p, encoding='utf-8')).items():
            id2ko[k] = v
            if k in id2en: en2ko.setdefault(id2en[k], v)
    for f in sorted(glob.glob(os.path.join(FIX, prefix + '*.json'))):     # 수동 보정 (id 또는 원문 키)
        for k, v in json.load(open(f, encoding='utf-8')).items():
            if k in id2ko or re.fullmatch(r'[a-zA-Z]+[0-9a-f:]*[0-9a-f]+', k): id2ko[k] = v
            else: en2ko[k] = v
    return en2ko, id2ko


def _tr(item, en2ko, id2ko):
    t = id2ko.get(item['id'])
    if t is None: t = en2ko.get(item['en'])
    return t


def all_texts():
    if RES is not None: return list(RES.values())
    out = []
    for f in glob.glob(os.path.join(KO, '*.json')) + glob.glob(os.path.join(FIX, '*.json')):
        out += list(json.load(open(f, encoding='utf-8')).values())
    return out


# ---------------- SLUS ----------------
def slus_plan(cs):
    """→ inplace[(파일오프셋, bytes)], reloc[(bytes, data참조[], code쌍[])]"""
    items = json.load(open(os.path.join(SRC, 'slus.json')))
    en2ko, id2ko = _load('ui')
    allstr = {x['va']: x for x in json.load(open(os.path.join(ROOT, 'work', 'slus_strings.json')))}
    inplace = []; reloc = []; n = 0
    for x in items:
        t = _tr(x, en2ko, id2ko)
        if t is None or t == x['en']: continue
        b = cs.encode(t) + b'\0'
        inner = allstr[x['va']]['inner']
        if len(b) <= x['span'] and not inner:
            inplace.append((V2O(x['va']), b + bytes(x['span'] - len(b)))); n += 1
        elif x['data'] and not x['code']:
            reloc.append((b, x['data'], []))
        elif x['code']:
            reloc.append((b, x['data'], [tuple(p) for p in x['code']]))
        else:
            REPORT.append('SLUS 넘침(처리불가) %s %r' % (x['id'], t))
    return inplace, reloc


def apply_slus(elf, cs, tail_base):
    """elf(bytearray) 수정. tail_base: 새 문자열을 둘 시작 주소. → 새 문자열 영역 bytes"""
    inplace, reloc = slus_plan(cs)
    for off, b in inplace: elf[off:off + len(b)] = b
    # 선수 이름 표 (0x470800~, 48바이트 레코드, 이름 칸 22바이트)
    names = dict((en.decode('latin1'), ko) for en, ko in _name_map())
    for va in range(0x470800, 0x470d40, 0x30):
        o = V2O(va); raw = bytes(elf[o:o + 22]); s = raw.split(bytes(1))[0].decode('latin1')
        if s in names and raw[len(s):] == bytes(22 - len(s)):
            b = cs.encode(names[s]) if isinstance(names[s], str) else names[s]
            if len(b) < 22: elf[o:o + 22] = b + bytes(22 - len(b))
    tail = bytearray(); dedup = {}
    # lui 공유 확인용
    lui_users = {}
    for b, data, code in reloc:
        for lui, add in code: lui_users.setdefault(lui, set()).add(add)
    for b, data, code in reloc:
        if b in dedup: va = dedup[b]
        else:
            va = tail_base + len(tail); dedup[b] = va
            tail += b
            while len(tail) % 4: tail.append(0)
        for d in data: struct.pack_into('<I', elf, V2O(d), va)
        hi = ((va + 0x8000) >> 16) & 0xFFFF; lo = va & 0xFFFF
        for lui, add in code:
            # 같은 lui 를 다른 문자열도 쓰면 lui 를 바꿀 수 없음 → 해당 addiu 를 다른 레지스터로? (드묾) 보고
            others = lui_users.get(lui, set()) - {add}
            w = struct.unpack_from('<I', elf, V2O(lui))[0]
            a = struct.unpack_from('<I', elf, V2O(add))[0]
            if others and (w & 0xFFFF) != hi:
                REPORT.append('lui 공유로 재배치 불가: %x' % add); continue
            struct.pack_into('<I', elf, V2O(lui), (w & 0xFFFF0000) | hi)
            op = a >> 26
            if op == 13:                       # ori → addiu 로 바꿔 부호 있는 하위값 사용
                a = (a & 0x03FFFFFF) | (9 << 26)
            struct.pack_into('<I', elf, V2O(add), (a & 0xFFFF0000) | lo)
    return bytes(tail)


# ---------------- MISC STDE/TTDE ----------------
def misc_block(name, cs):
    info = json.load(open(os.path.join(SRC, name + '.json')))
    pre = 'st' if name == 'STDE' else 'tt'
    en2ko, id2ko = _load(pre)
    out = bytearray(struct.pack('<H', len(info['recs'])))
    for k, (rid, en) in enumerate(info['recs']):
        t = id2ko.get('%s%d' % (pre, k))
        if t is None: t = en2ko.get(en)
        if t is None or not all(ord(c) < 0x80 for c in en):
            b = en.encode('latin1')
        else: b = cs.encode(t)
        b += b'\0'
        b += bytes((-len(b)) % 4)
        out += struct.pack('<HH', rid, len(b)) + b
    return bytes(out)


def misc_replace(d, name, new):
    d = bytearray(d)
    rec = d.index(name.encode(), 0x800, 0x4000)
    pos = (len(d) + 0x7FF) & ~0x7FF
    d += bytes(pos - len(d)) + new
    d += bytes((-len(d)) % 0x800)
    sec = (pos - 0x4000) // 0x800
    assert sec < 0x10000
    struct.pack_into('<HH', d, rec + 4, sec, (len(new) + 255) // 256)
    return bytes(d)


# ---------------- PAC 고정 칸 ----------------
def pac_patches(cs):
    """→ {(파일, dpac, key): [(pos, bytes)]}"""
    items = json.load(open(os.path.join(SRC, 'pac.json')))
    en2ko, id2ko = _load('pac')
    out = {}
    for x in items:
        t = _tr(x, en2ko, id2ko)
        if t is None or t == x['en']: continue
        if os.environ.get('SKIPCHAR') and x['id'].startswith('CHAR'): continue
        b = cs.encode(t)
        if len(b) > x['maxb']:
            REPORT.append('PAC 넘침 %s %r' % (x['id'], t)); continue
        if x.get('waza'):
            fld = b + b'\0' + b' ' * (31 - len(b))
        else:
            fld = b + bytes(x['maxb'] + 1 - len(b))
        out.setdefault((x['file'], x['dpac'], x['key']), []).append((x['pos'], fld))
    return out


def patch_pacs(cs, pacs, read_ext):
    """pacs: 이미 수정된 PAC {파일명: bytes} (폰트 등). → 추가/갱신된 PAC 사전"""
    res = {}
    get = lambda fn: res.get(fn) or pacs.get(fn) or read_ext(fn)
    # MISC
    d = get('MISC.PAC')
    for name in ('STDE', 'TTDE'):
        d = misc_replace(d, name, misc_block(name, cs))
    # 로딩 팁 이미지(무압축 TIM2, 같은 크기로 제자리 교체)
    import tips
    d = bytearray(d); offs = tips.tip_offsets(bytes(d))
    for k in tips.SPEC:
        o = offs[k]; tb = bytes(d[o:o + 0x50000])
        nb = tips.render(k, tb)
        d[o:o + len(nb)] = nb
    d = bytes(d)
    res['MISC.PAC'] = d
    # 고정 칸
    groups = {}
    for (fn, dp, key), lst in pac_patches(cs).items():
        groups.setdefault((fn, dp), {})[key] = lst
    for (fn, dp), keys in groups.items():
        d = get(fn)
        ent = [e for e in bpe.dpac_dir(d) if e[0] == dp][0]
        blob = d[ent[1]:ent[1] + ent[2]]
        repl = {}
        for key, lst in keys.items():
            if key is None:
                raw = bytearray(blob)
                for pos, b in lst: raw[pos:pos + len(b)] = b
                blob = bytes(raw)
            else:
                leafb = bytearray(bpe.unpack(dict(bpe.pac_entries(blob))[key]))
                for pos, b in lst: leafb[pos:pos + len(b)] = b
                repl[(key,)] = bpe.bpe_compress(bytes(leafb)) if dict(bpe.pac_entries(blob))[key][:4] == b'BPE ' else bytes(leafb)
        if repl: blob = bpe.replace_leaves(blob, repl)
        res[fn] = bpe.dpac_replace(d, dp, blob)
    return res


def _name_map():
    """(영문 bytes, 한글 str): 선수 마스터(CHAR) 항목 기준."""
    src = json.load(open(os.path.join(SRC, 'pac.json')))
    e2k, i2k = _load('pac')
    out = {}
    for x in src:
        if not x['id'].startswith('CHAR') or x['en'].startswith('Moves Set'): continue
        t = _tr(x, e2k, i2k)
        if t and t != x['en']: out.setdefault(x['en'].encode('latin1'), t)
    return list(out.items())


def name_pairs(cs):
    """표시 시점 치환용 (영문, 한글) 바이트 쌍: 선수 이름·별칭."""
    return [(en, cs.encode(ko)) for en, ko in _name_map()]

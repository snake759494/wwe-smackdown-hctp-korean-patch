"""게임 안 모든 폰트(TIM2 + YCHR) 찾기/분석."""
import bpe, struct, os, json
from tim2 import pictures
EXT = os.path.join(os.path.dirname(__file__), '..', 'work', 'ext')
SIZE = {}  # YCHR 크기 인덱스 → 픽셀 (0x45cde0 표) : 실행 파일에서 읽음
def size_table():
    from elf import Elf
    e = Elf(os.path.join(EXT, 'SLUS_207.87')); o = e.v2o(0x45cde0)
    return list(struct.unpack_from('<16I', e.d, o))
def ychr(b):
    tag = b[:4]; wi, hi, n = struct.unpack_from('<HHH', b, 4)
    cells = [struct.unpack_from('<4H', b, 10 + i * 8) for i in range(n)]
    p = 10 + n * 8; m = struct.unpack_from('<H', b, p)[0]
    kern = [b[p + 2 + i * 4:p + 6 + i * 4] for i in range(m)]
    return dict(tag=tag, wi=wi, hi=hi, cells=cells, kern=kern, tail=b[p + 2 + m * 4:])
def ychr_bytes(y):
    out = bytearray(y['tag'] + struct.pack('<HHH', y['wi'], y['hi'], len(y['cells'])))
    for c in y['cells']: out += struct.pack('<4H', *c)
    out += struct.pack('<H', len(y['kern'])) + b''.join(y['kern']) + y['tail']
    return bytes(out)

def leaves(b, path, depth=0):
    """BPE/PAC 를 재귀로 풀어 (경로, 바이트) 나열."""
    if b[:4] == b'BPE ': b = bpe.bpe_decode(b)
    if b[:4] == b'PAC ' and depth < 6:
        try: ents = bpe.pac_entries(b)
        except Exception: ents = []
        if ents:
            for i, x in ents: yield from leaves(x, path + [i], depth + 1)
            return
    yield path, b

FONT_SRC = [('MENU.PAC', 'MENU/FNT2'), ('GAME2D.PAC', 'GA2D/DALL'), ('GAME2D.PAC', 'GA2D/ED2D/FONT'),
            ('ENTR2D.PAC', None), ('_AUTO.PAC', '')]
def inventory():
    """[(파일, DPAC경로, 하위경로, ychr바이트, 텍스처(TIM2 바이트), 그림번호)]"""
    out = []
    for fn, want in FONT_SRC:
        d = open(os.path.join(EXT, fn), 'rb').read()
        dl = bpe.dpac_dir(d) if d[:4] == b'DPAC' else [('', 0, len(d))]
        for p, off, sz in dl:
            if want is not None and p != want: continue
            if want is None and '/F' not in p: continue
            lv = dict((tuple(k), v) for k, v in leaves(d[off:off + sz], []))
            for k, v in lv.items():
                if v[:4] != b'YCHR': continue
                base = k[:-1] + ((k[-1] // 10) * 10,)
                # 텍스처: base 경로 아래 TIM2 들 (번호순)
                tims = sorted((kk, vv) for kk, vv in lv.items() if vv[:4] == b'TIM2' and kk[:len(base)] == base)
                if not tims:
                    base2 = k[:-1] + (k[-1] - 1,)
                    tims = sorted((kk, vv) for kk, vv in lv.items() if vv[:4] == b'TIM2' and kk[:len(base2)] == base2)
                pic = (k[-1] % 10) - 1
                out.append(dict(file=fn, dpac=p, key=k, ychr=v, tims=tims, pic=pic))
    return out

def pic_pixels(tb, pi):
    p = pictures(tb)[pi]
    cl = tb[p['clut']:p['clut'] + p['clsz']]
    p['alpha'] = [cl[i * 4 + 3] for i in range(p['clc'])]
    im = tb[p['img']:p['img'] + p['imsz']]
    w, h = p['w'], p['h']
    if p['imt'] == 4:
        px = bytearray(w * h)
        for i, b in enumerate(im[:w * h // 2]): px[2 * i] = b & 15; px[2 * i + 1] = b >> 4
    else: px = bytearray(im[:w * h])
    return p, w, h, px

GA, GB = 1, 23          # 24x24 글리프 안 한글 잉크 위/아래 행(대략)
def plan_slot(y, w, h, px, ref=None, alpha=None, free_high=False, G=24, yalign=1):
    """슬롯 계산: (ux,uy) 업로드 위치, 창(wx,wy,ww,wh), 표시(dw,dh)."""
    cells = y['cells']
    H = cells[0x48]
    cx, cy, cw, chh = H
    if ref is None:
        op = [a > 8 for a in alpha] if alpha else [i > 0 for i in range(256)]
        rows = [r for r in range(cy, cy + chh) if any(op[px[r * w + c]] for c in range(cx, min(w, cx + cw)))]
        if not rows: return 'noink'
        ct, cb = rows[0] - cy, rows[-1] - cy + 1
    else:
        k = chh / ref[2]; ct, cb = ref[0] * k, ref[1] * k
    capH = cb - ct
    ga, gb = GA * G / 24, GB * G / 24
    s = 1.12 * capH / (gb - ga)                    # 표시단위/텍셀
    t = (ct + capH / 2) / s - (ga + gb) / 2         # 창 위쪽이 업로드 위쪽보다 t 텍셀 위
    wh = round(chh / s); ww = G
    t = round(t)
    # 글리프(0..G 행) 전체가 창 안에 들어오게: 0 <= t <= wh - G (아래 잘림 방지, 위로 약간 이동 허용)
    if wh < G + 1:
        wh = G + 1; s = chh / wh
    t = max(0, min(t, wh - G - 1))
    top = min(0, -t); bot = max(G, -t + wh)       # 업로드 기준 필요한 행 범위
    need_h = bot - top + 2; need_w = G + 2
    used = bytearray(w * h)
    hi = bytearray(w * h)
    if free_high:
        for (x0, y0, cw2, ch2) in cells[0x80:]:
            for r in range(max(0, y0), min(h, y0 + ch2)):
                for c in range(max(0, x0), min(w, x0 + cw2)): hi[r * w + c] = 1
    for (x0, y0, cw2, ch2) in (cells[:0x80] if free_high else cells):
        if cw2 == 0 or ch2 == 0: continue
        for r in range(max(0, y0 - 1), min(h, y0 + ch2 + 1)):
            for c in range(max(0, x0 - 1), min(w, x0 + cw2 + 1)): used[r * w + c] = 1
    op = [a > 0 for a in alpha] if alpha else [i > 0 for i in range(256)]
    for i in range(w * h):
        if op[px[i]] and not hi[i]: used[i] = 1
    best = None
    for r0 in range(h - need_h, -1, -1):
        for c0 in range(((w - need_w + 1) // 8) * 8 - 1, -1, -8):
            if c0 < 0: continue
            ok = True
            for r in range(r0, r0 + need_h):
                row = used[r * w + c0:r * w + c0 + need_w]
                if any(row): ok = False; break
            if ok and (r0 + 1 - top) % yalign == 0: best = (c0, r0); break
        if best: break
    if not best: return ('nospace', need_w, need_h)
    ux = best[0] + 1; uy = best[1] + 1 - top
    return dict(G=G, rect=(best[0], best[1], need_w, need_h), ux=ux, uy=uy, wx=ux, wy=uy - t, ww=ww, wh=wh, dw=round(ww * s), dh=chh,
                capt=ct, capb=cb, s=s)

SIZES = [16, 32, 64, 128, 256, 512, 1024]
def repack(y, tb, keep, W, H, reserve=None):
    """keep 코드의 글리프만 W x H 새 텍스처에 다시 배치. reserve=(w,h) 오른쪽 아래 빈 칸 확보.
    → (새 YCHR dict, 새 TIM2 바이트)"""
    p, w0, h0, px = pic_pixels(tb, 0)
    tr = p['alpha'].index(0)
    cells = list(y['cells'])
    rects = {}
    for c in keep:
        x, yy, cw, ch = cells[c]
        if cw and ch: rects.setdefault((x, yy, cw, ch), []).append(c)
    order = sorted(rects, key=lambda r: (-r[3], -r[2]))
    newpx = bytearray([tr]) * (W * H)
    rx, ry = (W - reserve[0], H - reserve[1]) if reserve else (W, H)
    cx = cy = 0; rowh = 0; place = {}
    for r in order:
        x, yy, cw, ch = r
        if cx + cw > W:
            cx = 0; cy += rowh + 1; rowh = 0
        if cy + ch > ry and cx + cw > rx:   # 예약 칸과 겹치면 다음 줄
            cx = 0; cy += rowh + 1; rowh = 0
        assert cy + ch <= H, '공간 부족'
        place[r] = (cx, cy)
        for j in range(ch):
            for i in range(cw):
                sx, sy = x + i, yy + j
                if 0 <= sx < w0 and 0 <= sy < h0: newpx[(cy + j) * W + cx + i] = px[sy * w0 + sx]
        cx += cw + 1; rowh = max(rowh, ch)
    newcells = [(0, 0, 0, 0)] * len(cells)
    for c in range(len(cells)):
        x, yy, cw, ch = cells[c]
        if c in keep and cw and ch:
            nx, ny = place[(x, yy, cw, ch)]; newcells[c] = (nx, ny, cw, ch)
    ny = dict(y); ny['cells'] = newcells
    ny['wi'] = SIZES.index(W); ny['hi'] = SIZES.index(H)
    # 커닝 표는 그대로
    # TIM2 다시 쓰기 (그림 1장, 4bpp)
    hdr_off = p['off']; hsz = p['hsz']
    pic = bytearray(tb[hdr_off:hdr_off + hsz])
    img = bytearray(W * H // 2)
    for i in range(0, W * H, 2): img[i // 2] = newpx[i] | (newpx[i + 1] << 4)
    clut = tb[p['clut']:p['clut'] + p['clsz']]
    tot = hsz + len(img) + len(clut)
    struct.pack_into('<III', pic, 0, tot, len(clut), len(img))
    struct.pack_into('<HH', pic, 20, W, H)
    tex0 = struct.unpack_from('<Q', pic, 24)[0]
    tw, th = SIZES.index(W) + 4, SIZES.index(H) + 4
    tex0 = (tex0 & ~((0x3f << 14) | (0xf << 26) | (0xf << 30))) | ((W // 64) << 14) | (tw << 26) | (th << 30)
    struct.pack_into('<Q', pic, 24, tex0)
    head = bytearray(tb[:hdr_off])
    nt = bytes(head) + bytes(pic) + bytes(img) + bytes(clut)
    return ny, nt

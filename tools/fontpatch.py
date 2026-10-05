"""모든 폰트에 한글 슬롯 셀 기록(+필요하면 텍스처 칸 비우기)."""
import struct, os, bpe
from fonts import *
from tim2 import pictures

def _plan(f, ref, yalign=1, forceG=None):
    y = ychr(f['ychr']); tb = f['tims'][min(f['pic'], len(f['tims']) - 1)][1]
    p, w, h, px = pic_pixels(tb, 0)
    r = None
    if f['pic'] > 0:          # 글로/외곽 레이어: 번진 16px 세트
        for hi in (0, 1):
            r = plan_slot(y, w, h, px, ref, p['alpha'], hi, 16)
            if isinstance(r, dict): r['hi'] = hi; r['glow'] = 1; return y, tb, p, w, h, px, r
        return y, tb, p, w, h, px, None
    if forceG:
        for hi in (0, 1):
            r = plan_slot(y, w, h, px, ref, p['alpha'], hi, forceG, yalign)
            if isinstance(r, dict): r['hi'] = hi; return y, tb, p, w, h, px, r
        return y, tb, p, w, h, px, None
    for hi in (0, 1):
        r24 = plan_slot(y, w, h, px, ref, p['alpha'], hi, 24, yalign)
        if isinstance(r24, dict) and r24['s'] >= 0.7: r = r24; break
        r16 = plan_slot(y, w, h, px, ref, p['alpha'], hi, 16, yalign)
        if isinstance(r16, dict): r = r16; break
        if isinstance(r24, dict): r = r24; break
    if r is not None: r['hi'] = hi
    return y, tb, p, w, h, px, r

# (파일, dpac, YCHR키) → (텍스처키, 새 W, 새 H, 예약 칸)
REPACK = {
    ('GAME2D.PAC', 'GA2D/ED2D/FONT', (51,)): ((50, 0), 128, 64, (18, 18)),
    ('_AUTO.PAC', '', (0, 31)): ((0, 30, 0), 256, 256, (26, 41)),
    ('MENU.PAC', 'MENU/FNT2', (31,)): ((30, 0), 256, 256, (26, 41)),
    ('MENU.PAC', 'MENU/FNT2', (41,)): ((40, 0), 256, 128, (18, 34)),
}
KEEP = [c for c in range(1, 0x7f) if c not in (28, 29, 30, 31)]
# 호스트: (id, 강제 G)
HOSTS = {('GAME2D.PAC', 'GA2D/DALL', (0, 41)): (0, None),
         ('MENU.PAC', 'MENU/FNT2', (31,)): (1, 24),
         ('_AUTO.PAC', '', (0, 31)): (1, 24)}
_M = ('MENU.PAC', 'MENU/FNT2', (31,)); _A = ('_AUTO.PAC', '', (0, 31)); _G = ('GAME2D.PAC', 'GA2D/DALL', (0, 41))
GUESTS = {('GAME2D.PAC', 'GA2D/DALL', (0, 51)): _G,
          ('MENU.PAC', 'MENU/FNT2', (11,)): _M, ('MENU.PAC', 'MENU/FNT2', (12,)): _M, ('MENU.PAC', 'MENU/FNT2', (21,)): _M,
          ('_AUTO.PAC', '', (0, 11)): _A, ('_AUTO.PAC', '', (0, 12)): _A}

def patch_fonts():
    """→ {(파일, dpac경로): {키경로: 새바이트}} , 보고서"""
    inv = inventory(); refs = {}; out = {}; rep = []; hostwin = {}
    inv.sort(key=lambda f: 0 if (f['file'], f['dpac'], tuple(f['key'])) in HOSTS else (2 if (f['file'], f['dpac'], tuple(f['key'])) in GUESTS else 1))
    for f in inv:
        rk = (f['file'], f['dpac'], tuple(f['key']))
        if rk in REPACK:
            tk, W, H, res = REPACK[rk]
            tims = dict(f['tims'])
            ny, nt = repack(ychr(f['ychr']), tims[tk], KEEP, W, H, res)
            f['ychr'] = ychr_bytes(ny)
            tims[tk] = nt
            f['tims'] = sorted(tims.items())
            out.setdefault((f['file'], f['dpac']), {})[tk] = nt
    for f in inv:
        key = (f['file'], f['dpac'], f['key'][:-1] + (f['key'][-1] // 10,))
        ref = refs.get(key) if f['pic'] > 0 else None
        fk0 = (f['file'], f['dpac'], tuple(f['key']))
        if fk0 in GUESTS: r = None; y = ychr(f['ychr']); tb = f['tims'][min(f['pic'], len(f['tims']) - 1)][1]; p, w, h, px = pic_pixels(tb, 0)
        else: y, tb, p, w, h, px, r = _plan(f, ref, 4 if fk0 in HOSTS else 1, HOSTS[fk0][1] if fk0 in HOSTS else None)
        cells = y['cells']
        for c in (28, 29, 30, 31): assert cells[c] == (0, 0, 0, 0), (f['dpac'], f['key'], c, cells[c])
        lutsel = 1 if (f['file'], f['dpac'], f['key']) == ('MENU.PAC', 'MENU/FNT2', (1,)) else 0
        H = cells[0x48]
        fk = (f['file'], f['dpac'], tuple(f['key']))
        if r is None and fk in GUESTS and GUESTS[fk] in hostwin:
            # 게스트: 호스트 텍스처 슬롯을 빌려 씀 (호스트가 없을 때는 아래 빈 칸 셀로 대체)
            hux, huy, hW, hH, hG, hid = hostwin[GUESTS[fk]]
            gW, gH = SIZES[y['wi']], SIZES[y['hi']]
            assert (hux * gW) % hW == 0 and (huy * gH) % hH == 0 and (hG * gW) % hW == 0 and (hG * gH) % hH == 0, (hux, huy)
            dh = H[3]; dw = max(1, round(dh * 0.95))
            # 창 = 호스트 업로드 영역 GxG (게스트 텍스처 크기 기준으로 환산한 정수 좌표)
            cells[28] = (0, 0, dw, dh)
            cells[29] = (hux * gW // hW, huy * gH // hH, hG * gW // hW, hG * gH // hH)
            cells[30] = (0, 0, 0xFFFF, 0); cells[31] = (0, 0, hG | 0x2000 | (0x8000 if f['pic'] > 0 else 0), hid << 8)
            rep.append((f['file'], f['dpac'], f['key'], 'guest', dw, dh))
        elif r is None:
            # 공간 없음: 한글은 투명 칸으로 자리만 차지
            sp = cells[0x20]
            capH = H[3] * 0.6
            dw = round(capH * 1.12 * 24 / 22)
            cells[28] = (0, 0, dw, H[3]); cells[29] = (sp[0], sp[1], max(1, sp[2] // 2), max(1, sp[3] // 2))
            cells[30] = (0, 0, 0xFFFF, 0); cells[31] = (0, 0, 24, 0)
            rep.append((f['file'], f['dpac'], f['key'], 'blank'))
        else:
            if f['pic'] == 0: refs[key] = (r['capt'], r['capb'], H[3], r['dw'], H[2])
            elif ref is not None and len(ref) > 3:
                r['dw'] = max(1, round(ref[3] * H[2] / ref[4]))     # 레이어 글꼴: 가로는 본 글꼴 'H' 폭 비율
            cells[28] = (0, 0, r['dw'], r['dh']); cells[29] = (r['wx'], r['wy'], r['ww'], r['wh'])
            cells[30] = (0, 0, r['ux'], r['uy'])
            hid = HOSTS[fk][0] if fk in HOSTS else 0
            cells[31] = (0, 0, r['G'] | (0x8000 if r.get('glow') else 0) | (0x4000 if fk in HOSTS else 0), lutsel | (hid << 8))
            if fk in HOSTS: hostwin[fk] = (r['ux'], r['uy'], w, h, r['G'], hid)
            rep.append((f['file'], f['dpac'], f['key'], r['G'], r['hi'], (r['ux'], r['uy']), r['dw'], r['dh'], round(r['s'], 2)))
        d = out.setdefault((f['file'], f['dpac']), {})
        d[tuple(f['key'])] = ychr_bytes(y)
        if r is not None and r['hi']:
            # 슬롯 영역의 기존 픽셀(고위 코드 글리프)을 투명색으로
            tk = f['tims'][min(f['pic'], len(f['tims']) - 1)][0]
            tb2 = bytearray(d.get(tuple(tk), tb))
            assert pictures(bytes(tb2))[0]['w'] == w
            pp = pictures(bytes(tb2))[0]
            tr = p['alpha'].index(0)
            x0, y0, rw, rh = r['rect']
            for yy in range(y0, y0 + rh):
                for xx in range(x0, x0 + rw):
                    i = yy * w + xx; bo = pp['img'] + i // 2
                    if i & 1: tb2[bo] = (tb2[bo] & 0x0F) | (tr << 4)
                    else: tb2[bo] = (tb2[bo] & 0xF0) | tr
            d[tuple(tk)] = bytes(tb2)
    return out, rep

if __name__ == '__main__':
    out, rep = patch_fonts()
    for r in rep: print(r)

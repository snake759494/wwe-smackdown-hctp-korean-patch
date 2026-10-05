"""이미지 안 글자를 한글로 다시 그리기 (TIM2 4/8bpp, 팔레트 유지)."""
import os, struct
from PIL import Image, ImageDraw, ImageFont
import bpe
from tim2 import pictures
from fonts import leaves

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
EXT = os.path.join(ROOT, 'work', 'ext')
SANS = os.path.join(ROOT, 'NanumSquareNeo-dEb.ttf')


def _palette(tb, p):
    cl = tb[p['clut']:p['clut'] + p['clsz']]
    pal = [tuple(cl[i * 4:i * 4 + 4]) for i in range(p['clc'])]
    if p['imt'] == 5 and not (p['clt'] & 0x80):
        sw = lambda i: (i & 0xe7) | ((i & 8) << 1) | ((i & 16) >> 1)
        pal = [pal[sw(i)] for i in range(len(pal))]
    return pal


def decode(tb, pi=0):
    """→ (RGBA 이미지, 팔레트, 그림정보)"""
    p = pictures(tb)[pi]; w, h = p['w'], p['h']
    im = tb[p['img']:p['img'] + p['imsz']]
    if p['imt'] == 4:
        idx = []
        for b in im[:w * h // 2]: idx += [b & 15, b >> 4]
    else: idx = list(im[:w * h])
    pal = _palette(tb, p)
    img = Image.new('RGBA', (w, h)); img.putdata([pal[i] for i in idx])
    return img, pal, p, idx


def encode(tb, p, pal, rgba):
    """RGBA(알파 0~128) 이미지를 원래 팔레트 번호로 되돌려 TIM2 에 기록."""
    w, h = p['w'], p['h']
    px = list(rgba.getdata())
    cache = {}
    def near(c):
        if c in cache: return cache[c]
        best = min(range(len(pal)), key=lambda i: sum((a - b) ** 2 * (4 if k == 3 else 1) for k, (a, b) in enumerate(zip(pal[i], c))))
        cache[c] = best; return best
    idx = [near(c) for c in px]
    out = bytearray(tb)
    if p['imt'] == 4:
        data = bytes(idx[i] | idx[i + 1] << 4 for i in range(0, w * h, 2))
    else: data = bytes(idx)
    out[p['img']:p['img'] + len(data)] = data
    return bytes(out)


def text_image(w, h, text, font=SANS, color=(255, 255, 255), pad=1, maxsize=None, stroke=0, scolor=(0, 0, 0)):
    """w x h 투명 바탕에 가운데 정렬 글자 (알파 0~128, 필요하면 가로 압축)."""
    SC = 4
    size = (maxsize or h) * SC
    f = ImageFont.truetype(font, size)
    tmp = Image.new('L', (w * SC * 4, h * SC * 2), 0)
    d = ImageDraw.Draw(tmp)
    bb = d.textbbox((0, 0), text, font=f, stroke_width=stroke * SC)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    lay = Image.new('RGBA', (tw + 4, th + 4), (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((2 - bb[0], 2 - bb[1]), text, font=f, fill=color + (255,), stroke_width=stroke * SC, stroke_fill=scolor + (255,))
    tgt_h = (h - 2 * pad) * SC; tgt_w = (w - 2 * pad) * SC
    s = tgt_h / lay.size[1]
    nw = min(tgt_w, int(lay.size[0] * s))
    lay = lay.resize((max(1, nw), int(tgt_h)), Image.LANCZOS)
    big = Image.new('RGBA', (w * SC, h * SC), (0, 0, 0, 0))
    big.alpha_composite(lay, ((w * SC - lay.size[0]) // 2, pad * SC))
    small = big.resize((w, h), Image.LANCZOS)
    r = [(c[0], c[1], c[2], c[3] * 128 // 255) for c in small.getdata()]
    out = Image.new('RGBA', (w, h)); out.putdata(r)
    return out


# (파일, dpac 경로, 키) → (글자, 글꼴, 외곽선)
MONTH_CITY = {
    ('ET2D/CS2D/ABAC', (0, 2)): '4월', ('ET2D/CS2D/ABAC', (0, 4)): '미주리주 캔자스시티',
    ('ET2D/CS2D/AWMN', (0, 2)): '3월', ('ET2D/CS2D/AWMN', (0, 4)): '워싱턴주 시애틀',
    ('ET2D/CS2D/ABAD', (0, 4)): '오하이오주 콜럼버스',
    ('ET2D/CS2D/AJUD', (0, 4)): '테네시주 내슈빌',
    ('ET2D/CS2D/AROY', (0, 2)): '1월', ('ET2D/CS2D/AROY', (0, 4)): '매사추세츠주 보스턴',
    ('ET2D/CS2D/ANOM', (0, 2)): '10월', ('ET2D/CS2D/ANOM', (0, 4)): '아칸소주 리틀록',
    ('ET2D/CS2D/ANOW', (0, 2)): '2월', ('ET2D/CS2D/ANOW', (0, 4)): '캐나다 퀘벡주 몬트리올',
    ('ET2D/CS2D/AUNF', (0, 2)): '9월', ('ET2D/CS2D/AUNF', (0, 4)): '캘리포니아주 로스앤젤레스',
    ('ET2D/CS2D/ASUM', (0, 2)): '8월', ('ET2D/CS2D/ASUM', (0, 4)): '뉴욕주 롱아일랜드',
    ('ET2D/CS2D/ASUR', (0, 2)): '11월', ('ET2D/CS2D/ASUR', (0, 4)): '뉴욕주 뉴욕시',
    ('ET2D/CS2D/AARM', (0, 2)): '12월', ('ET2D/CS2D/AARM', (0, 4)): '플로리다주 포트로더데일',
    ('ET2D/CS2D/AVEN', (0, 2)): '7월', ('ET2D/CS2D/AVEN', (0, 4)): '미시간주 디트로이트',
}


def image_patches():
    """→ {(파일, dpac): {키: 새 TIM2}}"""
    out = {}
    d = open(os.path.join(EXT, 'ENTR2D.PAC'), 'rb').read()
    for p, off, sz in bpe.dpac_dir(d):
        want = {k: t for (dp, k), t in MONTH_CITY.items() if dp == p}
        if not want: continue
        lv = dict((tuple(k), b) for k, b in leaves(d[off:off + sz], []))
        for k, t in want.items():
            img, pal, pi, idx = decode(lv[k])
            r = text_image(pi['w'], pi['h'], t, stroke=1)
            out.setdefault(('ENTR2D.PAC', p), {})[k] = encode(lv[k], pi, pal, r)
    return out


def redraw_regions(tb, regions):
    """regions: [(x0,y0,x1,y1,글자)] — 영역을 투명으로 비우고 외곽선 있는 흰 글자로 다시 씀."""
    img, pal, pi, idx = decode(tb)
    img = img.copy()
    for x0, y0, x1, y1, t in regions:
        img.paste(Image.new('RGBA', (x1 - x0, y1 - y0), (0, 0, 0, 0)), (x0, y0))
        r = text_image(x1 - x0, y1 - y0, t, font=SANS, stroke=1)
        img.paste(r, (x0, y0))
    return encode(tb, pi, pal, img)


GAME2D_IMG = {
    (1, 4): [(0, 97, 64, 111, '항복'), (64, 97, 128, 111, '탈출'), (0, 114, 64, 127, '벗기기')],
    (1, 6): [(0, 0, 128, 16, '정말입니까?')],
}


def game2d_patches():
    d = open(os.path.join(EXT, 'GAME2D.PAC'), 'rb').read()
    e = [x for x in bpe.dpac_dir(d) if x[0] == 'GA2D/DALL'][0]
    lv = dict((tuple(k), b) for k, b in leaves(d[e[1]:e[1] + e[2]], []))
    return {('GAME2D.PAC', 'GA2D/DALL'): {k: redraw_regions(lv[k], r) for k, r in GAME2D_IMG.items()}}

"""한글 글리프(24px/16px, 2bpp) 생성과 2바이트 코드 배정."""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
FONT = os.path.join(ROOT, 'NanumSquareNeo-dEb.ttf')
LEADS = list(range(0x81, 0xA0)) + list(range(0xE0, 0xF0))   # 47개
TRAIL0, NTRAIL = 0x80, 125                                   # 0x80~0xFC


def code_of(idx):
    l, t = divmod(idx, NTRAIL)
    return bytes([LEADS[l], TRAIL0 + t])


def idx_of(b0, b1):
    l = LEADS.index(b0)
    return l * NTRAIL + (b1 - TRAIL0)


class Charset:
    """번역문에 쓰인 한글 음절 → 순번. (음절 정렬 순)"""
    def __init__(self, chars):
        self.chars = sorted(set(c for c in chars if '가' <= c <= '힣'))
        assert len(self.chars) <= len(LEADS) * NTRAIL
        self.index = {c: i for i, c in enumerate(self.chars)}

    def encode(self, s):
        """유니코드 문자열 → 게임 바이트열 (한글은 2바이트, 나머지는 ASCII)."""
        out = bytearray()
        for ch in s:
            if ch in self.index: out += code_of(self.index[ch])
            elif ord(ch) < 0x80: out.append(ord(ch))
            else: raise ValueError('지원하지 않는 문자: %r in %r' % (ch, s))
        return bytes(out)

    def decode(self, b):
        out = []; i = 0
        while i < len(b):
            c = b[i]
            if c in LEADS and i + 1 < len(b) and b[i + 1] >= 0x80:
                out.append(self.chars[idx_of(c, b[i + 1])]); i += 2
            else: out.append(chr(c)); i += 1
        return ''.join(out)


def render(ch, G, font_path=FONT, glow=False):
    """G x G 회색조(0~255) 글리프. 한글 잉크가 위 GA*G/24 ~ 아래 GB*G/24 행에 오도록."""
    SC = 4                                    # 고해상도로 그린 뒤 축소
    big = G * SC
    size = int(G * SC * 0.98)
    f = ImageFont.truetype(font_path, size)
    im = Image.new('L', (big, big), 0)
    dr = ImageDraw.Draw(im)
    # 기준 음절 '한'·'를' 등의 잉크 범위로 세로 위치 고정
    ref_top, ref_bot = _ref_box(f, size)
    ink_h = ref_bot - ref_top
    target_top, target_bot = 1 * G / 24 * SC, 23 * G / 24 * SC
    scale = (target_bot - target_top) / ink_h
    # 스케일을 반영해 다시 폰트 크기 조정
    size2 = max(4, int(size * scale))
    f2 = ImageFont.truetype(font_path, size2)
    t2, b2 = _ref_box(f2, size2)
    bbox = dr.textbbox((0, 0), ch, font=f2)
    w = bbox[2] - bbox[0]
    x = (big - w) / 2 - bbox[0]
    y = target_top - t2
    dr.text((x, y), ch, font=f2, fill=255)
    if glow:   # 글로/외곽 레이어용: 굵게 부풀리고 살짝 번지게
        from PIL import ImageFilter
        im = im.filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.MaxFilter(7))
        im = im.filter(ImageFilter.GaussianBlur(SC * 0.7))
    return im.resize((G, G), Image.LANCZOS)


_REF = {}
def _ref_box(f, size):
    key = (f.path, size)
    if key not in _REF:
        im = Image.new('L', (size * 3, size * 3), 0)
        dr = ImageDraw.Draw(im)
        tops, bots = [], []
        for c in '한글를꽃뷁':
            bb = dr.textbbox((0, 0), c, font=f)
            tops.append(bb[1]); bots.append(bb[3])
        _REF[key] = (min(tops), max(bots))
    return _REF[key]


def to2bpp(im, gamma=0.9):
    """회색조 → 2bpp 바이트열 (한 바이트에 4픽셀, 비트0-1 = 왼쪽)."""
    G = im.size[0]
    px = list(im.getdata())
    q = [min(3, int(round(((v / 255.0) ** gamma) * 3))) for v in px]
    out = bytearray()
    for i in range(0, len(q), 4):
        out.append(q[i] | q[i + 1] << 2 | q[i + 2] << 4 | q[i + 3] << 6)
    return bytes(out)


def lut(idxmap):
    """2bpp 바이트 → 4bpp 2바이트(u16 LE) 변환표. idxmap: 값0~3 → CLUT 번호."""
    out = bytearray()
    for b in range(256):
        p = [idxmap[(b >> (2 * k)) & 3] for k in range(4)]
        out += bytes([p[0] | p[1] << 4, p[2] | p[3] << 4])
    return bytes(out)


def build(charset):
    g24 = bytearray(); g16 = bytearray(); o16 = bytearray(); o24 = bytearray()
    for c in charset.chars:
        g24 += to2bpp(render(c, 24)); g16 += to2bpp(render(c, 16)); o16 += to2bpp(render(c, 16, glow=True), 0.7)
        o24 += to2bpp(render(c, 24, glow=True), 0.5)
    return bytes(g24), bytes(g16), bytes(o16), bytes(o24)


if __name__ == '__main__':
    cs = Charset('시범경기생성시즌옵션제작진한글패치')
    sheet = Image.new('L', (24 * len(cs.chars), 62), 0)
    for i, c in enumerate(cs.chars):
        sheet.paste(render(c, 24), (i * 24, 0)); sheet.paste(render(c, 16), (i * 24, 24)); sheet.paste(render(c, 16, glow=True), (i * 24, 44))
    sheet.save(os.path.join(ROOT, 'work', 'glyph_test.png'))

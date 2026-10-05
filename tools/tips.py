"""로딩 팁 이미지(MISC.PAC 안 TIM2 34~56번) 한글화: 지정 상자의 흰 글자를 지우고 한글을 다시 씀."""
import os, re, cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont
import imgpatch as ip

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
F_TITLE = os.path.join(ROOT, 'NanumSquareNeo-eHv.ttf')
F_BODY = os.path.join(ROOT, 'NanumSquareNeo-cBd.ttf')

# 상자: (x0, y0, x1, y1, 글자, 종류)  종류: T=제목, L/C/R=본문 정렬
from tipspec import SPEC


def erase(rgb, boxes):
    """상자 안의 밝은 무채색(글자)과 그 테두리를 인페인팅으로 지움."""
    a = rgb.astype(int)
    mn = a.min(2); mx = a.max(2); lum = a.mean(2)
    sel = np.zeros(mn.shape, np.uint8); m = np.zeros(mn.shape, np.uint8)
    for x0, y0, x1, y1 in boxes:
        sel[y0:y1, x0:x1] = 1
        sub = ((lum[y0:y1, x0:x1] > 150) & ((mx - mn)[y0:y1, x0:x1] < 45))
        m[y0:y1, x0:x1] |= sub.astype(np.uint8)
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    for i in range(1, n):
        if st[i][3] > 26 or st[i][4] > 400: m[lab == i] = 0      # 글자보다 큰 흰 덩어리(사진 테두리 등)는 보존
    m = cv2.dilate(m, np.ones((7, 7), np.uint8)) & sel
    return cv2.inpaint(rgb, m * 255, 4, cv2.INPAINT_TELEA)


def draw_text(img, box, text, kind):
    x0, y0, x1, y1 = box
    lines = text.split('\n')
    bw, bh = x1 - x0, y1 - y0
    title = kind == 'T'
    font = F_TITLE if title else F_BODY
    size = min(int(bh / len(lines) * (1.1 if title else 0.82)), 22 if title else 19)
    while True:
        f = ImageFont.truetype(font, size)
        ws = [ImageDraw.Draw(img).textbbox((0, 0), l, font=f)[2] for l in lines]
        if max(ws) <= bw or size <= 9: break
        size -= 1
    SC = 4
    layer = Image.new('RGBA', (bw * SC, bh * SC), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    fb = ImageFont.truetype(font, size * SC)
    lh = bh * SC / len(lines)
    for i, l in enumerate(lines):
        bb = d.textbbox((0, 0), l, font=fb)
        tw = bb[2] - bb[0]
        if kind == 'R': x = bw * SC - tw - SC
        elif kind in ('C', 'T'): x = (bw * SC - tw) / 2
        else: x = SC
        y = i * lh + (lh - (bb[3] - bb[1])) / 2 - bb[1]
        sw = 2 * SC if title else SC
        d.text((x, y), l, font=fb, fill=(255, 255, 255, 255), stroke_width=sw, stroke_fill=(20, 20, 30, 255))
    if title:   # 기울임
        layer = layer.transform(layer.size, Image.AFFINE, (1, 0.25, -0.25 * layer.size[1] / 2, 0, 1, 0), Image.BICUBIC)
    layer = layer.resize((bw, bh), Image.LANCZOS)
    img.alpha_composite(layer, (x0, y0))


def render(k, tb):
    """TIM2 바이트 → 한글 TIM2 바이트"""
    img, pal, pi, idx = ip.decode(tb)
    rgba = np.array(img).copy()
    alpha = rgba[:, :, 3].copy()
    spec = SPEC[k]
    rgb = erase(np.ascontiguousarray(rgba[:, :, :3]).astype(np.uint8), [s[:4] for s in spec])
    out = Image.fromarray(np.dstack([rgb, np.full(alpha.shape, 255, np.uint8)]), 'RGBA')
    for x0, y0, x1, y1, t, kind in spec: draw_text(out, (x0, y0, x1, y1), t, kind)
    # 원래 팔레트로 되돌림 (가장 가까운 색)
    return ip.encode(tb, pi, pal, Image.fromarray(np.dstack([np.array(out)[:, :, :3], alpha]), 'RGBA'))


def tip_offsets(d):
    return [m.start() for m in re.finditer(b'TIM2', d) if m.start() % 0x10 == 0]


def preview(k, path):
    d = open(os.path.join(ip.EXT, 'MISC.PAC'), 'rb').read()
    o = tip_offsets(d)[k]
    nb = render(k, d[o:o + 0x50000])
    im = ip.decode(nb)[0]
    Image.fromarray(np.array(im)[:, :, :3]).save(path)

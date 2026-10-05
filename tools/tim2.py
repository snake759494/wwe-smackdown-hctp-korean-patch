import struct
from PIL import Image
def pictures(d):
    assert d[:4] == b'TIM2'
    n = struct.unpack_from('<H', d, 6)[0]; p = 0x80 if d[5] == 1 else 16; out = []
    for _ in range(n):
        tot, clsz, imsz, hsz, clc, fmt, mip, clt, imt, w, h = struct.unpack_from('<IIIHHBBBBHH', d, p)
        tex0, tex1 = struct.unpack_from('<QQ', d, p + 24)
        out.append(dict(off=p, tot=tot, clsz=clsz, imsz=imsz, hsz=hsz, clc=clc, clt=clt, imt=imt, w=w, h=h, tex0=tex0,
                        img=p + hsz, clut=p + hsz + imsz))
        p += tot
    return out
def to_png(d, pic, path):
    w, h = pic['w'], pic['h']; im = d[pic['img']:pic['img'] + pic['imsz']]
    if pic['imt'] == 4:
        px = []
        for b in im: px += [b & 15, b >> 4]
    elif pic['imt'] == 5: px = list(im)
    elif pic['imt'] in (2, 3):
        bpp = 3 if pic['imt'] == 2 else 4
        img = Image.new('RGBA', (w, h))
        img.putdata([(im[i*bpp], im[i*bpp+1], im[i*bpp+2], min(255, im[i*bpp+3]*2) if bpp == 4 else 255) for i in range(w*h)])
        bg = Image.new('RGBA', (w, h), (40, 40, 90, 255)); bg.alpha_composite(img); bg.save(path); return
    else: raise Exception('imt %d' % pic['imt'])
    cl = d[pic['clut']:pic['clut'] + pic['clsz']]
    pal = [tuple(cl[i*4:i*4+4]) for i in range(pic['clc'])]
    if pic['imt'] == 5 and not (pic['clt'] & 0x80):  # CSM1 swizzle
        def sw(i): return (i & 0xe7) | ((i & 8) << 1) | ((i & 16) >> 1)
        pal = [pal[sw(i)] for i in range(len(pal))]
    img = Image.new('RGBA', (w, h))
    img.putdata([(r, g, b, min(255, a * 2)) for r, g, b, a in (pal[x] for x in px[:w*h])])
    bg = Image.new('RGBA', (w, h), (40, 40, 90, 255)); bg.alpha_composite(img); bg.save(path)

"""한글 ISO 빌드.  python build.py"""
import os, sys, struct, shutil, json, time, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpe, iso, isoedit, kfont, codepatch, fontpatch, imgpatch

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
EXT = os.path.join(ROOT, 'work', 'ext')
SRC_ISO = os.path.join(ROOT, 'WWE SmackDown! Here Comes the Pain (USA).iso')
OUT_ISO = os.path.join(ROOT, 'WWE SmackDown! Here Comes the Pain (USA) (Korean).iso')
STATE = os.path.join(ROOT, 'work', 'build_state.json')
DATA_LBA0 = 396                      # DMY500M0.DAT 시작 (더미 영역에 새 파일 배치)
DATA_LBA_END = 396 + 256000 * 3      # DMY500M0~2


def log(*a): print(*a, flush=True)


def read_ext(name):
    return open(os.path.join(EXT, name), 'rb').read()


def build():
    t0 = time.time()
    files = {}                                   # ISO 경로 → 새 바이트
    import inject as tx
    texts = tx.all_texts()                       # 한글 문자 수집용
    cs = kfont.Charset(''.join(texts))
    log('음절 수', len(cs.chars))
    g24, g16, o16, o24 = kfont.build(cs)
    if os.environ.get('NOGLOW'): o16 = b''
    luts = kfont.lut([0, 5, 10, 15]) + kfont.lut([15, 13, 7, 0])
    tail_fn = lambda d, base: tx.apply_slus(d, cs, base)
    elf, L, new_end = codepatch.patch_elf(os.path.join(EXT, 'SLUS_207.87'), g24, g16, len(cs.chars), luts, tail_fn=tail_fn, o16=o16, o24=o24, xpairs=tx.name_pairs(cs))
    log('코드 구간 %x..%x' % (codepatch.BASE, new_end))
    files['SLUS_207.87'] = bytes(elf)
    # 폰트
    fmods, rep = fontpatch.patch_fonts()
    if os.environ.get('NOFONT'): fmods = {}
    for key, rp in imgpatch.image_patches().items(): fmods.setdefault(key, {}).update(rp)
    for key, rp in imgpatch.game2d_patches().items(): fmods.setdefault(key, {}).update(rp)
    pacs = {}
    for (fn, dp), repl in fmods.items():
        d = pacs.get(fn) or read_ext(fn)
        rp = {tuple(k) if isinstance(k, tuple) else (k,): v for k, v in repl.items()}
        if d[:4] != b'DPAC':
            pacs[fn] = bpe.replace_leaves(d, rp); continue
        ent = [e for e in bpe.dpac_dir(d) if e[0] == dp][0]
        blob = d[ent[1]:ent[1] + ent[2]]
        pacs[fn] = bpe.dpac_replace(d, dp, bpe.replace_leaves(blob, rp))
    for fn, d in tx.patch_pacs(cs, pacs, read_ext).items(): pacs[fn] = d
    for fn, d in pacs.items(): files['PAC/' + fn] = d
    for r in tx.REPORT[:50]: log('  !', r)
    log('보고 %d건' % len(tx.REPORT))
    write_iso(files)
    log('완료 %.1fs' % (time.time() - t0))


def write_iso(files):
    ents = {p: (l, s, r) for p, l, s, r in iso.walk(SRC_ISO)}
    if not os.path.exists(OUT_ISO) or os.path.getsize(OUT_ISO) != os.path.getsize(SRC_ISO):
        log('원본 복사...'); shutil.copyfile(SRC_ISO, OUT_ISO)
    st = json.load(open(STATE)) if os.path.exists(STATE) else {'used_end': DATA_LBA0}
    with open(SRC_ISO, 'rb') as src, open(OUT_ISO, 'r+b') as f:
        # 메타데이터 섹터 원상 복구 (0..395)
        src.seek(0); f.seek(0); f.write(src.read(DATA_LBA0 * 2048))
        lba = DATA_LBA0
        for path, data in sorted(files.items()):
            f.seek(lba * 2048); f.write(data)
            pad = (-len(data)) % 2048; f.write(bytes(pad))
            isoedit.relocate(f, SRC_ISO, path, lba, len(data))
            log('  %-16s LBA %d  %d B' % (path, lba, len(data)))
            lba += (len(data) + 2047) // 2048
        assert lba < DATA_LBA_END
        # 더미 파일이 새 데이터와 겹치지 않게 시작 위치를 뒤로 미루고 크기를 줄인다
        dmy0 = 396 + 256000
        assert lba < dmy0
        isoedit.relocate(f, SRC_ISO, 'DMY500M0.DAT', lba, (dmy0 - lba) * 2048)
        # 이전 빌드가 더 많이 썼다면 나머지를 원본(0)으로
        if st['used_end'] > lba:
            f.seek(lba * 2048)
            n = st['used_end'] - lba
            while n > 0:
                k = min(n, 4096); f.write(bytes(k * 2048)); n -= k
        json.dump({'used_end': lba}, open(STATE, 'w'))


if __name__ == '__main__':
    build()

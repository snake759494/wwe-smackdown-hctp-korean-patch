"""SLUS_207.87 패치: 한글 글리프 구간 추가 + 출력 훅."""
import struct, os
from asm import assemble
from elf import Elf
import kfont

BASE = 0x5A1000
F_GETFONTCELL = 0x1625B0
F_SPRITESHOW = 0x15EEE0
F_SPRITEFAST = 0x15F450
CALL_SPRITESHOW = [0x162E80, 0x162F68, 0x162F88]      # ShowString 안
CALL_SPRITEFAST = [0x162988, 0x1629A4]                # ShowFast 안
RENDER_PTR = 0x524EB0

HOOK = r'''
# crt0 의 BSS 초기화가 _end(0x5a1000) 다음 16바이트까지 지우므로 비워 둔다
    .space 16
# ---- GetFontCell 진입 훅 -------------------------------------------------
# a0=this a1=prev a2=c a3=&str t0=&cell t1=&kern t2=&cellno
kfc:
    andi  v1, a2, 0xff
    sltiu at, v1, 0x81
    bnez  at, kfc_orig
    sltiu at, v1, 0xa0
    bnez  at, kfc_lead
    addiu t4, v1, -0x81
    sltiu at, v1, 0xe0
    bnez  at, kfc_orig
    sltiu at, v1, 0xf0
    beqz  at, kfc_orig
    addiu t4, v1, -0xc1
kfc_lead:
    lw    t3, 0(a3)
    lbu   t5, 1(t3)
    sltiu at, t5, 0x80
    bnez  at, kfc_orig
    sll   t6, t4, 7
    subu  t6, t6, t4
    subu  t6, t6, t4
    subu  t6, t6, t4
    addu  t6, t6, t5
    addiu t6, t6, -0x80
    la    t7, NGLYPH
    lw    t7, 0(t7)
    sltu  at, t6, t7
    bnez  at, kfc_ok
    nop
    move  t6, zero
kfc_ok:
    addiu t3, t3, 1
    sw    t3, 0(a3)
    sw    zero, 0(t1)
    lw    t8, 0x150(a0)
    lw    t8, 0x18(t8)                # 자기 셀 배열
    la    t7, PEND
    sw    a0, 0(t7)
    sw    t6, 4(t7)
    ld    v0, 0x140(a0)               # 기본: 자기 텍스처
    move  t4, t8                       # 업로드 셀 배열
    lhu   t9, 636(t8)
    andi  at, t9, 0x2000              # 게스트 글꼴?
    beqz  at, kfc_cell
    nop
    lhu   t3, 638(t8)
    srl   t3, t3, 8
    sll   t3, t3, 4
    la    t9, HOST
    addu  t9, t9, t3
    lw    t3, 0(t9)
    bnez  t3, kfc_guest
    nop
    addiu at, zero, -1                 # 호스트 없음: 글자 건너뜀
    sw    at, 4(t7)
    jr    ra
    move  v0, zero
kfc_guest:
    lw    t4, 0x18(t3)                # 호스트 셀 배열(업로드)
    ld    v0, 8(t9)                   # 호스트 TEX0
kfc_cell:
    sw    t4, 8(t7)
    sd    v0, 16(t7)
    sd    v0, 0x100(a0)
    la    t9, KCELL
    lw    v1, 580(t8)                 # 창은 자기 셀(게스트는 호스트 텍스처 좌표로 기록됨)
    sw    v1, 0(t9)
    lw    v1, 584(t8)
    sw    v1, 4(t9)
    lw    v1, 588(t8)
    sw    v1, 8(t9)
    lw    v1, 592(t8)
    sw    v1, 12(t9)
    lw    v1, 576(t8)                 # 표시 크기는 자기 셀
    sw    v1, 16(t9)
    sw    t9, 0(t0)
    jr    ra
    addiu v0, zero, 1
kfc_orig:
    la    t9, PEND
    addiu v0, zero, -1
    sw    v0, 4(t9)
    addiu sp, sp, -0x60
    sd    ra, 0x50(sp)
    j     0x1625b8
    nop


# ---- 표시 시점 이름 치환: t2 = 문자열 → 표에 있으면 한글 문자열로 (t3-t8, v1, at 사용) ----
XL:
    beqz  t2, xl_ret
    move  t3, zero                 # 해시
    move  t4, t2
    addiu t8, zero, 48
xl_h:
    lbu   v1, 0(t4)
    beqz  v1, xl_hd
    sll   at, t3, 5
    subu  t3, at, t3
    addu  t3, t3, v1
    addiu t4, t4, 1
    addiu t8, t8, -1
    bnez  t8, xl_h
    nop
    jr    ra                       # 너무 김
    nop
xl_hd:
    la    t4, XLN
    lw    t5, 0(t4)                # hi = n
    move  t6, zero                 # lo
    lw    t7, 4(t4)                # 표
xl_bs:
    sltu  at, t6, t5
    beqz  at, xl_ret
    addu  t8, t6, t5
    srl   t8, t8, 1                # mid
    sll   at, t8, 3
    addu  at, at, t8
    sll   at, at, 0
    sll   v1, t8, 2
    addu  v1, v1, t8
    sll   v1, v1, 2                # mid*20? → 12바이트 레코드
    sll   v1, t8, 3
    sll   at, t8, 2
    addu  v1, v1, at               # mid*12
    addu  v1, v1, t7
    lw    at, 0(v1)
    beq   at, t3, xl_found
    sltu  at, at, t3
    beqz  at, xl_hi
    nop
    addiu t6, t8, 1
    b     xl_bs
    nop
xl_hi:
    move  t5, t8
    b     xl_bs
    nop
xl_found:
    lw    t4, 4(v1)                # 영문
    move  t5, t2
xl_cmp:
    lbu   t6, 0(t4)
    lbu   t7, 0(t5)
    bne   t6, t7, xl_ret
    addiu t4, t4, 1
    bnez  t6, xl_cmp
    addiu t5, t5, 1
    lw    t2, 8(v1)
xl_ret:
    jr    ra
    nop

ss_xl:                              # ShowString 진입
    move  t2, a1
    move  t9, ra
    jal   XL
    nop
    move  ra, t9
    move  a1, t2
    addiu sp, sp, -0x200
    j     0x162a28
    sd    ra, 0xa0(sp)

gw_xl:                              # GetFontWidth: lw v0,0x160(a0)
    lw    t2, 0x160(a0)
    move  t9, ra
    jal   XL
    nop
    move  ra, t9
    move  v0, t2
    bnez  v0, gw_1
    move  s3, a0
    j     0x162284
    nop
gw_1:
    j     0x16227c
    nop

# ---- CFontDraw::ShowFast: 한자 모드(0x164) 문자열도 그리기 ----------------
shf_fix:
    lw    v1, 0x160(s5)
    bnez  v1, shf_back
    nop
    lw    v1, 0x164(s5)
    beqz  v1, shf_skip
    nop
shf_back:
    move  t2, v1
    move  t9, ra
    jal   XL
    nop
    move  ra, t9
    move  v1, t2
    j     0x1627cc
    nop
shf_skip:
    j     0x1629e0
    nop

# ---- 경기 중 글꼴 호스트 등록/해제 ---------------------------------------
host_reg:                              # SetupAfterSendVRAM 끝 (a0 = 폰트 데이터, +0x54 = CFontDraw*)
    lw    t0, 0x54(a0)
    beqz  t0, host_ret
    nop
    lw    t1, 0x150(t0)
    beqz  t1, host_ret
    nop
    lw    t2, 0x18(t1)
    lhu   t3, 636(t2)
    andi  t3, t3, 0x4000
    beqz  t3, host_ret
    nop
    lhu   t3, 638(t2)
    srl   t3, t3, 8
    sll   t3, t3, 4
    la    t4, HOST
    addu  t4, t4, t3
    sw    t1, 0(t4)
    ld    t5, 0x140(t0)
    sd    t5, 8(t4)
host_ret:
    jr    ra
    nop
host_clear:                            # a0 = 폰트 데이터: 이 폰트가 호스트면 해제
    lw    t0, 0x54(a0)
    beqz  t0, host_cret
    nop
    lw    t1, 0x150(t0)
    la    t4, HOST
    lw    t5, 0(t4)
    bne   t1, t5, host_c1
    nop
    sw    zero, 0(t4)
host_c1:
    lw    t5, 16(t4)
    bne   t1, t5, host_cret
    nop
    sw    zero, 16(t4)
host_cret:
    jr    ra
    nop
host_rel:                              # ReleaseData__19CFontCtrlDataGame2D 시작
    move  t8, ra
    jal   host_clear
    nop
    move  ra, t8
    addiu sp, sp, -0x70
    sd    ra, 0x40(sp)
    j     0x2335e8
    nop
host_rel_menu:                         # ReleaseData__12FontCtrlData 시작
    move  t8, ra
    jal   host_clear
    nop
    move  ra, t8
    addiu sp, sp, -0x50
    sd    ra, 0x20(sp)
    j     0x194e58
    nop

# ---- SpriteShow / ShowFast 직전: 글리프 업로드 패킷 ---------------------------
kup_sprite:
    la    t8, 0x15eee0
    b     kup
    nop
kup_fast:
    la    t8, 0x15f450
kup:
    la    t9, PEND
    lw    v0, 4(t9)
    bltz  v0, kup_go
    lw    v1, 0(t9)
    bne   v1, a0, kup_go
    nop
    lw    t0, 8(t9)                   # 업로드 셀 배열
    la    at, NOUPLOAD
    lw    at, 0(at)
    bnez  at, kup_restore
    nop
    lhu   t1, 616(t0)           # cell30.w = 업로드 x (0xffff = 업로드 없음)
    lhu   t2, 618(t0)           # cell30.h = 업로드 y
    ori   at, zero, 0xffff
    beq   t1, at, kup_go
    lw    t3, 0x150(a0)
    lw    t3, 0x18(t3)
    lhu   t4, 638(t3)           # 자기 cell31.h = LUT 번호
    lhu   t3, 636(t3)           # 자기 cell31.w = G | 플래그
    # 원본 글리프 주소 t5, 2bpp 바이트 수 t6
    andi  at, t3, 0x8000
    beqz  at, kup_notglow
    nop
    andi  t3, t3, 0xff
    addiu at, zero, 24
    beq   t3, at, kup_o24
    nop
    la    t5, GLYPHO16
    addiu t6, zero, 64
    b     kup_g
    nop
kup_o24:
    la    t5, GLYPHO24
    addiu t6, zero, 144
    b     kup_g
    nop
kup_notglow:
    andi  t3, t3, 0xff
    addiu at, zero, 24
    bne   t3, at, kup_g16
    nop
    la    t5, GLYPH24
    addiu t6, zero, 144
    b     kup_g
    nop
kup_g16:
    la    t5, GLYPH16
    addiu t6, zero, 64
kup_g:
    mult  v0, t6
    mflo  v1
    addu  t5, t5, v1
    # LUT
    la    t7, LUTS
    andi  t4, t4, 0xff
    sll   t4, t4, 9
    addu  t7, t7, t4
    # 패킷 버퍼
    lui   at, %hi(0x524eb0)
    lw    t9, %lo(0x524eb0)(at)
    lui   at, 1
    addu  t9, t9, at            # t9 = CRender + 0x10000
    srl   v1, t6, 3             # nq = (2bpp바이트*2)/16
    addiu a3, v1, 10           # Q (a3 는 SpriteShow 인자가 아님 → 보존 필요)
    lw    v0, 0x554(t9)
    sltu  at, v0, a3
    bnez  at, kup_restore
    nop
    subu  v0, v0, a3
    sw    v0, 0x554(t9)
    lw    v0, 0x564(t9)
    sll   at, a3, 4
    addu  at, v0, at
    sw    at, 0x564(t9)
    lui   at, 0x2000
    or    v0, v0, at            # 비캐시 주소
    # qw0: DMA cnt
    lui   at, 0x1000
    addiu t9, a3, -1
    or    at, at, t9
    sw    at, 0(v0)
    sw    zero, 4(v0)
    sw    zero, 8(v0)
    sw    zero, 12(v0)
    # qw1: VIF NOP NOP NOP DIRECT(Q-2)
    lui   at, 0x5000
    addiu t9, a3, -2
    or    at, at, t9
    sw    zero, 16(v0)
    sw    zero, 20(v0)
    lui   t9, 0x1300
    sw    t9, 24(v0)
    sw    at, 28(v0)
    # qw2: GIFtag A+D x4
    addiu at, zero, 4
    sw    at, 32(v0)
    lui   at, 0x1000
    sw    at, 36(v0)
    addiu at, zero, 0xe
    sw    at, 40(v0)
    sw    zero, 44(v0)
    # qw3: BITBLTBUF  (DBP | DBW<<16 | DPSM<<24) 상위 워드
    la    t9, PEND
    lw    t9, 16(t9)
    andi  at, t9, 0x3fff
    srl   a3, t9, 14
    andi  a3, a3, 0x3f
    sll   a3, a3, 16
    or    at, at, a3
    srl   a3, t9, 20
    andi  a3, a3, 0x3f
    sll   a3, a3, 24
    or    at, at, a3
    sw    zero, 48(v0)
    sw    at, 52(v0)
    addiu at, zero, 0x50
    sw    at, 56(v0)
    sw    zero, 60(v0)
    # qw4: TRXPOS
    sll   at, t2, 16
    or    at, at, t1
    sw    zero, 64(v0)
    sw    at, 68(v0)
    addiu at, zero, 0x51
    sw    at, 72(v0)
    sw    zero, 76(v0)
    # qw5: TRXREG (G x G)
    sw    t3, 80(v0)
    sw    t3, 84(v0)
    addiu at, zero, 0x52
    sw    at, 88(v0)
    sw    zero, 92(v0)
    # qw6: TRXDIR
    sw    zero, 96(v0)
    sw    zero, 100(v0)
    addiu at, zero, 0x53
    sw    at, 104(v0)
    sw    zero, 108(v0)
    # qw7: GIFtag IMAGE nq
    srl   at, t6, 3
    sw    at, 112(v0)
    lui   at, 0x0800
    sw    at, 116(v0)
    sw    zero, 120(v0)
    sw    zero, 124(v0)
    # 이미지: 2bpp → 4bpp
    addiu v1, v0, 128
kup_cp:
    lbu   at, 0(t5)
    sll   at, at, 1
    addu  at, at, t7
    lhu   at, 0(at)
    sh    at, 0(v1)
    addiu t5, t5, 1
    addiu t6, t6, -1
    bnez  t6, kup_cp
    addiu v1, v1, 2
    # GIFtag A+D x1 EOP + TEXFLUSH
    ori   at, zero, 0x8001
    sw    at, 0(v1)
    lui   at, 0x1000
    sw    at, 4(v1)
    addiu at, zero, 0xe
    sw    at, 8(v1)
    sw    zero, 12(v1)
    sw    zero, 16(v1)
    sw    zero, 20(v1)
    addiu at, zero, 0x3f
    sw    at, 24(v1)
    sw    zero, 28(v1)
kup_restore:
    la    t9, KSAVE
    lw    a3, 0(t9)
kup_go:
    jr    t8
    nop
'''
# a3 는 호출 인자로 쓰이지 않지만 안전하게 보존 (kup 진입 시 저장)
HOOK = HOOK.replace('''kup:
    la    t9, PEND''', '''kup:
    la    t9, KSAVE
    sw    a3, 0(t9)
    la    t9, PEND''')
HOOK = HOOK.replace('''    bltz  v0, kup_go
    lw    v1, 0(t9)
    bne   v1, a0, kup_go''', '''    bltz  v0, kup_restore
    lw    v1, 0(t9)
    bne   v1, a0, kup_restore''')
HOOK = HOOK.replace('''    beq   t1, at, kup_go''', '''    beq   t1, at, kup_restore''')

DATA = r'''
.align 4
PEND:   .word 0, 0xffffffff, 0, 0, 0, 0
.align 4
HOST:   .word 0, 0, 0, 0, 0, 0, 0, 0
NOUPLOAD: .word 0
XLN:    .word 0, 0
KSAVE:  .word 0
NGLYPH: .word 0

.align 4
KCELL:  .space 32
.align 4
LUTS:   .space 1024
.align 4
GLYPH24:
'''


def build_segment(g24, g16, nglyph, luts, o16=b'', o24=b'', xpairs=()):
    src = HOOK + DATA
    code, L = assemble(src, BASE, {'GLYPH16': BASE, 'GLYPHO16': BASE, 'GLYPHO24': BASE})
    seg = bytearray(code)
    assert len(luts) == 1024
    o = L['LUTS'] - BASE; seg[o:o + 1024] = luts
    struct.pack_into('<I', seg, L['NGLYPH'] - BASE, nglyph)
    seg += g24
    while len(seg) % 16: seg.append(0)
    L['GLYPH16'] = BASE + len(seg)
    seg += g16
    while len(seg) % 16: seg.append(0)
    L['GLYPHO16'] = BASE + len(seg)
    seg += o16
    while len(seg) % 16: seg.append(0)
    L['GLYPHO24'] = BASE + len(seg)
    seg += o24
    while len(seg) % 16: seg.append(0)
    # GLYPH16 주소는 코드에 들어가므로 다시 어셈블
    code2, L2 = assemble(src, BASE, {'GLYPH16': L['GLYPH16'], 'GLYPHO16': L['GLYPHO16'], 'GLYPHO24': L['GLYPHO24']})
    assert len(code2) == len(code)
    seg[:len(code2)] = code2
    seg[L['LUTS'] - BASE:L['LUTS'] - BASE + 1024] = luts
    struct.pack_into('<I', seg, L['NGLYPH'] - BASE, nglyph)
    # 이름 치환 표
    seg = bytearray(seg)
    def H(b):
        h = 0
        for c in b: h = (h * 31 + c) & 0xffffffff
        return h
    ents = {}
    for en, ko in xpairs:
        if len(en) >= 48: continue
        h = H(en)
        if h in ents and ents[h][0] != en: ents[h] = None; continue
        ents[h] = (en, ko)
    ents = sorted((h, v) for h, v in ents.items() if v)
    strs = bytearray(); recs = []
    sbase = BASE + len(seg) + len(ents) * 12
    for h, (en, ko) in ents:
        a = sbase + len(strs); strs += en + bytes(1)
        b2 = sbase + len(strs); strs += ko + bytes(1)
        recs.append(struct.pack('<III', h, a, b2))
    tab = BASE + len(seg)
    seg += b''.join(recs) + strs
    while len(seg) % 16: seg.append(0)
    struct.pack_into('<II', seg, L2['XLN'] - BASE, len(ents), tab)
    if os.environ.get('NOUPLOAD'): struct.pack_into('<I', seg, L2['NOUPLOAD'] - BASE, 1)
    return bytes(seg), L2


def patch_elf(src_path, g24, g16, nglyph, luts, extra=None, tail_fn=None, o16=b'', o24=b'', xpairs=()):
    """extra: [(va, bytes)] 추가 덮어쓰기."""
    e = Elf(src_path)
    d = bytearray(e.d)
    seg, L = build_segment(g24, g16, nglyph, luts, o16, o24, xpairs)
    def put(va, b):
        o = e.v2o(va); d[o:o + len(b)] = b
    J = lambda t: struct.pack('<I', (2 << 26) | ((t >> 2) & 0x3ffffff))
    JAL = lambda t: struct.pack('<I', (3 << 26) | ((t >> 2) & 0x3ffffff))
    put(F_GETFONTCELL, J(L['kfc']) + b'\0\0\0\0')
    for a in CALL_SPRITESHOW:
        assert d[e.v2o(a):e.v2o(a) + 4] == JAL(F_SPRITESHOW)
        put(a, JAL(L['kup_sprite']))
    for a in CALL_SPRITEFAST:
        assert d[e.v2o(a):e.v2o(a) + 4] == JAL(F_SPRITEFAST)
        put(a, JAL(L['kup_fast']))
    # 추가 데이터(번역 문자열 등)를 구간 끝에
    if tail_fn:
        seg = bytearray(seg)
        while len(seg) % 16: seg.append(0)
        seg += tail_fn(d, BASE + len(seg))
        while len(seg) % 16: seg.append(0)
        seg = bytes(seg)
    # 힙 시작 이동
    new_end = (BASE + len(seg) + 0xfff) & ~0xfff
    hi, lo = ((new_end + 0x8000) >> 16) & 0xffff, new_end & 0xffff
    for a_lui, a_add in ((0x100180, 0x100188), (0x10041C, 0x10042C)):
        w = struct.unpack_from('<I', d, e.v2o(a_lui))[0]; assert w & 0xffff == 0x5a
        struct.pack_into('<I', d, e.v2o(a_lui), (w & 0xffff0000) | hi)
        w = struct.unpack_from('<I', d, e.v2o(a_add))[0]; assert w & 0xffff == 0x1000
        struct.pack_into('<I', d, e.v2o(a_add), (w & 0xffff0000) | lo)
    W = lambda v: struct.pack('<I', v)
    NOP = W(0)
    BR = lambda at, to: W((4 << 26) | (((to - at - 4) >> 2) & 0xffff))       # b
    # GetFontCell: 한자 모드여도 영문 표 경로 (beqz v0,kanji → nop)
    assert d[e.v2o(0x1625E0):e.v2o(0x1625E0) + 4] == W(0x10400011)
    put(0x1625E0, NOP)
    # GetFontHeight: 높이는 'H'(0x48) 셀, 한자 모드도 영문 경로
    put(0x1623A0, W((9 << 26) | (3 << 16) | (0x48 * 20)) + NOP + NOP)      # addiu v1,zero,0x5a0
    put(0x1623C4, NOP + BR(0x1623C8, 0x162388) + NOP)
    # CFontDraw::ShowFast
    put(0x1627C0, J(L['shf_fix']) + NOP)
    # 이름 치환 진입점
    assert d[e.v2o(0x162A20):e.v2o(0x162A24)] == W(0x27BDFE00)
    put(0x162A20, J(L['ss_xl']) + NOP)
    assert d[e.v2o(0x162270):e.v2o(0x162274)] == W(0x8C820160)
    put(0x162270, J(L['gw_xl']) + NOP)
    # 경기 중 글꼴 호스트 등록/해제
    assert d[e.v2o(0x2335D4):e.v2o(0x2335D4) + 4] == W(0x03E00008)
    put(0x2335D4, J(L['host_reg']))
    put(0x2335E0, J(L['host_rel']) + NOP)
    assert d[e.v2o(0x194E48):e.v2o(0x194E48) + 4] == W(0x03E00008)
    put(0x194E48, J(L['host_reg']))
    put(0x194E50, J(L['host_rel_menu']) + NOP)
    # newlib sbrk 의 heap_ptr 초기값(_end)
    assert struct.unpack_from('<I', d, e.v2o(0x40A494))[0] == 0x5A1000
    struct.pack_into('<I', d, e.v2o(0x40A494), new_end)
    for va, b in (extra or []): put(va, b)
    # 새 적재 구간 = 두 번째 프로그램 헤더
    off = (len(d) + 0x7f) & ~0x7f
    d += bytes(off - len(d)); d += seg
    ph1 = e.phoff + 32
    struct.pack_into('<8I', d, ph1, 1, off, BASE, BASE, len(seg), len(seg), 7, 0x10)
    return bytes(d), L, new_end

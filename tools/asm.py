"""라벨을 지원하는 작은 R5900(MIPS) 어셈블러. 필요한 명령만 구현."""
import re, struct

REGS = ['zero', 'at', 'v0', 'v1', 'a0', 'a1', 'a2', 'a3', 't0', 't1', 't2', 't3', 't4', 't5', 't6', 't7',
        's0', 's1', 's2', 's3', 's4', 's5', 's6', 's7', 't8', 't9', 'k0', 'k1', 'gp', 'sp', 'fp', 'ra']
R = {n: i for i, n in enumerate(REGS)}
R['s8'] = 30

I_OPS = {'addiu': 9, 'slti': 10, 'sltiu': 11, 'andi': 12, 'ori': 13, 'xori': 14, 'daddiu': 25}
MEM = {'lb': 32, 'lh': 33, 'lw': 35, 'lbu': 36, 'lhu': 37, 'lwu': 39, 'sb': 40, 'sh': 41, 'sw': 43,
       'ld': 55, 'sd': 63, 'lq': 30, 'sq': 31}
R3 = {'addu': 0x21, 'subu': 0x23, 'and': 0x24, 'or': 0x25, 'xor': 0x26, 'nor': 0x27, 'slt': 0x2a,
      'sltu': 0x2b, 'daddu': 0x2d, 'dsubu': 0x2f, 'sllv': 4, 'srlv': 6, 'dsllv': 0x14, 'dsrlv': 0x16}
SH = {'sll': 0, 'srl': 2, 'sra': 3, 'dsll': 0x38, 'dsrl': 0x3a, 'dsll32': 0x3c, 'dsrl32': 0x3e}


def num(s, labels=None):
    s = s.strip()
    m = re.fullmatch(r'%(hi|lo)\((.+)\)', s)
    if m:
        v = num(m.group(2), labels)
        if m.group(1) == 'hi': return ((v + 0x8000) >> 16) & 0xffff
        return v & 0xffff
    if labels is not None and s in labels: return labels[s]
    if re.fullmatch(r'[A-Za-z_]\w*', s):
        if labels is None: return 0
        raise KeyError('라벨 없음: ' + s)
    return int(eval(s, {}, dict(labels or {})))


def assemble(src, base, ext=None):
    """src(문자열) → (bytes, labels).  ext: 외부 라벨(주소)."""
    lines = []
    for raw in src.splitlines():
        t = raw.split('#')[0].strip()
        if not t: continue
        while True:
            m = re.match(r'^([A-Za-z_]\w*):\s*(.*)$', t)
            if not m: break
            lines.append(('label', m.group(1))); t = m.group(2).strip()
        if t: lines.append(('ins', t))

    def size(t):
        op = t.split()[0]
        if op in ('li', 'la'): return 8
        if op == '.word': return 4 * len(t[5:].split(','))
        if op == '.half': return 2 * len(t[5:].split(','))
        if op == '.byte': return len(t[5:].split(','))
        if op == '.space': return num(t[6:])
        if op == '.align':
            return None
        return 4
    labels = dict(ext or {})
    pc = base
    for kind, t in lines:
        if kind == 'label': labels[t] = pc; continue
        if t.startswith('.align'):
            a = 1 << num(t[6:]); pc = (pc + a - 1) & ~(a - 1); continue
        pc += size(t)
    out = bytearray(); pc = base
    for kind, t in lines:
        if kind == 'label': continue
        if t.startswith('.align'):
            a = 1 << num(t[6:]); n = ((pc + a - 1) & ~(a - 1)) - pc
            out += bytes(n); pc += n; continue
        b = enc(t, pc, labels); out += b; pc += len(b)
    return bytes(out), labels


def enc(t, pc, L):
    op, _, rest = t.partition(' ')
    a = [x.strip() for x in rest.split(',')] if rest.strip() else []
    w = lambda v: struct.pack('<I', v & 0xffffffff)
    reg = lambda s: R[s.strip().lstrip('$')]
    if op == '.word': return b''.join(w(num(x, L)) for x in a)
    if op == '.half': return b''.join(struct.pack('<H', num(x, L) & 0xffff) for x in a)
    if op == '.byte': return bytes(num(x, L) & 0xff for x in a)
    if op == '.space': return bytes(num(rest))
    if op == 'nop': return w(0)
    if op == 'li':
        v = num(a[1], L) & 0xffffffff
        return w((15 << 26) | (reg(a[0]) << 16) | (v >> 16)) + w((13 << 26) | (reg(a[0]) << 21) | (reg(a[0]) << 16) | (v & 0xffff))
    if op == 'la':
        v = num(a[1], L)
        hi = ((v + 0x8000) >> 16) & 0xffff
        return w((15 << 26) | (reg(a[0]) << 16) | hi) + w((9 << 26) | (reg(a[0]) << 21) | (reg(a[0]) << 16) | (v & 0xffff))
    if op == 'move': return w((reg(a[1]) << 21) | (reg(a[0]) << 11) | 0x2d)
    if op in I_OPS: return w((I_OPS[op] << 26) | (reg(a[1]) << 21) | (reg(a[0]) << 16) | (num(a[2], L) & 0xffff))
    if op == 'lui': return w((15 << 26) | (reg(a[0]) << 16) | (num(a[1], L) & 0xffff))
    if op in MEM:
        m = re.fullmatch(r'(.*)\((\$?\w+)\)', a[1])
        off = num(m.group(1) or '0', L)
        return w((MEM[op] << 26) | (reg(m.group(2)) << 21) | (reg(a[0]) << 16) | (off & 0xffff))
    if op in R3: return w((reg(a[1]) << 21) | (reg(a[2]) << 16) | (reg(a[0]) << 11) | R3[op])
    if op in SH: return w((reg(a[1]) << 16) | (reg(a[0]) << 11) | ((num(a[2]) & 31) << 6) | SH[op])
    if op in ('mult', 'multu', 'div', 'divu'):
        fn = {'mult': 0x18, 'multu': 0x19, 'div': 0x1a, 'divu': 0x1b}[op]
        return w((reg(a[0]) << 21) | (reg(a[1]) << 16) | fn)
    if op == 'mflo': return w((reg(a[0]) << 11) | 0x12)
    if op == 'mfhi': return w((reg(a[0]) << 11) | 0x10)
    if op == 'jr': return w((reg(a[0]) << 21) | 8)
    if op == 'jalr': return w((reg(a[0]) << 21) | (31 << 11) | 9)
    if op in ('j', 'jal'):
        tgt = num(a[0], L)
        return w(((2 if op == 'j' else 3) << 26) | ((tgt >> 2) & 0x3ffffff))
    br = lambda tgt: ((num(tgt, L) - pc - 4) >> 2) & 0xffff
    if op in ('beq', 'bne'): return w(((4 if op == 'beq' else 5) << 26) | (reg(a[0]) << 21) | (reg(a[1]) << 16) | br(a[2]))
    if op == 'b': return w((4 << 26) | br(a[0]))
    if op == 'beqz': return w((4 << 26) | (reg(a[0]) << 21) | br(a[1]))
    if op == 'bnez': return w((5 << 26) | (reg(a[0]) << 21) | br(a[1]))
    if op == 'blez': return w((6 << 26) | (reg(a[0]) << 21) | br(a[1]))
    if op == 'bgtz': return w((7 << 26) | (reg(a[0]) << 21) | br(a[1]))
    if op == 'bltz': return w((1 << 26) | (reg(a[0]) << 21) | br(a[1]))
    if op == 'bgez': return w((1 << 26) | (reg(a[0]) << 21) | (1 << 16) | br(a[1]))
    raise ValueError('미구현: ' + t)

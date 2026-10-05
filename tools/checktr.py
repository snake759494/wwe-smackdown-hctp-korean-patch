"""번역 검사:  python tools/checktr.py <묶음이름|all>"""
import json, os, re, sys, glob
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
BAT = os.path.join(ROOT, 'work', 'batches')
KO = os.path.join(ROOT, 'translation', 'ko')
TOK = re.compile(r'%[-0-9.]*[sdcyn%]|@MSG2|@MSG|@S|@C|#[0-9]|\\n|\n')


def width(s):
    w = 0
    for c in s:
        if '가' <= c <= '힣': w += 1
        elif c == '\n': continue
        elif c.isupper() or c in 'MW@%&': w += 1
        else: w += 0.75
    return w


def nbytes(s): return sum(2 if '가' <= c <= '힣' else 1 for c in s)


def check(name):
    src = json.load(open(os.path.join(BAT, name + '.json'), encoding='utf-8'))
    p = os.path.join(KO, name + '.json')
    if not os.path.exists(p): return ['번역 파일 없음']
    ko = json.load(open(p, encoding='utf-8'))
    errs = []
    for it in src:
        i = it['id']; en = it['en']
        if i not in ko: errs.append('%s: 누락' % i); continue
        t = ko[i]
        if not isinstance(t, str): errs.append('%s: 문자열 아님' % i); continue
        bad = [c for c in t if not ('가' <= c <= '힣' or ord(c) < 0x80)]
        if bad: errs.append('%s: 허용 안 되는 문자 %r' % (i, ''.join(sorted(set(bad)))))
        if sorted(TOK.findall(en)) != sorted(TOK.findall(t)):
            # %n 과 \n 은 줄 수만 맞으면 허용(줄이는 것은 허용)
            a = [x for x in TOK.findall(en) if x not in ('\n', '%n', '\\n')]
            b = [x for x in TOK.findall(t) if x not in ('\n', '%n', '\\n')]
            if a != b: errs.append('%s: 서식 토큰 불일치 %s → %s' % (i, a, b))
        nl_en = en.count('\n') + en.count('%n'); nl_ko = t.count('\n') + t.count('%n')
        if nl_ko > nl_en: errs.append('%s: 줄 수 증가 (%d→%d)' % (i, nl_en, nl_ko))
        if it.get('maxb') is not None and nbytes(t) > it['maxb']:
            errs.append('%s: 바이트 초과 %d > %d  %r' % (i, nbytes(t), it['maxb'], t))
        if it.get('w') and width(t) > it['w'] * 1.15 + 1 and len(en) < 40:
            errs.append('%s: 폭 초과 %.1f > %.1f  %r' % (i, width(t), it['w'], t))
        if en.startswith(' ') != t.startswith(' ') and en.strip():
            errs.append('%s: 앞 공백 불일치' % i)
        if not t and en: errs.append('%s: 빈 번역' % i)
    extra = set(ko) - set(it['id'] for it in src)
    if extra: errs.append('알 수 없는 id %d개' % len(extra))
    return errs


if __name__ == '__main__':
    names = sys.argv[1:]
    if names == ['all']:
        names = sorted(os.path.basename(f)[:-5] for f in glob.glob(os.path.join(BAT, '*.json')))
    tot = 0
    for n in names:
        e = check(n); tot += len(e)
        print('[%s] %s' % (n, '정상' if not e else '%d건' % len(e)))
        for x in e[:60]: print('   ', x)
    sys.exit(1 if tot else 0)

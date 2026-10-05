"""원본 ISO에서 빌드에 필요한 파일을 꺼내고 위치 정보(work/src)를 만든다.  python tools/prepare.py"""
import os, sys, subprocess, pycdlib
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ISO = os.path.join(ROOT, 'WWE SmackDown! Here Comes the Pain (USA).iso')
EXT = os.path.join(ROOT, 'work', 'ext')
FILES = ['/SLUS_207.87;1'] + ['/PAC/%s.PAC;1' % n for n in
         ('MENU', 'GAME2D', 'ENTR2D', 'MISC', 'MOVES', 'CA', 'STABLE', 'M', '_AUTO')]
if __name__ == '__main__':
    os.makedirs(EXT, exist_ok=True)
    i = pycdlib.PyCdlib(); i.open(ISO)
    for p in FILES:
        out = os.path.join(EXT, p.split('/')[-1][:-2])
        if not os.path.exists(out): i.get_file_from_iso(out, iso_path=p)
    i.close()
    here = os.path.dirname(os.path.abspath(__file__))
    for s in ('slus_strings.py', 'extract.py'):
        subprocess.check_call([sys.executable, os.path.join(here, s)], cwd=here)
    print('준비 완료')

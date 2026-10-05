# 빌드

Python 3.11 이상, `requirements.txt`의 라이브러리, 원본 북미판 ISO, 나눔스퀘어네오 글꼴 `NanumSquareNeo-cBd.ttf`·`NanumSquareNeo-dEb.ttf`·`NanumSquareNeo-eHv.ttf`가 필요합니다. 글꼴은 나눔스퀘어네오 공식 배포본에서 구합니다.

저장소 루트에 원본 `WWE SmackDown! Here Comes the Pain (USA).iso`와 글꼴을 놓고 실행합니다.

```text
python -m pip install -r requirements.txt
python tools/prepare.py
python tools/build.py
```

- `prepare.py`: 원본 ISO에서 실행 파일과 필요한 PAC을 `work/ext/`로 꺼내고, 문자열 위치·참조 정보(`work/src/`)를 만듭니다. 영어 원문이 담긴 작업 파일은 Git에서 제외됩니다.
- `build.py`: `translation/resolved.json`의 한글 번역을 주입해 `WWE SmackDown! Here Comes the Pain (USA) (Korean).iso`를 만듭니다. 바뀐 파일은 디스크의 더미 파일(DMY500M0) 영역에 다시 배치하고 ISO9660·UDF 디렉터리를 갱신합니다.

같은 원본과 같은 라이브러리·글꼴이면 배포판과 바이트 단위로 같은 ISO가 나옵니다(SHA-256은 README 참고). 도구·글꼴 버전이 다르면 결과가 달라질 수 있으므로, 배포판과 같은 결과가 필요하면 릴리즈의 xdelta를 적용하세요.

차분 파일 생성과 복원 검사:

```text
xdelta3 -e -9 -S none -A -s "WWE SmackDown! Here Comes the Pain (USA).iso" "WWE SmackDown! Here Comes the Pain (USA) (Korean).iso" WWE_SmackDown_HCTP_KO_v1.0.xdelta
xdelta3 -d -s "WWE SmackDown! Here Comes the Pain (USA).iso" WWE_SmackDown_HCTP_KO_v1.0.xdelta verify.iso
```

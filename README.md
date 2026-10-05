# WWE SmackDown! Here Comes the Pain (PS2 북미판, SLUS-20787) 비공식 한글패치

정식 릴리즈 **v1.0**입니다. 원본 ISO에 적용하는 xdelta 차분 파일을 배포합니다.

## 적용 방법

1. 아래 해시와 일치하는 원본 `WWE SmackDown! Here Comes the Pain (USA).iso`를 준비합니다.
2. [릴리즈](https://github.com/snake759494/wwe-smackdown-hctp-korean-patch/releases/tag/v1.0)에서 `WWE_SmackDown_HCTP_KO_v1.0.xdelta`를 받습니다.
3. xdelta3 또는 Windows의 xdeltaUI로 **원본 ISO에** 적용합니다.

```text
xdelta3 -d -s "WWE SmackDown! Here Comes the Pain (USA).iso" WWE_SmackDown_HCTP_KO_v1.0.xdelta "WWE SmackDown! Here Comes the Pain (USA) (Korean).iso"
```

| 항목 | 값 |
| --- | --- |
| 원본 형식 | DVD ISO (2,048바이트 섹터), 북미판 SLUS-20787 |
| 원본 ISO 크기 | 4,525,228,032 B |
| 원본 ISO MD5 | `014ae3d46510de9f6b01ce9a6e436a82` |
| 원본 ISO SHA-256 | `690ca52a5fd8418d2f4e2ed7e3a49df7613ddbd88ac68e7928acd0e5514dc087` |
| xdelta SHA-256 | `af56e4c515d9b0f4e5ec634090e5edffb5fdb8ffe904075b32ce4f7420a4e7a7` |
| 결과 ISO 크기 | 4,525,228,032 B |
| 결과 ISO SHA-256 | `f2e876528379532e1b7de4224b6290bfd11973703ebf3021654a3063f6887de7` |

메모리 카드 저장 데이터는 원본과 그대로 호환됩니다. 저장 데이터에 남은 영어 선수 이름도 화면에서 한글로 표시됩니다.

## 한글화 범위

- 영어 전용 게임에 2바이트 한글 출력 추가(한글 1,079자, 나눔스퀘어네오). 글꼴마다 빈 칸에 글자를 그때그때 올려 그리는 방식이라 VRAM을 추가로 쓰지 않습니다.
- 메뉴·옵션·생성 모드·메모리 카드 안내 등 UI 문구 약 1,480종.
- 시즌 모드 스토리 대사 3,412줄과 백스테이지 이벤트 1,998줄.
- 선수 이름·별칭(경기 화면, 선택 화면, 명단), 기술 이름 1,861개, 피니셔, 의상, 도발·동작, 입장 음악·영상, 스테이블 이름.
- 로딩 화면 조작 팁 이미지 23장, PPV 소개 월·도시 이미지, 경기 중 확인 문구·서브미션 표시 이미지.

## 남은 부분 및 확인 범위

로고, 법적 저작권 고지 이미지, "PAUSE"·"KO"·"Hit Any button Repeatedly" 등 일부 경기 연출 그림, 팀 이름 일부, 디버그 문구는 영어로 남아 있습니다. 실황 음성·영상은 번역하지 않았습니다.

PCSX2에서 메인 메뉴, 시범 경기 설정과 경기 진행(일시정지·경기 종료 화면 포함), 옵션, 생성 모드 메뉴, 시즌 시작과 스토리 대사를 확인했습니다. 모든 시즌 이벤트와 매치 종류를 직접 진행해 보지는 못했습니다. 넘치거나 어색한 문구는 이슈로 알려 주세요.

## 제작 자료

- `tools/`: 원본 준비, PAC/BPE 해석·재압축, 글꼴·실행 코드 패치, 이미지 문자 재작성, ISO 빌드 도구.
- `translation/resolved.json`: 항목 ID별로 직접 작성한 한글 번역. 영어 원문은 빌드할 때 사용자의 원본에서 복원합니다.
- `translation/STYLE.md`: 번역 지침과 용어집.
- [빌드 방법](docs/BUILD.md), [기술 설명](docs/TECHNICAL.md), [권리 및 외부 자료](RIGHTS.md), [변경 내역](CHANGELOG.txt).

원본 게임·패치 ISO·추출 자료·글꼴과 외부 도구 바이너리는 배포하지 않습니다. 외부 기계 번역은 사용하지 않았습니다.

# WWE SmackDown! Here Comes the Pain 한글화 번역 지침

## 입출력
- 입력 묶음: `work/batches/<묶음>.json` — 배열, 항목 `{"id", "en", "w"?, "maxb"?, "ctx": [앞 문자열, 뒤 문자열]}`
  - `ctx`는 데이터상 바로 앞뒤 문자열(참고용, 번역 대상 아님). 메시지 창 문구는 한 줄씩 따로 저장돼 있으므로
    앞뒤 줄을 보고 문장 흐름을 맞춘다.
- 출력: `translation/ko/<묶음>.json` — `{"<id>": "번역문", ...}` (UTF-8, ensure_ascii=False, 모든 id 포함)
  - 번역하지 않고 원문 유지할 항목은 원문을 그대로 넣는다(빈 문자열 금지. 원문이 빈 문자열이면 빈 문자열).
- 다 쓴 뒤 반드시 `python tools/checktr.py <묶음>` 으로 검사하고 오류를 고친다.

## 반드시 지킬 것 (어기면 게임 오류)
1. **사용 문자**: 한글 완성형(가~힣)과 ASCII만. 그 밖의 문자(…, ·, ‘’, “”, 전각 기호, 한자, 자모 단독, 이모지) 금지.
   말줄임은 `...`, 따옴표는 `"` 와 `'`.
2. **maxb(바이트 한도)** 가 있는 항목: 한글 1자 = 2바이트, ASCII 1자 = 1바이트로 센 합이 maxb 이하.
3. **w(폭)** 가 있는 항목: 번역문 폭(한글 1자 = 1, 영문 대문자 = 1, 그 밖의 ASCII = 0.75)이 대략 w 이하.
   메뉴·버튼·표 머리 같은 짧은 항목은 엄격히, 문장은 약간 넘어도 됨.
4. **서식·제어 토큰 보존**(개수·순서 그대로): `%s %d %2d %c %y %n %%` 등, `@MSG` `@MSG2` `@S` `@C`(맨 앞 토큰),
   `#1` `#2` `#3`(이름 자리), `\n`(줄바꿈), 앞뒤 공백, 줄 맨 앞 공백.
   - `%n` 은 줄바꿈 기호다. 원문의 `%n`/`\n` 개수만큼 줄을 나누되, 한국어 어순에 맞게 줄 내용을 재배치해도 된다.
     줄 수를 늘리지 말 것(줄이는 것은 가능, 단 `%n`은 원문 개수 유지가 안전하면 유지).
   - 순서가 중요한 `%s %d` 는 순서를 바꾸지 말 것.
5. `PlayStation`2` 의 백틱(`)은 ® 기호이므로 그대로 둔다. `memory card  (8MB) (for PlayStation`2)` →
   `메모리 카드(8MB)(PlayStation`2용)`, `MEMORY CARD slot @MSG` → `MEMORY CARD 슬롯 @MSG`.
6. **이름 자리 `#1` `#2` 뒤 조사**: 받침에 따라 바뀌는 조사(은/는, 이/가, 을/를, 와/과, (으)로, 이랑, 아/야)를 붙이지 말 것.
   `의, 에, 에서, 에게, 한테, 도, 만, 까지, 보다, 처럼` 은 가능. 필요하면 문장을 바꿔 쓴다(`#1, ...` 처럼 호칭으로 빼기 등).
   `#1`은 선수 이름일 수도, 방송(쇼) 이름일 수도 있으니 문맥으로 판단.

## 번역하지 않는 것 (원문 그대로)
- 내부 키·식별자로 보이는 것: 파일명, 공백 없는 코드(TRACK1, TYPE A 등은 아래 예외 참고), 디버그 문구, 개발용 문자열,
  ‘MATT ONLY’ 같은 퍼즐 단어 목록(같은 위치에 대문자 단어 조각이 줄줄이 있는 것), 의미 없는 더미.
- 단, `TRACK1` → `트랙1`, `TYPE A` → `타입 A`, `COLOR1` → `색상1`처럼 화면 표시 항목은 번역해도 된다.
- 약어: KO, DQ, TLC, SD$, SP, GM(→ 아래 용어), PPV, WWE, RAW 는 그대로.

## 문체
- 메뉴·버튼·제목·항목명: 짧은 명사형. 원문이 대문자여도 한국어는 그냥 한글.
- 시스템 안내·확인 메시지·설명: 합니다체("~합니다.", "~하시겠습니까?").
- 시즌 대사:
  - 해설 `J.R.:` 는 그대로 두고 존댓말 계열('~군요', '~네요', '~입니다'), `King:` 은 `킹:` 으로 쓰고 반말('~야', '~지').
    `Cole:` → `콜:`, `Tazz:` → `타즈:`. 화자 줄 형식(`"J.R.:\n 내용"`, 줄 앞 공백)은 그대로 유지.
  - 레슬러 프로모·대화: 인물 성격에 맞는 구어체(대개 반말, 거친 말투 가능). 단장(GM)·회장은 상황에 따라 반말/하게체.
  - 더 락은 자신을 3인칭으로 부른다("더 락은 ...").  유행어는 자연스러운 한국어 의역 가능.
  - 한 줄은 대략 한글 24자 이내. 원문 줄바꿈 위치는 한국어 흐름에 맞게 옮겨도 되지만 줄 수는 늘리지 않는다.
- 기술(무브) 이름: 통용 음역 위주(Powerslam → 파워슬램, Suplex → 수플렉스, Brainbuster → 브레인버스터,
  Piledriver → 파일드라이버, DDT → DDT, Clothesline → 클로스라인, Dropkick → 드롭킥, Elbow Drop → 엘보 드롭,
  Pin → 핀). 길면 bytes 한도 안에서 줄인다. 고유 피니셔도 음역(Rock Bottom → 락 바텀, Pedigree → 페디그리,
  Stone Cold Stunner → 스톤 콜드 스터너, F-5 → F-5).
- 도발·자세 이름, 의상 설명: 뜻을 살린 짧은 명사형.

## 용어집
| 영어 | 한국어 |
|---|---|
| Exhibition / Season / Create / Options / Credits | 시범 경기 / 시즌 / 생성 / 옵션 / 제작진 |
| Superstar / Created Superstar | 슈퍼스타 / 생성 슈퍼스타 |
| Stable / Faction | 스테이블 / 세력 |
| Manager / Referee / Special Referee | 매니저 / 심판 / 특별 심판 |
| GM (General Manager), G.M. | 단장 |
| Taunt / Entrance / Attire / Appearance | 도발 / 입장 / 의상 / 외모 |
| Move set / Special move / Finisher | 기술 세트 / 필살기 / 피니셔 |
| Signature / Grapple / Irish whip | 시그니처 / 그래플 / 아이리시 휩 |
| Turnbuckle / Apron / Ropes / Ring / Ringside | 턴버클 / 에이프런 / 로프 / 링 / 링사이드 |
| Groggy | 그로기 |
| Face / Heel | 페이스 / 힐 |
| Superstar Points / Attribute Points / SmackDown! Dollars (SD$) | 슈퍼스타 포인트 / 능력치 포인트 / 스맥다운! 달러(SD$) |
| Strength / Submission / Speed / Technique / Endurance | 힘 / 서브미션 / 스피드 / 기술 / 지구력 |
| Health / Healing | 체력 / 회복 |
| Locker Room / GM Room / Meditation Room / Backstage | 라커룸 / 단장실 / 명상실 / 백스테이지 |
| Program (RAW/SmackDown!) / Brand | 프로그램 / 브랜드 |
| Title / Champion / Championship / Contender | 타이틀 / 챔피언 / 챔피언십 / 도전자 |
| World Heavyweight / Intercontinental / U.S. / Cruiserweight / Hardcore / Women's / Tag Team / World Tag | 월드 헤비웨이트 / 인터컨티넨탈 / U.S. / 크루저웨이트 / 하드코어 / 여성 / 태그 팀 / 월드 태그 팀 |
| Single / Tag / Tornado Tag / 6-Man Tag / Handicap | 싱글 / 태그 / 토네이도 태그 / 6인 태그 / 핸디캡 |
| Royal Rumble / King of the Ring / Hardcore / Survival / Main Events | 로열 럼블 / 킹 오브 더 링 / 하드코어 / 서바이벌 / 메인 이벤트 |
| Triple Threat / Fatal 4-Way / Battle Royal / Cage / Elimination | 트리플 스레트 / 페이탈 4웨이 / 배틀 로열 / 케이지 / 엘리미네이션 |
| Hell in a Cell / I Quit / Ironman / Ladder / Last Man Standing / Lumberjack | 헬 인 어 셀 / 아이 큇 / 아이언맨 / 래더 / 라스트 맨 스탠딩 / 럼버잭 |
| Slobber Knocker / Street Fight / Table / TLC / Elimination Chamber | 슬로버 노커 / 스트리트 파이트 / 테이블 / TLC / 엘리미네이션 체임버 |
| First Blood / Bra & Panties / Submission (match) / Ultimate Submission | 퍼스트 블러드 / 브라 & 팬티즈 / 서브미션 / 얼티밋 서브미션 |
| Pin / Give Up / Rope Break / KO / DQ / Ring Out / Interference | 핀 / 기브업 / 로프 브레이크 / KO / DQ(반칙패) / 링아웃 / 난입 |
| SmackDown! / RAW / Velocity / HEAT | 스맥다운! / RAW / 벨로시티 / 히트 |
| WrestleMania / SummerSlam / Survivor Series / Armageddon / No Way Out / Backlash | 레슬매니아 / 서머슬램 / 서바이버 시리즈 / 아마겟돈 / 노 웨이 아웃 / 백래시 |
| Judgment Day / Vengeance / Unforgiven / No Mercy / Bad Blood / Insurrextion / Rebellion | 저지먼트 데이 / 벤전스 / 언포기븐 / 노 머시 / 배드 블러드 / 인서렉션 / 리벨리언 |
| memory card / Save / Load / Delete / Copy / Format | 메모리 카드 / 저장 / 불러오기 / 삭제 / 복사 / 포맷 |
| Select / Back / Cancel / Decision / Yes / No / OK | 선택 / 뒤로 / 취소 / 결정 / 예 / 아니요 / 확인 |
| ON / OFF / Random / Normal / Easy / Hard | 켜기 / 끄기 / 무작위 / 보통 / 쉬움 / 어려움 |
| Now Loading / Now Saving | 불러오는 중 / 저장 중 |
| Theater Mode / Shop Zone | 시어터 모드 / 숍 존 |

### 인물 이름 (대사·목록 공통)
The Rock 더 락 / Steve Austin 스티브 오스틴(Stone Cold 스톤 콜드) / Triple H 트리플 H / (The) Undertaker 언더테이커 /
Kurt Angle 커트 앵글 / Brock Lesnar 브록 레스너 / Goldberg 골드버그 / Chris Jericho 크리스 제리코 / Chris Benoit 크리스 벤와 /
Eddie Guerrero 에디 게레로 / Chavo Guerrero 차보 게레로 / Los Guerreros 로스 게레로스 / Rey Mysterio 레이 미스테리오 /
Rob Van Dam 롭 밴 댐(RVD) / Kane 케인 / Big Show 빅 쇼 / Edge 엣지 / Christian 크리스찬 / Booker T 부커 T / Goldust 골더스트 /
Batista 바티스타 / Randy Orton 랜디 오턴 / Ric Flair 릭 플레어 / Evolution 에볼루션 / Shawn Michaels 숀 마이클스 /
Hollywood Hulk Hogan 할리우드 헐크 호건 / Kevin Nash 케빈 내시 / Scott Steiner 스콧 스타이너 / John Cena 존 시나 /
Matt Hardy 맷 하디 / Jeff Hardy 제프 하디 / Lita 리타 / Trish Stratus 트리시 스트라터스 / Stacy Keibler 스테이시 키블러 /
Torrie Wilson 토리 윌슨 / Victoria 빅토리아 / Molly Holly 몰리 홀리 / Jazz 재즈 / Ivory 아이보리 / Sable 세이블 /
Stephanie McMahon 스테파니 맥마흔 / Vince McMahon 빈스 맥마흔(Mr. McMahon 미스터 맥마흔) / Eric Bischoff 에릭 비숍 /
Jim Ross 짐 로스(J.R.) / Jerry Lawler 제리 롤러(King 킹) / Michael Cole 마이클 콜 / Tazz 타즈 / Jonathan Coachman 조나단 코치맨 /
Earl Hebner 얼 헤브너 / Mike Chioda 마이크 키오다 / A-Train 에이트레인 / Albert 앨버트 / Al Snow 알 스노 / Bradshaw 브래드쇼 /
Faarooq 파룩 / Bubba Ray Dudley 버바 레이 더들리 / D-Von Dudley 디본 더들리 / Spike Dudley 스파이크 더들리 /
Dudley Boyz 더들리 보이즈 / Billy Kidman 빌리 키드먼 / Charlie Haas 찰리 하스 / Shelton Benjamin 셸턴 벤자민 /
Haas & Benjamin 하스 & 벤자민 / Hardcore Holly 하드코어 홀리 / The Hurricane 허리케인 / Lance Storm 랜스 스톰 /
Mark Henry 마크 헨리 / Maven 메이븐 / Rhyno 라이노 / Rico 리코 / Rikishi 리키시 / Rodney Mack 로드니 맥 /
Sean O'Haire 숀 오헤어 / Shawn Stasiak 숀 스타지악 / Steven Richards 스티븐 리처즈 / Tajiri 타지리 / Test 테스트 /
Ultimo Dragon 울티모 드래곤 / Val Venis 발 비니스 / William Regal 윌리엄 리걸 / X-Pac 엑스팩 / Tomcat 탐캣 /
Roddy Piper 로디 파이퍼 / Jimmy (Superfly) Snuka 지미 (슈퍼플라이) 스누카 / Ted DiBiase 테드 디비아시 /
The Million Dollar Man 밀리언 달러 맨 / Hawk 호크 / Animal 애니멀 / George Steele 조지 스틸 / Hillbilly Jim 힐빌리 짐 /
Iron Sheik 아이언 쉭 / Nicholai Volkoff 니콜라이 볼코프 / Sergeant Slaughter 서전트 슬로터 / Ultimate Warrior 얼티밋 워리어 /
DDP 다이아몬드 댈러스 페이지(DDP) / The Big Valbowski 빅 발보스키 / Theodore Long 시어도어 롱 / Paul Heyman 폴 헤이먼 /
Sgt. 서전트 / Mr. 미스터.

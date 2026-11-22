# Classic JRPG Project (Python Pygame)

> Python과 Pygame을 기반으로 한 고전 JRPG 스타일의 2D 턴제 게임 개발 기획서입니다.

---

## 📋 프로젝트 요약

| 항목 | 내용 |
| :--- | :--- |
| **프로젝트 유형** | 2D 픽셀 아트 기반 고전 JRPG |
| **핵심 기능** | 턴제 전투, 캐릭터 성장, 인벤토리, 필드 탐험, 세이브/로드 |
| **주요 기술** | Python 3, Pygame, SQLite, JSON, PyInstaller |
| **저장 방식** | 로컬 SQLite 데이터베이스 |
| **네트워크** | 초기 버전은 인터넷 및 클라우드 서버 불필요 |
| **배포 목표** | Windows 독립 실행형 EXE |

---

## 1. 프로젝트 개요

### 1.1 프로젝트명
* **가칭:** Classic JRPG Project

### 1.2 개발 목적
파이널 판타지, 드래곤 퀘스트 등 고전 JRPG에서 영감을 받아 턴제 전투, 캐릭터 성장, 아이템 관리, 필드 탐험 등의 기능을 제공하는 2D 게임을 개발합니다. 특정 상용 게임의 캐릭터·음악·그래픽을 복제하지 않고 독자적인 세계관과 적법하게 이용 가능한 리소스를 사용합니다.

### 1.3 핵심 개발 방향
* 16비트 레트로 픽셀 아트 스타일의 GUI 구현
* 턴제 전투 시스템 구축
* 캐릭터, 몬스터, 아이템 및 스킬 데이터 관리
* SQLite를 이용한 로컬 게임 데이터 저장
* JSON을 이용한 게임 콘텐츠 관리
* 클라우드 서버 없이 실행 가능한 구조 설계
* Windows EXE 형태의 독립 실행 프로그램 배포

---

## 2. 개발 환경 및 기술 스택

| 구분 | 기술 | 활용 목적 |
| :--- | :--- | :--- |
| **프로그래밍 언어** | Python 3 | 게임 로직 및 데이터 처리 |
| **게임 라이브러리** | Pygame | 2D 렌더링, 게임 루프, 입력 처리 |
| **데이터베이스** | SQLite | 플레이어 진행 데이터 및 세이브 관리 |
| **데이터 형식** | JSON | 캐릭터·몬스터·아이템·스킬 정의 |
| **맵 에디터** | Tiled | 필드 및 던전 타일맵 제작 |
| **맵 라이브러리** | PyTMX | Tiled 맵 데이터 로딩 |
| **그래픽 도구** | LibreSprite / Aseprite | 픽셀 아트 및 스프라이트 제작 |
| **배포 도구** | PyInstaller | Python 프로젝트의 EXE 패키징 |
| **사운드** | pygame.mixer | BGM 및 효과음 재생 |

---

## 3. 시스템 아키텍처

### 3.1 계층별 구성
* **GUI 계층:** 화면 표시 및 사용자 입력 (타이틀, 필드, 전투, 메뉴 UI)
* **게임 로직 계층:** 게임 규칙 및 상태 처리 (전투, 턴 관리, 인벤토리, 퀘스트)
* **데이터 계층:** 게임 콘텐츠 정의 (JSON 기반 캐릭터·몬스터·아이템 데이터)
* **저장소 계층:** 진행 상태 영속화 (SQLite 기반 세이브 및 로드)

### 3.2 권장 프로젝트 디렉터리 구조
```text
JRPG_Project/
├── main.py
├── engine/
│   ├── game_engine.py
│   ├── scene_manager.py
│   ├── state_manager.py
│   └── resource_manager.py
├── systems/
│   ├── battle_system.py
│   ├── turn_manager.py
│   ├── inventory_system.py
│   ├── quest_system.py
│   └── save_system.py
├── entities/
│   ├── character.py
│   ├── player.py
│   └── enemy.py
├── scenes/
│   ├── title_scene.py
│   ├── world_scene.py
│   ├── battle_scene.py
│   └── menu_scene.py
├── gui/
│   ├── battle_ui.py
│   ├── status_ui.py
│   ├── inventory_ui.py
│   └── dialogue_ui.py
├── assets/
│   ├── characters/
│   ├── monsters/
│   ├── maps/
│   ├── backgrounds/
│   ├── ui/
│   ├── bgm/
│   └── sounds/
├── data/
│   ├── characters.json
│   ├── monsters.json
│   ├── skills.json
│   └── items.json
└── saves/
    └── game.db
```
> **참고:** 개발 중에는 프로젝트 내부 `saves/` 폴더를 사용할 수 있습니다. 실제 배포 시에는 운영체제별 사용자 데이터 폴더에 데이터베이스를 저장하는 방식을 권장합니다.

---

## 4. 데이터베이스 및 데이터 관리 설계

### 4.1 JSON과 SQLite의 역할 구분
* **JSON (게임 콘텐츠 정의):** 캐릭터 기본 능력치, 몬스터, 아이템, 스킬, 맵 설정 등
* **SQLite (사용자 진행 데이터):** 현재 레벨·HP·MP, 보유 아이템, 장비, 퀘스트 진행, 세이브 슬롯 등

---

## 5. 주요 게임 기능

1. **전투 시스템:** 턴제 전투, 공격/방어/스킬/아이템, 몬스터 AI, 승패 판정
2. **캐릭터 시스템:** 레벨/경험치, 능력치(HP, MP, 공격력 등) 성장, 장비 관리
3. **인벤토리 시스템:** 아이템 획득/사용, 수량 관리, 장비 교체
4. **필드 탐험 시스템:** 타일 기반 필드/던전, 이동·충돌 처리, NPC 상호작용
5. **세이브 및 로드 시스템:** SQLite 기반 다중 세이브 슬롯 지원
6. **Undo / Redo 시스템:** Stack 자료구조를 이용한 상태 복원 및 재실행

---

## 6. 그래픽 및 외부 리소스 가이드

| 사이트 / 도구 | 활용 분야 | 주소 |
| :--- | :--- | :--- |
| **OpenGameArt** | 캐릭터, 몬스터, 타일셋, 음악, 효과음 | [Link](https://opengameart.org/) |
| **Kenney** | UI, 아이콘, 타일셋, 캐릭터 | [Link](https://kenney.nl/assets) |
| **itch.io** | 무료 RPG 픽셀 아트 및 타일맵 | [Link](https://itch.io/game-assets/free/genre-rpg/tag-pixel-art/tag-tilemap) |

> ⚠️ **라이선스 주의:** 무료 에셋이라도 상업적 이용, 수정, 재배포 조건이 다를 수 있습니다. 각 에셋의 라이선스를 확인하고 `ASSET_LICENSES` 문서에 반드시 기록해주세요.

---

## 7. 배포 및 실행 환경

* **패키징:** PyInstaller를 활용하여 Python 미설치 환경에서도 구동되는 Windows EXE 배포
* **파일 분리 원칙:**
  * `Game.exe`: PyInstaller 패키징
  * `assets/` & `data/`: 게임 버전과 함께 읽기 전용으로 배포
  * `game.db`: 사용자별 쓰기 가능한 외부 경로에 저장

---

## 8. 개발 단계 및 추진 순서

1. **1단계 (기본 환경):** Pygame 초기화, 게임 루프, 입력, Scene 전환, 기본 GUI
2. **2단계 (데이터 관리):** JSON 구조, SQLite 스키마, CRUD, 세이브/로드
3. **3단계 (전투 시스템):** 턴제 전투, 스킬/아이템, 몬스터 AI
4. **4단계 (필드 및 캐릭터):** 타일맵, 이동/충돌, NPC, 인벤토리/장비
5. **5단계 (리소스 적용):** 픽셀 아트, 애니메이션, BGM, 효과음
6. **6단계 (테스트 및 배포):** 기능 검증 및 EXE 빌드

---

## 9. 부록. 구현 전 확인 사항 (Checklist)
* [x] SQLite 테이블 간 기본키·외래키 및 관계 ERD 확정
* [x] 세이브 슬롯별 저장 범위 및 데이터 버전 정의
* [x] DB 마이그레이션 정책 마련
* [x] Undo / Redo 상태 범위 및 RNG 상태 처리 정책 정의
* [x] 외부 에셋 라이선스 및 출처 문서화

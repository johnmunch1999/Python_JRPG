# 세이브 데이터 형식 (2단계)

## 역할 구분
- `data/*.json` — 읽기 전용 게임 정의(캐릭터·몬스터·스킬·아이템·새 게임 초기값). 시작 시 `data_loader.load_all()`이 상호 참조를 검증.
- `saves/game.db` (SQLite) — 플레이어 진행 상황. 환경변수 `JRPG_SAVE_DB`로 경로 변경 가능(테스트·배포용).

## ERD (스키마 v2)
```
save_slots (slot PK)
 ├─< party_members (slot FK → save_slots ON DELETE CASCADE, position)  PK(slot, position)
 ├─< inventory     (slot FK → save_slots ON DELETE CASCADE, item_id)   PK(slot, item_id)
 └─< flags         (slot FK → save_slots ON DELETE CASCADE, flag)      PK(slot, flag)
```
- `save_slots`: data_version, saved_at, playtime, map, x, y, facing, gold
- `party_members`: char_id, level, exp, hp, mp, weapon, armor (id는 JSON 키를 참조)
- `inventory`: qty > 0 (장비 중이 아닌 무기·갑옷도 여기에 들어감)
- `flags`: 한 번만 일어나는 월드 이벤트. 예: `chest:<map>:<object name>` (v2에서 추가)

## 슬롯 저장 범위
슬롯 1~3. 파티(레벨·경험치·현재 HP/MP·장비), 소지금, 인벤토리, 맵·좌표·방향, 플레이 시간, 월드 플래그(열린 상자 등).
저장 시 해당 슬롯을 한 트랜잭션 안에서 삭제 후 다시 기록(반쯤 쓰인 슬롯 없음).

## 버전과 마이그레이션
- 이력: v1 초기 스키마 → v2 `flags` 테이블 추가. v1 DB는 처음 열 때 자동으로 v2로 올라감(`tools/save_test.py`에서 검증).
- **스키마 버전**: `PRAGMA user_version`. `save_system.MIGRATIONS[i]`가 v i → v i+1 업그레이드. 새 테이블·컬럼은 리스트 끝에 추가만 하고 기존 항목은 수정 금지. DB가 게임보다 새 버전이면 오류.
- **데이터 버전**: 슬롯별 `data_version`. 저장 내용의 의미가 바뀔 때 올리고 `load()`에서 변환.

## RNG / Undo
- RNG 상태는 저장하지 않음. 로드 후 인카운터 걸음 수는 새로 뽑음(세이브-로드 반복으로 결과를 바꿀 수 있는 것은 허용).
- Undo/Redo는 범위 외. 필요하면 3단계 전투 내부에서만 검토.

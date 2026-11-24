# Classic JRPG Project

pygame-ce로 만든 고전 스타일 턴제 JRPG입니다.

## 바로 실행하기 (Windows)

Python을 설치하지 않아도 됩니다.

1. [Releases 페이지](https://github.com/johnmunch1999/Python_JRPG/releases/latest)에서 `ClassicJRPG.exe`를 내려받습니다.
2. 원하는 폴더(예: `내 문서\ClassicJRPG`)에 넣고 더블클릭합니다.

- 세이브는 exe와 같은 폴더의 `saves\game.db`에 저장됩니다. 그래서 `Program Files`처럼 쓰기 권한이 없는 폴더에 두면 저장이 안 될 수 있습니다.
- 처음 실행할 때 Windows SmartScreen 경고가 나올 수 있습니다. 서명되지 않은 exe라서 그렇습니다. "추가 정보 → 실행"을 누르면 됩니다.
- exe는 저장소 파일에 포함되어 있지 않습니다. 용량이 커서(약 44MB) Releases에만 올립니다.

조작: 방향키 이동, `Z`/`Enter` 확인, `X`/`Esc` 취소

## 소스에서 실행하기

```
pip install -r requirements.txt
python main.py
```

## 실행 파일 직접 빌드하기

PyInstaller로 `assets`와 `data`를 모두 묶어 exe 하나를 만듭니다. 설정은 [game.spec](game.spec)에 있습니다.
`pygame`과 `pygame-ce`가 같이 깔려 있으면 충돌할 수 있으므로 가상환경에서 빌드하세요.

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt pyinstaller
.venv\Scripts\pyinstaller --noconfirm --clean game.spec
```

결과물은 `dist\ClassicJRPG.exe`에 생깁니다. (`build/`, `dist/`, `.venv/`는 git에서 제외됩니다.)

## 라이선스

사용한 에셋의 출처와 라이선스는 [ASSET_LICENSES.md](ASSET_LICENSES.md)에 정리되어 있습니다.

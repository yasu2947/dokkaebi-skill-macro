# 도깨비 스킬 매크로

한월 RPG 스타일 스킬바를 **이미지 매칭**으로 감지하고, 설정된 슬롯 키를 자동으로 입력하는 Windows 데스크톱 도구입니다.

---

## 📦 다운로드 & 실행 (EXE)

> GitHub Releases 탭에서 최신 버전을 받으세요.

1. `DokkaebiSkillMacro_vX.X.X.zip` 압축 해제
2. `DokkaebiSkillMacro` 폴더 안의 **`DokkaebiSkillMacro.exe`** 더블클릭
3. 처음 실행 시 `config.json`, `presets.json`, `templates/` 폴더가 **exe 옆에 자동 생성**됩니다

```
DokkaebiSkillMacro/          ← 이 폴더 전체를 아무 곳에나 두면 됩니다
├── DokkaebiSkillMacro.exe
├── config.json              (첫 실행 후 자동 생성)
├── presets.json             (프리셋 저장 시 자동 생성)
├── templates/               (슬롯 이미지 저장 위치)
└── _internal/               (PyInstaller 의존성, 건드리지 마세요)
```

---

## 🛠 개발 환경에서 실행

**요구 사항**: Windows 10/11, Python 3.10+

```powershell
cd dokkaebi-skill-macro
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m src.main
```

## 🔨 EXE 직접 빌드

```powershell
pip install -r requirements-dev.txt
.\build_exe.ps1
# 결과물: dist\DokkaebiSkillMacro\DokkaebiSkillMacro.exe
```

---

## 📖 사용 흐름

| 단계 | 내용 |
|------|------|
| 1 | 스킬 슬롯 메뉴에서 **템플릿 폴더(📁)** 버튼으로 이미지 폴더 열기 |
| 2 | **스킬바 ROI** 영역을 화면에서 드래그로 지정 |
| 3 | 슬롯 수(1~7) 및 각 슬롯 키 설정 |
| 4 | 게임에서 스킬 ON 상태일 때 「템플릿 저장」으로 `slot_01_ready.png` … 저장 |
| 5 | **1사이클 실행**: 매칭 임계값 이상 슬롯에 키 입력 후 자동 종료 |
| 6 | **중단** 버튼으로 언제든 정지 가능 |

### 키 입력 형식

- 키보드: `2`, `f`, `space`, `enter`, `shift`, `f1` …
- 마우스: `mouse4`, `mouse5`, `mb_left`, `mb_right`, `mb_middle`

---

## 📁 프로젝트 구조

```
dokkaebi-skill-macro/
├── src/
│   ├── app_meta.py          # 버전·체인지로그
│   ├── main.py              # 진입점 (python -m src.main)
│   ├── core/                # 캡처·매칭·설정·경로 로직
│   └── ui/                  # PyQt6 UI 컴포넌트
├── contents/
│   ├── font/                # Noto Sans KR 폰트
│   ├── images/              # 로고 (yasu.png, yasu.ico)
│   └── sounds/              # 쿨타임 알림음
├── exe_entry.py             # PyInstaller 진입점
├── build_exe.ps1            # 빌드 스크립트
├── requirements.txt
└── requirements-dev.txt
```

---

## ⚠️ 주의

- 온라인 게임 서버 규정·EULA를 확인 후 사용하세요. 자동 입력은 제재 대상이 될 수 있습니다.
- 관리자 권한 또는 전체 화면 독점 모드에서는 캡처/입력이 제한될 수 있습니다.

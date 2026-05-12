# 도깨비 스킬 매크로

한월 RPG 스킬바를 **이미지 매칭**으로 감지해 설정한 슬롯 키를 자동으로 입력하는 Windows 도구입니다.

---

## 다운로드

[**최신 릴리즈 → Releases**](https://github.com/yasu2947/dokkaebi-skill-macro/releases/latest)

`DokkaebiSkillMacro.exe` 한 파일만 받아서 실행하면 됩니다.  
처음 실행 시 설정 파일과 템플릿 폴더가 `%APPDATA%\DokkaebiSkillMacro\` 에 자동으로 생성됩니다.

---

## 사용법

### 1. 템플릿 이미지 준비

1. 사이드바 **스킬 슬롯** 탭으로 이동
2. 슬롯 수(1~7)와 각 슬롯에 입력할 키를 설정
3. **📁 버튼**으로 템플릿 폴더 열기
4. 게임에서 스킬이 **사용 가능한 상태**일 때 「템플릿 저장」 클릭  
   → `slot_01_ready.png`, `slot_02_ready.png` … 형태로 저장됨

### 2. ROI(인식 영역) 지정

- **스킬바 ROI**: 화면에서 스킬바 전체 영역을 드래그로 지정
- **슬롯 ROI** (선택): 각 슬롯을 개별 지정하면 인식 정확도가 올라감

### 3. 실행

| 모드 | 설명 |
|------|------|
| 1사이클 | 매칭된 슬롯에 키 입력 후 자동 종료 |
| 반복 | 매칭될 때마다 계속 입력 (중단 버튼으로 정지) |
| 레이드 | 두 스킬바를 번갈아 사용, 모든 스킬 발동 시 즉시 스왑 |

### 키 입력 형식

```
키보드: 2  f  space  enter  shift  f1  ctrl  alt ...
마우스: mouse4  mouse5  mb_left  mb_right  mb_middle
```

---

## 업데이트

앱 실행 후 사이드바 **버전 정보** 탭 → **업데이트 확인** 버튼  
새 버전이 있으면 다운로드 후 재시작하여 자동 적용됩니다.

---

## 개발 환경에서 실행

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m src.main
```

## EXE 직접 빌드

```powershell
pip install -r requirements-dev.txt
.\build_exe.ps1
# 결과물: dist\DokkaebiSkillMacro.exe
```

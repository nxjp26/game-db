# 기업DB 프로젝트 — 운영 규칙

## 프로젝트 개요

넥슨 재팬 기업개발팀의 일본 게임업계 M&A / 퍼블리싱 파트너 조사용 인텔리전스 대시보드 관리 프로젝트.

- **주 산출물**: `dashboard_v*.html` — 단일 자립형 HTML 대시보드 (외부 의존 없음)
- **배포**: 단일 HTML 파일 직접 공유 (Google Drive / 이메일 / 사내 파일서버). 서버·인터넷 연결 불필요
- **접근 제어**: HTML 내 비밀번호 gate (sessionStorage 기반)

---

## 폴더 구조

```
기업DB/
├── CLAUDE.md              ← 이 파일. 프로젝트 규칙
├── claude_en.md           ← AI 협업 원칙 (영문)
├── 설계서_v2.0.md         ← 시스템 설계서 (최신)
├── workflows/             ← 반복 작업 매뉴얼
│   └── update_dashboard.md
├── tools/                 ← Python 실행 스크립트
├── .tmp/                  ← 임시 파일 (gitignore)
├── .env                   ← API 키 등 시크릿 (gitignore)
└── dashboard_v*.html      ← 대시보드 산출물
```

---

## 데이터 규칙

- **기업명 표기**: 한국어 우선, 일본어 병기 — `드리콤 (ドリコム)` 형식
- **nk 필드**: 한국어 기업명. 없으면 `n` (일본어) fallback
- **버전 관리**: 파일명 `dashboard_v숫자.html` 형태. 이전 버전 보존

## M&A 분류 기준

- `O` = 매수가능 / `T` = 조건부 / `X` = 매수불가 / `N` = 미검토
- 분류 변경 시 반드시 `mr` (판단 근거) 필드 업데이트

## 보안

- 비밀번호는 HTML 파일 내 `GATE_HASH` 상수 (SHA-256 해시값)로 관리 — 평문 저장 금지
- 비밀번호 변경 방법: `node -e "require('crypto').createHash('sha256').update('새비밀번호').digest('hex')" | pbcopy` → 복사된 해시로 GATE_HASH 교체
- 현재 기본 비밀번호: nexon2026 (배포 전 변경 권장)
- `.env`, `credentials.json`, `token.json` 절대 커밋 금지
- ⚠️ GitHub Pages는 public 저장소이므로 소스코드 직접 접근 시 데이터 노출 가능. 민감도 높은 경우 private 저장소 + GitHub Pages 유료 플랜 사용 권장

## 업데이트 절차

`workflows/update_dashboard.md` 참조

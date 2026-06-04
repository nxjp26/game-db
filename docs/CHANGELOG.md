# Changelog

## v1.0.13 (2026-06-04) — V2 UI Enhancements

### V2 전용 기능 (기본값 OFF — `?ui=v2` 로 활성화)

**Ticket 1 — Drawer TL;DR + 액션 버튼**
- Drawer 상단에 TL;DR 2줄 블록 (포인트/리스크)
  - `tldr_point`, `tldr_risk` 필드 있으면 우선 사용, 없으면 기존 필드에서 heuristic 유도
- 액션 버튼 2개:
  - 📝 메모/태그: 인라인 에디터 패널 (태그 토글 + 자유 메모)
  - 🔗 출처 열기: `src_url` 있으면 새 탭, 없으면 disabled

**Ticket 2 — 태그 시스템 + URL 동기화**
- 고정 태그 5개: `관심 / NDA / 콜필요 / 보류 / 완료`
- 태그 저장: `localStorage: v2tags:<idx>`, `v2memo:<idx>`
- 카드에 최대 2개 태그 배지 표시
- 상단 태그 필터 바 (`#v2tagfilter`)
- URL `?tag=관심` 파라미터로 상태 유지·복원

**Ticket 3 — 변경이력 개선**
- 기간 토글: 7일 / 30일 / 전체 (날짜 메타 없으면 안내 메시지)
- 변경 타입 배지 자동 분류: CEO / 지표 / 출시 / M&A / 기타
- 항목 클릭 → V2 Drawer 바로 오픈

**Ticket 4 — 신뢰도 낮음 경고 UX**
- `confidence=Low` 시 재무 지표 옆 ⚠️ 아이콘
- `src_url` 없는 기록: 수치 muted(회색) 스타일

**Ticket 5 — 성능/UX 폴리시**
- 검색 디바운스 200ms
- 바텀시트 열릴 때 배경 스크롤 잠금 (`body.v2-lock`)
- URL `replaceState`로 history spam 방지

**Ticket 6 — Playwright 테스트 업데이트**
- V1 기본 테스트 4개 유지
- V2 테스트 9개 추가 (TL;DR, 태그, 변경이력, URL 복원 등)

---

## v1.0.12 (2026-06-04) — Phase 2 V2 UI 초기 구현

- V2 피처 플래그 도입 (`?ui=v2`)
- 스티키 상단바, 필터 칩, Drawer/BottomSheet
- 즐겨찾기(★ localStorage), URL 상태 관리
- 변경이력 뷰 기본 버전

## v1.0.11 (2026-06-04) — 데이터 품질 개선

- 기업 정보 한국어 복원 (배치1 탑20 일본어→한국어)
- 주주구조 인명 한국어 발음 표기

## v1.0.10 (2026-06-03) — Phase 0 기반 정리

- `data/기업DB.csv` 경로 고정
- `scripts/build_dashboard.py` 생성
- GitHub Actions CI (`validate-db.yml`, `smoke-test.yml`)
- `archive/dashboard_v3.html` 이동

---

## 수동 검증 방법

### V1 확인 (기본)
```
https://ishare.nexon.com/sites/jp-gamedb/
```
→ 기존 UI 그대로 표시됨

### V2 확인
```
https://ishare.nexon.com/sites/jp-gamedb/?ui=v2
```
1. **TL;DR**: 카드 클릭 → Drawer 상단 "포인트/리스크" 2줄
2. **태그**: 메모/태그 버튼 → 관심/NDA/콜필요/보류/완료 토글
3. **태그 필터**: 상단 태그 bar → 클릭 시 해당 태그 기업만 표시
4. **변경이력**: 상단 "📋 변경이력" 탭 → 기간 토글 + 타입 배지
5. **URL 상태**: 필터 변경 후 URL 복사·붙여넣기로 상태 복원 확인

# HTTP 기반 아키텍처 (아카이브)

**상태**: 아카이브됨 (사용 안 함)  
**대체**: NAS 기반 아키텍처로 변경

---

## 왜 아카이브되었나?

HTTP 업로드 방식은 다음 이유로 NAS 기반 방식으로 대체되었습니다:

- ❌ FastAPI 서버 필요 (복잡도 증가)
- ❌ 네트워크 에러 처리 복잡
- ❌ MD5 계산 & 검증 오버헤드
- ✅ NAS 파일 복사 방식이 훨씬 간단

---

## 이 폴더 내용

### server/
- `api.py`: FastAPI 기반 파일 업로드 서버

### client/
- `agent.py`: HTTP 업로드 클라이언트
- `config.example.json`: 클라이언트 설정 예시

### docs/
- `CLIENT_SERVER_COMPLETE_GUIDE.md`: HTTP 방식 설정 가이드

---

## 현재 사용 중인 아키텍처

**NAS 기반 아키텍처**를 사용하세요:
- 문서: `docs/NAS_ARCHITECTURE.md`
- 클라이언트: `client/nas_agent.py`
- 서버: `server/nas_processor.py`

---

참고용으로 보관됨.

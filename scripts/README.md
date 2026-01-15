# Scripts 디렉토리

LearningCollector 프로젝트의 스크립트 모음입니다. 용도별로 폴더가 구분되어 있습니다.

## 폴더 구조

```
scripts/
├── installation/     # 설치 시 사용하는 스크립트
├── runtime/          # 실행 시 사용하는 스크립트
├── systemd/          # systemd 서비스 설정 파일
└── maintenance/      # 유지보수 스크립트
```

---

## 1. installation/ - 설치 시 사용

프로젝트 초기 설치 및 설정에 사용하는 스크립트

### install.sh
**용도**: 전체 설치 프로세스 자동화
**실행 시점**: 프로젝트 최초 설치 시

```bash
bash scripts/installation/install.sh
```

**동작**:
1. Python 가상환경 생성
2. 의존성 설치 (requirements.txt)
3. .env 파일 생성
4. PostgreSQL 설정 (선택)
5. systemd timer 설정 (선택)

---

### setup-database.sh
**용도**: PostgreSQL 데이터베이스 및 스키마 설정
**실행 시점**: DB 초기 설정 시

```bash
bash scripts/installation/setup-database.sh
```

**동작**:
1. PostgreSQL 서비스 확인
2. 데이터베이스 생성
3. 스키마 생성 (create-schema.sql 실행)
4. 연결 테스트

---

### setup-daily-timer.sh
**용도**: systemd timer 설정 (매일 자동 수집)
**실행 시점**: 자동 수집 설정 시

```bash
bash scripts/installation/setup-daily-timer.sh
```

**동작**:
1. learningcollector-daily.service 복사 (/etc/systemd/system/)
2. learningcollector-daily.timer 복사 (/etc/systemd/system/)
3. Timer 활성화 및 시작
4. 다음 실행 시각 출력

---

### install-daemon.sh
**용도**: 실시간 파일 감지 daemon 설치
**실행 시점**: AI 채팅 파일 실시간 처리 설정 시

```bash
bash scripts/installation/install-daemon.sh
```

**동작**:
1. learningcollector.service 복사 (/etc/systemd/system/)
2. Daemon 활성화 및 시작
3. watchdog로 Downloads 폴더 모니터링

---

### create-schema.sql
**용도**: PostgreSQL 스키마 정의
**실행 방법**: setup-database.sh에서 자동 실행

```sql
-- 직접 실행 시
psql -h localhost -U your_user -d my_db -f scripts/installation/create-schema.sql
```

**내용**:
- `learning` 스키마 생성
- `learning_artifacts` 테이블 생성
- `github_commits` 테이블 생성
- `baekjoon_solutions` 테이블 생성
- `ai_chat_conversations` 테이블 생성

---

## 2. runtime/ - 실행 시 사용

실제 데이터 수집 및 처리에 사용하는 스크립트

### daily-collect.sh
**용도**: 일일 데이터 수집 (systemd timer에서 호출)
**실행 시점**: 매일 자정 (자동) 또는 수동 실행

```bash
# 수동 실행
bash scripts/runtime/daily-collect.sh
```

**동작**:
1. 가상환경 활성화
2. main.py 실행
3. 로그 기록 (logs/cron_날짜.log)
4. 성공/실패 상태 반환

---

### learningcollector-daemon.py
**용도**: 실시간 파일 감지 daemon (watchdog 사용)
**실행 시점**: systemd service로 백그라운드 실행

```bash
# 수동 실행 (테스트용)
python scripts/runtime/learningcollector-daemon.py
```

**동작**:
1. Downloads 폴더 감시
2. Claude/ChatGPT/Gemini .md 파일 감지
3. 자동으로 main.py 실행
4. 로그 기록 (logs/daemon.log)

---

## 3. systemd/ - systemd 서비스 설정

systemd 서비스 및 timer 정의 파일

### learningcollector-daily.service
**용도**: 일일 수집 서비스 정의
**설치 위치**: `/etc/systemd/system/learningcollector-daily.service`

```ini
[Unit]
Description=LearningCollector Daily Scan
After=postgresql.service

[Service]
Type=oneshot
User=your_user
WorkingDirectory=/home/your_user/LearningCollector
ExecStart=/home/your_user/LearningCollector/scripts/runtime/daily-collect.sh

[Install]
WantedBy=multi-user.target
```

---

### learningcollector-daily.timer
**용도**: 일일 수집 타이머 정의 (매일 자정 실행)
**설치 위치**: `/etc/systemd/system/learningcollector-daily.timer`

```ini
[Unit]
Description=LearningCollector Daily Timer

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

---

### learningcollector.service
**용도**: 실시간 daemon 서비스 정의
**설치 위치**: `/etc/systemd/system/learningcollector.service`

```ini
[Unit]
Description=LearningCollector Daemon
After=network.target postgresql.service

[Service]
Type=simple
User=your_user
WorkingDirectory=/home/your_user/LearningCollector
ExecStart=/home/your_user/LearningCollector/venv/bin/python /home/your_user/LearningCollector/scripts/runtime/learningcollector-daemon.py
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 4. maintenance/ - 유지보수

운영 중 유지보수에 사용하는 스크립트

### backup.sh
**용도**: PostgreSQL 데이터베이스 백업
**실행 주기**: 주기적으로 실행 (cron 또는 수동)

```bash
bash scripts/maintenance/backup.sh
```

**동작**:
1. PostgreSQL dump 생성
2. export/ 폴더에 저장 (날짜별)
3. 오래된 백업 자동 삭제 (30일 이상)

---

### healthcheck.py
**용도**: 시스템 상태 확인
**실행 시점**: 문제 진단 시 또는 주기적 모니터링

```bash
python scripts/maintenance/healthcheck.py
```

**확인 항목**:
1. PostgreSQL 연결 상태
2. 환경 변수 설정 (.env)
3. GitHub API 토큰 유효성
4. 백준허브 레포 접근 가능 여부
5. 최근 데이터 수집 시각
6. 디스크 공간

---

### test-installation.sh
**용도**: 설치 검증 테스트
**실행 시점**: 설치 완료 후 또는 문제 발생 시

```bash
bash scripts/maintenance/test-installation.sh
```

**테스트 항목**:
1. Python 버전 확인
2. 의존성 패키지 확인
3. .env 파일 존재 확인
4. DB 연결 테스트
5. systemd timer 상태 확인

---

## 사용 가이드

### 초기 설치 순서

```bash
# 1. 전체 설치
bash scripts/installation/install.sh

# 2. (자동으로 포함됨) DB 설정
# bash scripts/installation/setup-database.sh

# 3. (자동으로 포함됨) systemd timer 설정
# bash scripts/installation/setup-daily-timer.sh

# 4. 설치 검증
bash scripts/maintenance/test-installation.sh
```

### 일상적인 사용

**자동 수집 설정 시** (systemd timer):
```bash
# 아무것도 하지 않아도 매일 자정 자동 수집
# 상태 확인만 하면 됨
systemctl list-timers learningcollector-daily.timer
```

**수동 수집**:
```bash
# 직접 수집 스크립트 실행
bash scripts/runtime/daily-collect.sh
```

### 문제 발생 시

```bash
# 1. 시스템 상태 확인
python scripts/maintenance/healthcheck.py

# 2. 설치 검증
bash scripts/maintenance/test-installation.sh

# 3. 로그 확인
journalctl -u learningcollector-daily.service -n 20
```

---

## 경로 참조

다른 스크립트나 문서에서 이 스크립트들을 참조할 때:

```bash
# 설치 스크립트
scripts/installation/install.sh
scripts/installation/setup-database.sh
scripts/installation/setup-daily-timer.sh

# 런타임 스크립트
scripts/runtime/daily-collect.sh
scripts/runtime/learningcollector-daemon.py

# systemd 파일
scripts/systemd/learningcollector-daily.service
scripts/systemd/learningcollector-daily.timer
scripts/systemd/learningcollector.service

# 유지보수
scripts/maintenance/backup.sh
scripts/maintenance/healthcheck.py
scripts/maintenance/test-installation.sh
```

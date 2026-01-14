# 라즈베리파이 시스템 업데이트 가이드

## 개요

라즈베리파이에서 실행 중인 systemd 서비스/타이머를 안전하게 업데이트하는 방법을 설명합니다.

**주요 변경사항:**
- `LearningETL` → `개인 학습 정보 수집 자동화 도구` (Description 변경)
- `LearningCollector` 클래스명 변경 반영
- `collect_result_*.json` 로그 파일 형식 변경
- 파일 기반 날짜 추적 시스템 적용

---

## 사전 확인

### 1. 현재 상태 확인

```bash
# 타이머 상태 확인
sudo systemctl status learningetl-daily.timer

# 서비스 상태 확인
sudo systemctl status learningetl-daily.service

# 다음 실행 시간 확인
systemctl list-timers | grep learningetl
```

### 2. 최근 로그 확인

```bash
# 최근 수집 로그
sudo journalctl -u learningetl-daily.service --since "1 day ago"

# 수집 결과 파일 확인
ls -lh ~/LearningCollector/logs/*.json | tail -5
```

---

## 업데이트 절차

### Step 1: 저장소 업데이트

```bash
cd ~/LearningCollector  # 또는 ~/LearningETL (폴더명은 변경 안함)
git pull origin main
```

**주의:**
- 폴더명이 `LearningETL`이어도 괜찮습니다 (변경 불필요)
- GitHub 레포 이름만 `LearningCollector`로 변경되었습니다

### Step 2: 타이머/서비스 중지

```bash
# 타이머 중지 (새로운 작업 예약 방지)
sudo systemctl stop learningetl-daily.timer

# 현재 실행 중인 서비스 확인
sudo systemctl status learningetl-daily.service
```

### Step 3: systemd 파일 업데이트

```bash
cd ~/LearningCollector  # 또는 ~/LearningETL

# 현재 사용자 및 경로 확인
CURRENT_USER=$(whoami)
PROJECT_ROOT=$(pwd)

# service 파일 업데이트 ({{placeholder}} 치환)
sed -e "s|{{PROJECT_ROOT}}|$PROJECT_ROOT|g" \
    -e "s|{{USER}}|$CURRENT_USER|g" \
    scripts/systemd/learningetl-daily.service | \
    sudo tee /etc/systemd/system/learningetl-daily.service > /dev/null

# timer 파일 업데이트
sudo cp scripts/systemd/learningetl-daily.timer /etc/systemd/system/

# systemd 리로드
sudo systemctl daemon-reload
```

### Step 4: 서비스 재시작

```bash
# 타이머 시작
sudo systemctl start learningetl-daily.timer

# 상태 확인
sudo systemctl status learningetl-daily.timer
```

### Step 5: 수동 테스트 (선택사항)

```bash
# 즉시 수집 실행하여 테스트
sudo systemctl start learningetl-daily.service

# 실행 로그 실시간 확인
sudo journalctl -u learningetl-daily.service -f
```

---

## 검증

### 1. 타이머 정상 동작 확인

```bash
# 다음 실행 시간 확인 (자정으로 예약되어야 함)
systemctl list-timers learningetl-daily.timer
```

**예상 출력:**
```
NEXT                        LEFT          LAST                        PASSED  UNIT                        ACTIVATES
Wed 2026-01-15 00:00:00 KST 9h left       Tue 2026-01-14 00:00:00 KST 14h ago learningetl-daily.timer     learningetl-daily.service
```

### 2. 로그 파일 형식 확인

```bash
# 새로운 로그 파일 형식 확인
ls ~/LearningCollector/logs/collect_result_*.json

# 기존 로그 파일도 인식되는지 확인
ls ~/LearningCollector/logs/etl_result_*.json
```

**참고:** 두 형식 모두 정상적으로 인식됩니다 (하위 호환성 유지)

### 3. Description 변경 확인

```bash
# systemd에서 새로운 Description 확인
systemctl status learningetl-daily.timer
systemctl status learningetl-daily.service
```

**예상 출력:**
```
● learningetl-daily.timer - 개인 학습 정보 수집 자동화 도구 - 일일 실행 타이머
   Loaded: loaded (/etc/systemd/system/learningetl-daily.timer; enabled; vendor preset: enabled)
   Active: active (waiting) since ...
```

---

## 문제 해결

### Q1: 타이머가 시작되지 않습니다

```bash
# 상세 로그 확인
sudo journalctl -u learningetl-daily.timer -n 50

# 타이머 재활성화
sudo systemctl enable learningetl-daily.timer
sudo systemctl start learningetl-daily.timer
```

### Q2: 서비스 실행이 실패합니다

```bash
# 에러 로그 확인
sudo journalctl -u learningetl-daily.service -n 50

# daily-collect.sh 직접 실행하여 테스트
cd ~/LearningCollector  # 또는 ~/LearningETL
bash scripts/runtime/daily-collect.sh
```

### Q3: 가상환경 관련 에러

```bash
# venv 경로 확인
ls -la ~/LearningCollector/venv/bin/activate

# venv 재생성 (필요 시)
cd ~/LearningCollector
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Q4: 이전 로그 파일이 보이지 않습니다

**원인:** 파일명 변경으로 인해 혼동 가능

**해결:**
```bash
# 모든 결과 파일 확인
ls ~/LearningCollector/logs/*.json

# 기존 etl_result_*.json 파일을 collect_result_*.json으로 변경 (선택사항)
cd ~/LearningCollector/logs/
for file in etl_result_*.json; do
    [ -f "$file" ] && mv "$file" "${file/etl_result/collect_result}"
done
```

**참고:** 변경하지 않아도 시스템은 정상 작동합니다 (하위 호환)

---

## CLI 업데이트 사항

CLI 도구도 업데이트되었습니다:

```bash
# 통계 확인 (Description 변경됨)
python cli.py stats

# 기존 명령어는 모두 동일하게 작동
python cli.py list github
python cli.py list baekjoon
python cli.py list ai-chat
```

---

## 롤백 방법 (문제 발생 시)

### 1. 이전 버전으로 복원

```bash
cd ~/LearningCollector
git log --oneline -10  # 커밋 목록 확인
git reset --hard <이전_커밋_해시>  # 특정 커밋으로 복원
```

### 2. systemd 파일 재설치

```bash
# Step 3 재실행
sudo systemctl daemon-reload
sudo systemctl restart learningetl-daily.timer
```

---

## 자동 업데이트 스크립트 (선택사항)

향후 업데이트를 간편하게 하려면 스크립트를 사용하세요:

```bash
#!/bin/bash
# update-system.sh

set -e

cd ~/LearningCollector  # 또는 ~/LearningETL

echo "1. Git pull..."
git pull origin main

echo "2. 타이머 중지..."
sudo systemctl stop learningetl-daily.timer

echo "3. systemd 파일 업데이트..."
CURRENT_USER=$(whoami)
PROJECT_ROOT=$(pwd)

sed -e "s|{{PROJECT_ROOT}}|$PROJECT_ROOT|g" \
    -e "s|{{USER}}|$CURRENT_USER|g" \
    scripts/systemd/learningetl-daily.service | \
    sudo tee /etc/systemd/system/learningetl-daily.service > /dev/null

sudo cp scripts/systemd/learningetl-daily.timer /etc/systemd/system/

echo "4. systemd 리로드..."
sudo systemctl daemon-reload

echo "5. 타이머 재시작..."
sudo systemctl start learningetl-daily.timer

echo "완료! 상태 확인:"
systemctl list-timers learningetl-daily.timer
```

**사용법:**
```bash
chmod +x update-system.sh
./update-system.sh
```

---

## 참고 자료

- [How_daemon_works.md](../How_daemon_works.md) - 시스템 동작 구조
- [COLLECTION_DATE_TRACKING.md](COLLECTION_DATE_TRACKING.md) - 날짜 추적 메커니즘
- [ARCHITECTURE_EVOLUTION.md](ARCHITECTURE_EVOLUTION.md) - 아키텍처 변경 내역

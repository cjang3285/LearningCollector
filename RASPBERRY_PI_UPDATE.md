# 라즈베리파이 업데이트 가이드

## 간단 업데이트 절차

### 1. 기존 타이머/서비스 중지 및 제거

```bash
# 타이머/서비스 중지
sudo systemctl stop learningetl-daily.timer
sudo systemctl stop learningetl-daily.service

# 비활성화
sudo systemctl disable learningetl-daily.timer

# 기존 파일 제거
sudo rm /etc/systemd/system/learningetl-daily.timer
sudo rm /etc/systemd/system/learningetl-daily.service
```

### 2. 폴더명 변경 (필수)

```bash
# 프로젝트 폴더명 변경
cd ~
mv LearningETL LearningCollector
cd LearningCollector
```

### 3. 코드 업데이트

```bash
# Git pull
git pull origin main
```

### 4. 새로운 타이머/서비스 설치

```bash
# 현재 사용자 및 경로 확인
CURRENT_USER=$(whoami)
PROJECT_ROOT=$(pwd)

# service 파일 설치
sed -e "s|{{PROJECT_ROOT}}|$PROJECT_ROOT|g" \
    -e "s|{{USER}}|$CURRENT_USER|g" \
    scripts/systemd/learningcollector-daily.service | \
    sudo tee /etc/systemd/system/learningcollector-daily.service > /dev/null

# timer 파일 설치
sudo cp scripts/systemd/learningcollector-daily.timer /etc/systemd/system/

# systemd 리로드
sudo systemctl daemon-reload

# 타이머 활성화 및 시작
sudo systemctl enable learningcollector-daily.timer
sudo systemctl start learningcollector-daily.timer
```

### 5. 확인

```bash
# 타이머 상태 확인
systemctl list-timers learningcollector-daily.timer

# 상세 상태
sudo systemctl status learningcollector-daily.timer

# 수동 테스트 (선택사항)
sudo systemctl start learningcollector-daily.service
sudo journalctl -u learningcollector-daily.service -f
```

---

## 예상 출력

```
NEXT                        LEFT          LAST                        PASSED  UNIT                            ACTIVATES
Wed 2026-01-15 00:00:00 KST 9h left       -                           -       learningcollector-daily.timer   learningcollector-daily.service
```

```
● learningcollector-daily.timer - LearningCollector - Daily Collection Timer
   Loaded: loaded (/etc/systemd/system/learningcollector-daily.timer; enabled)
   Active: active (waiting) since ...
```

---

## 주요 변경사항

- **파일명**: `learningetl-daily.*` → `learningcollector-daily.*`
- **폴더명**: `~/LearningETL` → `~/LearningCollector`
- **Description**: 한글 → `LearningCollector - ...`
- **로그 형식**: `etl_result_*.json` → `collect_result_*.json` (하위 호환)

---

## 일상 사용 명령어

```bash
# 타이머 상태
systemctl list-timers learningcollector-daily.timer

# 서비스 로그
sudo journalctl -u learningcollector-daily.service --since today

# 수집 결과 파일
ls ~/LearningCollector/logs/collect_result_*.json

# 수동 실행
sudo systemctl start learningcollector-daily.service
```

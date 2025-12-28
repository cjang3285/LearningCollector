# 아키텍처 설계 변경 기록 (2025-12-28)

## 핵심 변경 사항
- Selenium 직접 크롤링 방식 폐기
- GitHub API를 통한 Push-Pull 모델 채택
- 백준허브(BaekjoonHub) 및 Claude Export 도구 연동

## 브랜치 생성 목적
- 기존 Selenium 의존성 제거 및 GitHub 기반 수집 로직(Puller) 신설을 위한 베이스 브랜치

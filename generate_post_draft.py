#!/usr/bin/env python3
"""
블로그 포스트 초안 생성기

data/{날짜}.json 파일을 읽어서 Claude API로 블로그 초안 생성
핵심 논점과 의사결정 과정만 추출
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

import json
from datetime import date, datetime
from typing import Dict, List
import anthropic

from config.settings import get_log_file
from config.logging_config import setup_logging

# 로깅 설정
logger = setup_logging(get_log_file('generate_post'), __name__)

# 데이터 디렉토리
DATA_DIR = PROJECT_ROOT / 'data'

# Claude API 키
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')


def load_daily_data(target_date: date) -> Dict:
    """날짜별 수집 데이터 로드"""
    file_path = DATA_DIR / f'{target_date}.json'

    if not file_path.exists():
        raise FileNotFoundError(f"데이터 파일이 없습니다: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def format_github_commits(commits: List[Dict]) -> str:
    """GitHub 커밋을 텍스트로 포맷"""
    if not commits:
        return "오늘 커밋 없음"

    lines = []
    for commit in commits:
        repo = commit['repo']
        message = commit['message'].split('\n')[0]  # 첫 줄만
        lines.append(f"- [{repo}] {message}")

    return "\n".join(lines)


def format_ai_conversations(conversations: List[Dict]) -> str:
    """AI 대화를 텍스트로 포맷"""
    if not conversations:
        return "오늘 AI 대화 없음"

    lines = []
    for conv in conversations:
        provider = conv['provider'].capitalize()
        msg_count = len(conv['messages'])
        code_count = len(conv['code_blocks'])

        lines.append(f"\n### {provider} 대화 (메시지 {msg_count}개, 코드 {code_count}개)")

        # 전체 대화 내용 추가
        for i, msg in enumerate(conv['messages'], 1):
            role = "사용자" if msg['role'] == 'user' else "AI"
            content = msg['content']
            # 너무 길면 앞부분만 (블로그 초안 생성 시 전체를 Claude에게 주기 위함)
            lines.append(f"\n**[{role} {i}]**\n{content}\n")

    return "\n".join(lines)


def format_baekjoon_solutions(solutions: List[Dict]) -> str:
    """Baekjoon 풀이를 텍스트로 포맷"""
    if not solutions:
        return "오늘 백준 풀이 없음"

    lines = []
    for sol in solutions:
        problem_id = sol.get('id', 'N/A')
        title = sol.get('title', 'Untitled')
        tier = sol.get('tier', 'Unknown')
        lang = sol.get('language', 'Unknown')

        lines.append(f"- [{tier}] {problem_id}. {title} ({lang})")

    return "\n".join(lines)


def create_prompt(data: Dict, target_date: date) -> str:
    """Claude에게 보낼 프롬프트 생성"""
    github = data.get('github', {})
    ai_chat = data.get('ai_chat', {})
    baekjoon = data.get('baekjoon', {})

    commits_text = format_github_commits(github.get('commits', []))
    conversations_text = format_ai_conversations(ai_chat.get('conversations', []))
    solutions_text = format_baekjoon_solutions(baekjoon.get('solutions', []))

    prompt = f"""오늘({target_date}) 하루 동안의 학습 활동 데이터입니다. 이를 바탕으로 블로그 포스트 초안을 작성해주세요.

# 오늘의 학습 활동

## GitHub 커밋
{commits_text}

## AI와의 대화
{conversations_text}

## 백준 문제 풀이
{solutions_text}

---

위 데이터를 바탕으로 다음 형식의 블로그 포스트 초안을 작성해주세요:

**요구사항:**
1. **핵심 논점과 의사결정 과정에 집중**
   - AI와의 대화에서 주요 논의 주제 추출
   - 중요한 의사결정 지점과 그 이유
   - 기술적 고민과 해결 방법

2. **간결하고 명확하게**
   - 불필요한 상세 내용 제외
   - 핵심만 남기기
   - 마크다운 형식

3. **구조:**
   ```markdown
   # {target_date} 학습 일지

   ## 오늘의 핵심 주제
   [1-2 문장으로 오늘의 학습 주제 요약]

   ## 주요 활동

   ### 개발 작업
   [GitHub 커밋 기반 활동 요약]

   ### 학습 및 토론
   [AI 대화에서의 핵심 논점 및 의사결정]
   - 논의 주제: ...
   - 주요 의사결정: ...
   - 배운 점: ...

   ### 문제 해결
   [백준 문제 풀이 요약]

   ## 오늘의 배움
   [핵심 인사이트 2-3개]

   ## 내일 할 일
   [다음 학습 방향 또는 TODO]
   ```

위 형식으로 초안을 작성해주세요. 대화 내용을 그대로 나열하지 말고, 핵심 논점과 의사결정만 추출하세요."""

    return prompt


def generate_draft(data: Dict, target_date: date) -> str:
    """Claude API로 블로그 초안 생성"""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다")

    logger.info("Claude API로 블로그 초안 생성 중...")

    # Prompt 생성
    prompt = create_prompt(data, target_date)

    # Claude API 호출
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    draft = message.content[0].text
    logger.info("블로그 초안 생성 완료")

    return draft


def save_draft(draft: str, target_date: date) -> Path:
    """블로그 초안을 파일로 저장"""
    file_path = DATA_DIR / f'post_draft_{target_date}.md'

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(draft)

    logger.info(f"블로그 초안 저장 완료: {file_path}")
    return file_path


def main():
    """메인 함수"""
    import argparse

    parser = argparse.ArgumentParser(
        description='블로그 포스트 초안 생성',
        epilog='''
사용 예시:
  # 오늘 데이터로 초안 생성
  python generate_post_draft.py

  # 특정 날짜 데이터로 초안 생성
  python generate_post_draft.py --date 2026-01-15
        '''
    )
    parser.add_argument('--date', type=str, help='날짜 (YYYY-MM-DD)')

    args = parser.parse_args()

    # 날짜 파싱
    target_date = date.today()
    if args.date:
        target_date = datetime.strptime(args.date, '%Y-%m-%d').date()

    try:
        logger.info(f"="*60)
        logger.info(f"블로그 초안 생성 시작 - {target_date}")
        logger.info(f"="*60)

        # 데이터 로드
        data = load_daily_data(target_date)

        # 초안 생성
        draft = generate_draft(data, target_date)

        # 파일 저장
        file_path = save_draft(draft, target_date)

        logger.info(f"\n✅ 완료!")
        logger.info(f"파일: {file_path}")

        # 미리보기 출력
        print("\n" + "="*60)
        print("블로그 초안 미리보기")
        print("="*60)
        print(draft[:500] + "..." if len(draft) > 500 else draft)
        print("="*60)

        sys.exit(0)

    except FileNotFoundError as e:
        logger.error(f"파일을 찾을 수 없습니다: {e}")
        logger.info("먼저 main.py를 실행하여 데이터를 수집하세요")
        sys.exit(1)

    except Exception as e:
        logger.error(f"초안 생성 실패: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

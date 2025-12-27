#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
전체 ETL 파이프라인 테스트

테스트 항목:
1. GitHub 데이터 수집 (Export → Parse → DB Save)
2. Baekjoon 데이터 수집 (Export → Parse → DB Save)
3. Claude 데이터 수집 (Export → Parse → DB Save)
4. DB 저장 결과 검증

각 Collector는 이미 전체 파이프라인을 처리합니다:
- Export: API/Playwright로 원본 데이터 수집
- Parse: 데이터 파싱 및 구조화
- Save: DB에 Learning Artifacts로 저장

로그: temp/pipeline_test.log
결과: temp/pipeline_test_result.json
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, date

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 로그 설정
LOG_FILE = PROJECT_ROOT / 'temp' / 'pipeline_test.log'
RESULT_FILE = PROJECT_ROOT / 'temp' / 'pipeline_test_result.json'

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def test_github_collector():
    """GitHub 데이터 수집 테스트 (Export → Parse → DB)"""
    logger.info("=" * 60)
    logger.info("1. GitHub 데이터 수집 테스트")
    logger.info("=" * 60)

    try:
        from collectors.github_collector import GitHubCollector

        collector = GitHubCollector()
        result = collector.collect()

        if result.get('success'):
            logger.info(f"✅ GitHub 수집 성공!")
            logger.info(f"   커밋 수: {result.get('commits_count', 0)}")
            logger.info(f"   저장된 아티팩트: {len(result.get('artifact_ids', []))}개")
            logger.info(f"   아티팩트 ID: {result.get('artifact_ids', [])}")
        else:
            logger.warning(f"⚠️  GitHub 수집 실패: {result.get('error', 'Unknown error')}")

        return result

    except Exception as e:
        logger.error(f"❌ GitHub 수집 에러: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'commits_count': 0,
            'artifact_ids': []
        }


def test_baekjoon_collector():
    """Baekjoon 데이터 수집 테스트 (Export → Parse → DB)"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("2. Baekjoon 데이터 수집 테스트")
    logger.info("=" * 60)

    try:
        from collectors.baekjoon_collector import BaekjoonCollector

        collector = BaekjoonCollector()
        result = collector.collect()

        if result.get('success'):
            logger.info(f"✅ Baekjoon 수집 성공!")
            logger.info(f"   문제 수: {result.get('solutions_count', 0)}")
            logger.info(f"   저장된 아티팩트: {len(result.get('artifact_ids', []))}개")
            logger.info(f"   아티팩트 ID: {result.get('artifact_ids', [])}")
        else:
            logger.warning(f"⚠️  Baekjoon 수집 실패: {result.get('error', 'Unknown error')}")

        return result

    except Exception as e:
        logger.error(f"❌ Baekjoon 수집 에러: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'solutions_count': 0,
            'artifact_ids': []
        }


def test_claude_collector():
    """Claude 데이터 수집 테스트 (Export → Parse → DB)"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("3. Claude 데이터 수집 테스트")
    logger.info("=" * 60)

    try:
        from collectors.claude_collector import ClaudeCollector

        collector = ClaudeCollector()
        result = collector.collect()

        if result.get('success'):
            logger.info(f"✅ Claude 수집 성공!")
            logger.info(f"   대화 수: {result.get('conversations_count', 0)}")
            logger.info(f"   저장된 아티팩트: {len(result.get('artifact_ids', []))}개")
            logger.info(f"   아티팩트 ID: {result.get('artifact_ids', [])}")
        else:
            logger.warning(f"⚠️  Claude 수집 실패: {result.get('error', 'Unknown error')}")

        return result

    except Exception as e:
        logger.error(f"❌ Claude 수집 에러: {e}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'conversations_count': 0,
            'artifact_ids': []
        }


def verify_db_data(results):
    """DB에 저장된 데이터 검증"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("4. DB 저장 데이터 검증")
    logger.info("=" * 60)

    try:
        import psycopg2
        from config.settings import get_db_config

        # PostgreSQL 연결
        db_config = get_db_config()
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        # 오늘 날짜의 아티팩트 조회
        today = date.today()

        cursor.execute("""
            SELECT
                source_type,
                COUNT(*) as count,
                array_agg(id) as ids
            FROM learning.learning_artifacts
            WHERE DATE(artifact_date) = %s
            GROUP BY source_type
        """, (today,))

        db_results = cursor.fetchall()
        conn.close()

        logger.info("DB 저장 현황:")
        verification = {}

        for row in db_results:
            artifact_type, count, ids = row
            logger.info(f"   {artifact_type}: {count}개 (ID: {ids})")
            verification[artifact_type] = {
                'count': count,
                'ids': [str(id) for id in ids] if ids else []
            }

        return {
            'success': True,
            'verification': verification
        }

    except Exception as e:
        logger.error(f"❌ DB 검증 실패: {e}", exc_info=True)
        logger.info("   (DB가 설정되지 않았거나 연결할 수 없습니다)")
        return {
            'success': False,
            'error': str(e)
        }


def save_test_result(results):
    """테스트 결과 저장"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("테스트 결과 저장")
    logger.info("=" * 60)

    with open(RESULT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    logger.info(f"💾 결과 파일: {RESULT_FILE}")


def main():
    """메인 테스트 함수"""
    logger.info("=" * 60)
    logger.info("전체 ETL 파이프라인 테스트 시작")
    logger.info(f"시작 시간: {datetime.now()}")
    logger.info("=" * 60)

    results = {
        'timestamp': datetime.now().isoformat(),
        'tests': {}
    }

    # 1. GitHub 테스트
    results['tests']['github'] = test_github_collector()

    # 2. Baekjoon 테스트
    results['tests']['baekjoon'] = test_baekjoon_collector()

    # 3. Claude 테스트
    results['tests']['claude'] = test_claude_collector()

    # 4. DB 검증
    results['tests']['db_verification'] = verify_db_data(results)

    # 결과 저장
    save_test_result(results)

    # 요약
    logger.info("")
    logger.info("=" * 60)
    logger.info("테스트 요약")
    logger.info("=" * 60)

    for name, result in results['tests'].items():
        if name == 'db_verification':
            status = "✅" if result.get('success') else "❌"
            logger.info(f"{status} {name}: {result.get('verification', {})}")
        else:
            status = "✅" if result.get('success') else "❌"

            # 각 collector마다 다른 count 키 사용
            if name == 'github':
                count = result.get('commits_count', 0)
            elif name == 'baekjoon':
                count = result.get('solutions_count', 0)
            elif name == 'claude':
                count = result.get('conversations_count', 0)
            else:
                count = 0

            artifact_count = len(result.get('artifact_ids', []))
            logger.info(f"{status} {name}: {count}개 수집, {artifact_count}개 저장")

    logger.info("")
    logger.info(f"로그: {LOG_FILE}")
    logger.info(f"결과: {RESULT_FILE}")
    logger.info("=" * 60)


if __name__ == '__main__':
    main()

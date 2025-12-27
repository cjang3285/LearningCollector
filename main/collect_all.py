#!/usr/bin/env python3
"""
Learning Data Collector

모든 소스(Claude, GitHub, 백준)에서 당일 활동을 수집하고
하나의 데이터 덩어리로 통합합니다.
"""

import json
from datetime import datetime, timezone
from typing import Dict, Any
from pathlib import Path

# 각 소스 import
from parse.claude_parse import ClaudeParser
from sources.github_export import GitHubExporter
from sources.github_parse import GitHubParser
from sources.baekjoon_export import BaekjoonExporter
from sources.baekjoon_parse import BaekjoonParser


class LearningCollector:
    """학습 데이터 통합 수집기"""
    
    def __init__(self):
        self.output_dir = Path.home() / "learning-data"
        self.output_dir.mkdir(exist_ok=True)
    
    def collect_claude(self, zip_path: str) -> Dict:
        """Claude 대화 수집 (수동 다운로드한 ZIP 파일 파싱)"""
        print("\n=== Claude 대화 수집 ===")

        try:
            if not zip_path:
                print("❌ Claude ZIP 파일 경로가 제공되지 않았습니다.")
                return {'success': False, 'data': [], 'error': 'ZIP 파일 경로 필요'}

            # Parse
            parser = ClaudeParser()
            conversations = parser.parse_zip(zip_path)
            
            # 오늘 대화만 필터
            from datetime import timedelta
            now = datetime.now(timezone.utc)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            filtered = parser.filter_by_date(
                conversations,
                after=today_start,
                before=now,
                min_messages=2
            )
            
            # 파싱
            parsed_data = []
            for conv in filtered:
                parsed_data.append(parser.parse_conversation(conv).to_dict())
            
            print(f"✅ Claude: {len(parsed_data)}개 대화")
            
            return {
                'success': True,
                'count': len(parsed_data),
                'data': parsed_data
            }
            
        except Exception as e:
            print(f"❌ Claude 수집 실패: {e}")
            return {'success': False, 'error': str(e), 'data': []}
    
    def collect_github(self) -> Dict:
        """GitHub 커밋 수집"""
        print("\n=== GitHub 커밋 수집 ===")
        
        try:
            # Export
            exporter = GitHubExporter()
            commits = exporter.export_today()
            
            # Parse
            parser = GitHubParser()
            parsed_data = []
            for commit in commits:
                parsed_data.append(parser.parse_commits([commit])[0].to_dict())
            
            summary = parser.get_summary(parsed_data)
            
            print(f"✅ GitHub: {summary['total_commits']}개 커밋, "
                  f"{summary['total_repos']}개 저장소")
            
            return {
                'success': True,
                'count': summary['total_commits'],
                'summary': summary,
                'data': parsed_data
            }
            
        except Exception as e:
            print(f"❌ GitHub 수집 실패: {e}")
            return {'success': False, 'error': str(e), 'data': []}
    
    def collect_baekjoon(self) -> Dict:
        """백준 문제 풀이 수집"""
        print("\n=== 백준 문제 풀이 수집 ===")
        
        try:
            # Export
            exporter = BaekjoonExporter()
            problems = exporter.export_today()
            
            # Parse
            parser = BaekjoonParser()
            parsed_data = []
            for problem in problems:
                parsed_data.append(parser.parse_problems([problem])[0].to_dict())
            
            summary = parser.get_summary(parsed_data)
            
            print(f"✅ 백준: {summary['total_problems']}개 문제")
            
            return {
                'success': True,
                'count': summary['total_problems'],
                'summary': summary,
                'data': parsed_data
            }
            
        except Exception as e:
            print(f"❌ 백준 수집 실패: {e}")
            return {'success': False, 'error': str(e), 'data': []}
    
    def collect_all(self, claude_zip: str = None) -> Dict[str, Any]:
        """모든 소스에서 데이터 수집"""
        print(f"\n{'='*60}")
        print(f"Learning Data Collection - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        # 각 소스 수집
        claude_result = self.collect_claude(claude_zip)
        github_result = self.collect_github()
        baekjoon_result = self.collect_baekjoon()
        
        # 통합 데이터
        integrated_data = {
            'metadata': {
                'collected_at': datetime.now(timezone.utc).isoformat(),
                'date': datetime.now().strftime('%Y-%m-%d')
            },
            'claude': claude_result,
            'github': github_result,
            'baekjoon': baekjoon_result,
            'summary': {
                'total_activities': (
                    claude_result['count'] +
                    github_result['count'] +
                    baekjoon_result['count']
                ),
                'conversations': claude_result['count'],
                'commits': github_result['count'],
                'problems': baekjoon_result['count']
            }
        }
        
        # 파일 저장
        output_file = self.output_dir / f"learning-{datetime.now().strftime('%Y%m%d')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(integrated_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n{'='*60}")
        print(f"📊 수집 완료")
        print(f"{'='*60}")
        print(f"총 활동: {integrated_data['summary']['total_activities']}개")
        print(f"  - 대화: {integrated_data['summary']['conversations']}개")
        print(f"  - 커밋: {integrated_data['summary']['commits']}개")
        print(f"  - 문제: {integrated_data['summary']['problems']}개")
        print(f"\n💾 저장: {output_file}")
        print(f"{'='*60}\n")
        
        return integrated_data


if __name__ == '__main__':
    import sys
    
    collector = LearningCollector()
    
    # Claude ZIP 경로를 인자로 받을 수 있음
    zip_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    result = collector.collect_all(zip_path)

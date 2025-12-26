#!/usr/bin/env python3
"""
백준 파서

수집된 백준 문제 풀이 데이터를 파싱하여 구조화합니다.
코드에서 주석을 추출하고 분석합니다.
"""

import re
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict, field


@dataclass
class CodeComment:
    """코드 주석 데이터"""
    line_number: int
    comment_type: str  # 'single' | 'multi' | 'docstring'
    content: str
    
    def to_dict(self):
        return asdict(self)


@dataclass
class CodeAnalysis:
    """코드 분석 결과"""
    language: str
    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int
    comments: List[CodeComment] = field(default_factory=list)
    
    def to_dict(self):
        return {
            'language': self.language,
            'total_lines': self.total_lines,
            'code_lines': self.code_lines,
            'comment_lines': self.comment_lines,
            'blank_lines': self.blank_lines,
            'comments': [c.to_dict() for c in self.comments]
        }


@dataclass
class ProblemData:
    """파싱된 문제 데이터"""
    problem_id: int
    title: str
    level: int
    tier: str
    tags: List[str]
    url: str
    submission: Dict = None  # 제출 정보 (있는 경우)
    code_analysis: CodeAnalysis = None  # 코드 분석 (있는 경우)
    
    def to_dict(self):
        result = {
            'problem_id': self.problem_id,
            'title': self.title,
            'level': self.level,
            'tier': self.tier,
            'tags': self.tags,
            'url': self.url
        }
        
        if self.submission:
            result['submission'] = self.submission
        
        if self.code_analysis:
            result['code_analysis'] = self.code_analysis.to_dict()
        
        return result


class CommentExtractor:
    """코드에서 주석 추출"""
    
    @staticmethod
    def extract_python(code: str) -> List[CodeComment]:
        """Python 주석 추출"""
        comments = []
        lines = code.split('\n')
        
        in_multiline = False
        multiline_start = 0
        multiline_content = []
        quote_char = None
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # 멀티라인 주석 처리 (""" 또는 ''')
            if not in_multiline:
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    quote_char = '"""' if stripped.startswith('"""') else "'''"
                    in_multiline = True
                    multiline_start = i
                    multiline_content = [stripped[3:]]
                    
                    # 같은 줄에 끝나는 경우
                    if stripped.endswith(quote_char) and len(stripped) > 6:
                        in_multiline = False
                        comments.append(CodeComment(
                            line_number=i,
                            comment_type='docstring',
                            content=stripped[3:-3].strip()
                        ))
                        multiline_content = []
                
                # 한 줄 주석
                elif '#' in stripped:
                    comment_start = stripped.index('#')
                    comment_text = stripped[comment_start+1:].strip()
                    if comment_text:
                        comments.append(CodeComment(
                            line_number=i,
                            comment_type='single',
                            content=comment_text
                        ))
            else:
                # 멀티라인 주석 종료 확인
                if quote_char in stripped:
                    multiline_content.append(stripped.replace(quote_char, ''))
                    comments.append(CodeComment(
                        line_number=multiline_start,
                        comment_type='docstring',
                        content='\n'.join(multiline_content).strip()
                    ))
                    in_multiline = False
                    multiline_content = []
                else:
                    multiline_content.append(stripped)
        
        return comments
    
    @staticmethod
    def extract_cpp_java(code: str) -> List[CodeComment]:
        """C++/Java 주석 추출"""
        comments = []
        lines = code.split('\n')
        
        in_multiline = False
        multiline_start = 0
        multiline_content = []
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            if not in_multiline:
                # 멀티라인 주석 시작
                if '/*' in stripped:
                    in_multiline = True
                    multiline_start = i
                    start_idx = stripped.index('/*')
                    
                    # 같은 줄에 끝나는 경우
                    if '*/' in stripped[start_idx:]:
                        end_idx = stripped.index('*/', start_idx)
                        comment_text = stripped[start_idx+2:end_idx].strip()
                        comments.append(CodeComment(
                            line_number=i,
                            comment_type='multi',
                            content=comment_text
                        ))
                        in_multiline = False
                    else:
                        multiline_content = [stripped[start_idx+2:]]
                
                # 한 줄 주석
                elif '//' in stripped:
                    comment_start = stripped.index('//')
                    comment_text = stripped[comment_start+2:].strip()
                    if comment_text:
                        comments.append(CodeComment(
                            line_number=i,
                            comment_type='single',
                            content=comment_text
                        ))
            else:
                # 멀티라인 주석 종료 확인
                if '*/' in stripped:
                    end_idx = stripped.index('*/')
                    multiline_content.append(stripped[:end_idx])
                    comments.append(CodeComment(
                        line_number=multiline_start,
                        comment_type='multi',
                        content='\n'.join(multiline_content).strip()
                    ))
                    in_multiline = False
                    multiline_content = []
                else:
                    multiline_content.append(stripped)
        
        return comments
    
    @classmethod
    def extract(cls, code: str, language: str) -> List[CodeComment]:
        """언어에 따라 주석 추출"""
        language_lower = language.lower()
        
        if 'python' in language_lower or 'pypy' in language_lower:
            return cls.extract_python(code)
        elif any(lang in language_lower for lang in ['c++', 'c', 'java', 'javascript', 'typescript']):
            return cls.extract_cpp_java(code)
        else:
            # 기본은 C 스타일 시도
            return cls.extract_cpp_java(code)


class CodeAnalyzer:
    """코드 분석"""
    
    @staticmethod
    def analyze(code: str, language: str) -> CodeAnalysis:
        """코드 분석 (라인 수, 주석 등)"""
        lines = code.split('\n')
        total_lines = len(lines)
        
        blank_lines = sum(1 for line in lines if not line.strip())
        
        # 주석 추출
        comments = CommentExtractor.extract(code, language)
        comment_lines = len(comments)
        
        # 주석이 멀티라인인 경우 실제 라인 수 계산
        for comment in comments:
            if comment.comment_type in ['multi', 'docstring']:
                comment_lines += comment.content.count('\n')
        
        code_lines = total_lines - blank_lines - comment_lines
        
        return CodeAnalysis(
            language=language,
            total_lines=total_lines,
            code_lines=code_lines,
            comment_lines=comment_lines,
            blank_lines=blank_lines,
            comments=comments
        )


class BaekjoonParser:
    """백준 데이터 파서"""
    
    def parse_problems(self, problems: List[Dict]) -> List[ProblemData]:
        """문제 리스트를 ProblemData로 변환"""
        parsed = []
        
        for p in problems:
            # 코드 분석 (있는 경우)
            code_analysis = None
            if 'submission' in p and 'code' in p['submission']:
                code_analysis = CodeAnalyzer.analyze(
                    p['submission']['code'],
                    p['submission']['language']
                )
            
            parsed.append(ProblemData(
                problem_id=p['problem_id'],
                title=p['title'],
                level=p['level'],
                tier=p['tier'],
                tags=p['tags'],
                url=p['url'],
                submission=p.get('submission'),
                code_analysis=code_analysis
            ))
        
        return parsed
    
    def group_by_tier(self, problems: List[ProblemData]) -> Dict[str, List[ProblemData]]:
        """티어별로 문제 그룹화"""
        grouped = {}
        
        for problem in problems:
            tier = problem.tier
            if tier not in grouped:
                grouped[tier] = []
            grouped[tier].append(problem)
        
        return grouped
    
    def group_by_tags(self, problems: List[ProblemData]) -> Dict[str, List[ProblemData]]:
        """태그별로 문제 그룹화"""
        grouped = {}
        
        for problem in problems:
            for tag in problem.tags:
                if tag not in grouped:
                    grouped[tag] = []
                grouped[tag].append(problem)
        
        return grouped
    
    def get_summary(self, problems: List[ProblemData]) -> Dict:
        """문제 통계 요약"""
        if not problems:
            return {
                'total_problems': 0,
                'tiers': {},
                'tags': {},
                'languages': {},
                'total_code_lines': 0,
                'total_comments': 0
            }
        
        tier_count = {}
        tag_count = {}
        language_count = {}
        total_code_lines = 0
        total_comments = 0
        
        for problem in problems:
            tier_count[problem.tier] = tier_count.get(problem.tier, 0) + 1
            
            for tag in problem.tags:
                tag_count[tag] = tag_count.get(tag, 0) + 1
            
            if problem.code_analysis:
                lang = problem.code_analysis.language
                language_count[lang] = language_count.get(lang, 0) + 1
                total_code_lines += problem.code_analysis.code_lines
                total_comments += len(problem.code_analysis.comments)
        
        return {
            'total_problems': len(problems),
            'tiers': tier_count,
            'tags': tag_count,
            'languages': language_count,
            'total_code_lines': total_code_lines,
            'total_comments': total_comments
        }


if __name__ == '__main__':
    # 테스트
    sample_code = '''
# 이진 탐색 구현
def binary_search(arr, target):
    """
    이진 탐색 알고리즘
    시간복잡도: O(log n)
    """
    left, right = 0, len(arr) - 1
    
    while left <= right:
        mid = (left + right) // 2  # 중간 인덱스
        
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    
    return -1  # 못 찾음
'''
    
    analysis = CodeAnalyzer.analyze(sample_code, 'Python 3')
    
    print(f"총 라인: {analysis.total_lines}")
    print(f"코드 라인: {analysis.code_lines}")
    print(f"주석 라인: {analysis.comment_lines}")
    print(f"빈 라인: {analysis.blank_lines}")
    print(f"\n주석:")
    for comment in analysis.comments:
        print(f"  L{comment.line_number} [{comment.comment_type}]: {comment.content[:50]}")

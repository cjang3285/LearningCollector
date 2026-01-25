"""
블로그 API 클라이언트
chanwook.kr 블로그에 포스팅
"""
import re
import requests
from pathlib import Path
from typing import List, Optional, Dict


class BlogAPIClient:
    """블로그 API 클라이언트"""

    def __init__(self, use_localhost: bool = True):
        """
        Args:
            use_localhost: True면 로컬호스트 사용, False면 프로덕션 URL 사용
        """
        if use_localhost:
            # LearningCollector와 같은 머신에서 실행 (인증 불필요)
            self.base_url = "http://localhost:3000/api"
        else:
            # 프로덕션 환경
            self.base_url = "https://chanwook.kr/api"

        self.posts_endpoint = f"{self.base_url}/posts"

    def create_post(
        self,
        title: str,
        content: str,
        excerpt: Optional[str] = None,
        tags: Optional[List[str]] = None,
        featured: bool = False
    ) -> dict:
        """
        블로그 포스트 생성

        Args:
            title: 제목 (필수)
            content: 내용 - 마크다운 형식 (필수)
            excerpt: 발췌문 (선택)
            tags: 태그 배열 (선택)
            featured: 추천 여부 (선택, 기본값: false)

        Returns:
            dict: API 응답
        """
        # 요청 데이터 구성
        payload = {
            "title": title,
            "content": content
        }

        if excerpt:
            payload["excerpt"] = excerpt

        if tags:
            payload["tags"] = tags

        if featured:
            payload["featured"] = featured

        try:
            # API 호출
            response = requests.post(
                self.posts_endpoint,
                json=payload,
                timeout=30
            )

            # 응답 확인
            if response.status_code == 201:
                return {
                    "success": True,
                    "message": "포스트 생성 성공",
                    "data": response.json()
                }
            else:
                return {
                    "success": False,
                    "message": f"포스트 생성 실패: HTTP {response.status_code}",
                    "error": response.text
                }

        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "message": "API 요청 실패",
                "error": str(e)
            }

    def create_posts_batch(self, posts: List[dict]) -> List[dict]:
        """
        여러 포스트를 배치로 생성

        Args:
            posts: 포스트 정보 딕셔너리 리스트
                   [{"title": "...", "content": "...", ...}, ...]

        Returns:
            list: API 응답 리스트
        """
        results = []

        for post in posts:
            result = self.create_post(**post)
            results.append(result)

        return results

    def extract_tags_from_draft_type(self, draft_type: str) -> List[str]:
        """
        Draft 타입에서 태그 추출

        Args:
            draft_type: draft 종류 (algorithm, dev, study)

        Returns:
            list: 태그 리스트
        """
        tag_mapping = {
            "algorithm": ["알고리즘", "백준", "코딩테스트"],
            "dev": ["개발", "프로젝트", "코드리뷰"],
            "study": ["학습", "AI", "공부"]
        }

        return tag_mapping.get(draft_type, [])

    def parse_frontmatter(self, content: str) -> tuple[Dict, str]:
        """
        Markdown frontmatter 파싱

        Args:
            content: MD 파일 전체 내용

        Returns:
            tuple: (frontmatter dict, content without frontmatter)
        """
        # frontmatter 패턴: ---로 시작하고 ---로 끝남
        frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
        match = re.match(frontmatter_pattern, content, re.DOTALL)

        if not match:
            return {}, content

        frontmatter_text = match.group(1)
        content_without_frontmatter = match.group(2)

        # YAML 파싱 (간단한 key: value 형식)
        frontmatter = {}
        for line in frontmatter_text.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")

                # tags 배열 처리
                if key == 'tags' and value.startswith('[') and value.endswith(']'):
                    # ["tag1", "tag2"] → ["tag1", "tag2"]
                    tags_str = value[1:-1]  # 대괄호 제거
                    frontmatter[key] = [
                        tag.strip().strip('"').strip("'")
                        for tag in tags_str.split(',')
                        if tag.strip()
                    ]
                elif key == 'featured':
                    frontmatter[key] = value.lower() == 'true'
                else:
                    frontmatter[key] = value

        return frontmatter, content_without_frontmatter

    def extract_metadata_from_content(self, content: str, draft_type: str) -> Dict:
        """
        Frontmatter 없는 MD 파일에서 메타데이터 자동 추출

        Args:
            content: MD 파일 내용
            draft_type: draft 종류 (algorithm, dev, study)

        Returns:
            dict: 추출된 메타데이터
        """
        metadata = {
            "title": "",
            "excerpt": "",
            "tags": self.extract_tags_from_draft_type(draft_type),
            "featured": False
        }

        lines = content.split('\n')

        # 1. Title 추출: 첫 번째 H1 (# )
        for line in lines:
            if line.strip().startswith('# '):
                metadata["title"] = line.strip()[2:].strip()
                break

        # 2. Excerpt 추출: H1 다음 첫 번째 비어있지 않은 문단
        found_h1 = False
        for line in lines:
            if line.strip().startswith('# '):
                found_h1 = True
                continue

            if found_h1 and line.strip() and not line.strip().startswith('#'):
                # 200자 제한
                excerpt = line.strip()
                if len(excerpt) > 200:
                    excerpt = excerpt[:197] + "..."
                metadata["excerpt"] = excerpt
                break

        return metadata

    def parse_draft_file(self, file_path: str) -> Dict:
        """
        Draft 파일 파싱하여 포스트 데이터 추출

        Args:
            file_path: Draft MD 파일 경로

        Returns:
            dict: {title, content, excerpt, tags, featured}
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Draft 파일을 찾을 수 없습니다: {file_path}")

        # 파일명에서 draft_type 추출 (algorithm_xxx.md → algorithm)
        filename = path.name
        draft_type_match = re.match(r'^(algorithm|dev|study)_', filename)
        draft_type = draft_type_match.group(1) if draft_type_match else "dev"

        # 파일 읽기
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Frontmatter 파싱 시도
        frontmatter, content_body = self.parse_frontmatter(content)

        if frontmatter:
            # Frontmatter 있음: 우선 사용
            post_data = {
                "title": frontmatter.get("title", ""),
                "content": content_body,
                "excerpt": frontmatter.get("excerpt", ""),
                "tags": frontmatter.get("tags", self.extract_tags_from_draft_type(draft_type)),
                "featured": frontmatter.get("featured", False)
            }
        else:
            # Frontmatter 없음: 본문에서 추출
            metadata = self.extract_metadata_from_content(content, draft_type)
            post_data = {
                "title": metadata["title"],
                "content": content,  # 전체 내용 사용
                "excerpt": metadata["excerpt"],
                "tags": metadata["tags"],
                "featured": metadata["featured"]
            }

        # 필수 필드 검증
        if not post_data["title"]:
            raise ValueError(f"Draft에서 제목을 추출할 수 없습니다: {file_path}")

        if not post_data["content"].strip():
            raise ValueError(f"Draft 내용이 비어있습니다: {file_path}")

        return post_data

    def create_post_from_draft(self, draft_file_path: str) -> dict:
        """
        Draft 파일로부터 블로그 포스트 생성

        Args:
            draft_file_path: Draft MD 파일 경로

        Returns:
            dict: API 응답
        """
        try:
            # Draft 파일 파싱
            post_data = self.parse_draft_file(draft_file_path)

            # 포스트 생성
            result = self.create_post(**post_data)

            return result

        except Exception as e:
            return {
                "success": False,
                "message": f"Draft 파일 처리 실패: {str(e)}",
                "error": str(e)
            }


if __name__ == "__main__":
    import sys

    # 로컬호스트 사용 (같은 머신에서 실행, 인증 불필요)
    client = BlogAPIClient(use_localhost=True)

    if len(sys.argv) > 1:
        # Draft 파일 경로가 주어진 경우
        draft_file = sys.argv[1]
        print(f"📝 Draft 파일에서 포스트 생성: {draft_file}")

        result = client.create_post_from_draft(draft_file)
        print("\n결과:")
        print(result)

    else:
        # 테스트: 직접 포스트 생성
        print("📝 테스트 포스트 생성")

        result = client.create_post(
            title="테스트 포스트",
            content="# 테스트\n\n이것은 테스트 포스트입니다.",
            excerpt="테스트용 포스트입니다.",
            tags=["테스트", "개발"],
            featured=False
        )

        print("\n결과:")
        print(result)

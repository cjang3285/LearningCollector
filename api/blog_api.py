"""
블로그 API 클라이언트
chanwook.kr 블로그에 포스팅
"""
import requests
from typing import List, Optional


class BlogAPIClient:
    """블로그 API 클라이언트"""

    def __init__(self):
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


if __name__ == "__main__":
    client = BlogAPIClient()

    # 테스트: 포스트 생성
    result = client.create_post(
        title="테스트 포스트",
        content="# 테스트\n\n이것은 테스트 포스트입니다.",
        tags=["테스트", "개발"],
        featured=False
    )

    print(result)

"""
Gemini API 클라이언트
블로그 초안 생성
"""
import os
import time
from google import genai


class GeminiClient:
    """Gemini API 클라이언트 (최신 google.genai 사용)"""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key)
        self.max_retries = 3
        self.retry_delay = 2  # 초

    def generate_draft(self, prompt: str, json_content: str) -> str:
        """
        Gemini를 사용하여 블로그 초안 생성 (재시도 로직 포함)

        Args:
            prompt: 프롬프트 (prompts 폴더의 md 파일 내용)
            json_content: JSON 파일 내용

        Returns:
            str: 생성된 초안 (마크다운), 실패 시 None
        """
        # 전체 프롬프트 구성
        full_prompt = f"""{prompt}

다음은 참조할 데이터입니다:

```json
{json_content}
```

위 데이터를 바탕으로 블로그 초안을 작성해주세요.
"""

        # 재시도 로직
        for attempt in range(self.max_retries):
            try:
                # Gemini API 호출 (최신 방식)
                response = self.client.models.generate_content(
                    model='gemini-2.0-flash-exp',
                    contents=full_prompt
                )

                # 응답 텍스트 반환
                return response.text

            except Exception as e:
                error_msg = str(e)

                # Rate limit 에러 확인
                is_rate_limit = any(keyword in error_msg.lower() for keyword in
                                   ['rate limit', 'quota', 'resource exhausted', '429'])

                if is_rate_limit and attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    print(f"      Rate limit 도달. {wait_time}초 대기 후 재시도... ({attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    # 재시도 불가능하거나 마지막 시도 실패
                    print(f"      Gemini API 호출 실패: {error_msg}")
                    return None

        return None

    def generate_batch_drafts(self, prompts_and_data: list) -> list:
        """
        여러 초안을 배치로 생성

        Args:
            prompts_and_data: [(prompt, json_content), ...] 리스트

        Returns:
            list: 생성된 초안 리스트
        """
        drafts = []

        for prompt, json_content in prompts_and_data:
            draft = self.generate_draft(prompt, json_content)
            drafts.append(draft)

        return drafts


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    client = GeminiClient()

    # 테스트
    test_prompt = """
다음 백준 문제 풀이를 바탕으로 블로그 포스팅 초안을 작성해주세요.

포함할 내용:
1. 문제 설명
2. 풀이 접근법
3. 코드 설명
4. 시간 복잡도 분석
"""

    test_json = """
{
  "문제_번호": "1234",
  "문제명": "두 수의 합",
  "티어": "Bronze 3",
  "풀이_코드": "a, b = map(int, input().split())\\nprint(a + b)"
}
"""

    draft = client.generate_draft(test_prompt, test_json)
    print(draft)

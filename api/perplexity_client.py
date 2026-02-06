"""
Perplexity API 클라이언트
Gemini 폴백용 블로그 초안 생성
OpenAI SDK 호환 (base_url만 변경)
"""
import os
import time
from openai import OpenAI


class PerplexityClient:
    """Perplexity Sonar API 클라이언트"""

    def __init__(self):
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        self.client = None
        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.perplexity.ai"
            )
        self.max_retries = 3
        self.retry_delay = 2  # 초

    def is_available(self) -> bool:
        """API 키가 설정되어 사용 가능한지 확인"""
        return self.client is not None

    def generate_draft(self, prompt: str, json_content: str) -> str:
        """
        Perplexity를 사용하여 블로그 초안 생성 (재시도 로직 포함)

        Args:
            prompt: 프롬프트 (prompts 폴더의 md 파일 내용)
            json_content: JSON 파일 내용

        Returns:
            str: 생성된 초안 (마크다운), 실패 시 None
        """
        if not self.is_available():
            return None

        full_prompt = f"""{prompt}

다음은 참조할 데이터입니다:

```json
{json_content}
```

위 데이터를 바탕으로 블로그 초안을 작성해주세요.
"""

        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="sonar",
                    messages=[
                        {"role": "user", "content": full_prompt}
                    ]
                )

                return response.choices[0].message.content

            except Exception as e:
                error_msg = str(e)

                is_rate_limit = any(keyword in error_msg.lower() for keyword in
                                   ['rate limit', 'quota', '429'])

                if is_rate_limit and attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    print(f"      ⏳ Perplexity rate limit. {wait_time}초 대기 후 재시도... ({attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"      ❌ Perplexity API 호출 실패: {error_msg[:200]}")
                    return None

        return None

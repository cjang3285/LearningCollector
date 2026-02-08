"""
Gemini API 클라이언트
블로그 초안 생성
"""
import os
import time
from google import genai
from core import structured_logger as slog


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
            t = slog.start_timer()
            try:
                # Gemini API 호출 (정식 모델 사용)
                response = self.client.models.generate_content(
                    model='gemini-2.5-flash-lite',
                    contents=full_prompt
                )

                duration = slog.elapsed_ms(t)
                slog.api_call("gemini", "POST", "generate_content",
                              200, duration, True,
                              model="gemini-2.5-flash-lite",
                              prompt_len=len(full_prompt),
                              response_len=len(response.text) if response.text else 0,
                              attempt=attempt + 1)

                # 응답 텍스트 반환
                return response.text

            except Exception as e:
                duration = slog.elapsed_ms(t)
                error_msg = str(e)

                # 일일 한도 초과 확인
                is_daily_quota = 'per_day' in error_msg.lower() or 'perdayperproject' in error_msg.lower()

                # Rate limit 에러 확인
                is_rate_limit = any(keyword in error_msg.lower() for keyword in
                                   ['rate limit', 'quota', 'resource exhausted', '429'])

                if is_daily_quota:
                    # 일일 한도 초과 - 재시도 불가
                    slog.api_error("gemini", "POST", "generate_content",
                                   duration, error_msg[:200],
                                   reason="daily_quota_exceeded",
                                   attempt=attempt + 1)
                    print(f"      ❌ Gemini API 일일 한도 초과. 내일 다시 시도하세요.")
                    return None
                elif is_rate_limit and attempt < self.max_retries - 1:
                    # 분당 한도 - 재시도 가능
                    wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    slog.warn("api_call", "api", api="gemini",
                              method="POST", endpoint="generate_content",
                              reason="rate_limit_retry",
                              attempt=attempt + 1, wait_seconds=wait_time)
                    print(f"      ⏳ Rate limit 도달. {wait_time}초 대기 후 재시도... ({attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    # 기타 에러 또는 마지막 시도 실패
                    slog.api_error("gemini", "POST", "generate_content",
                                   duration, error_msg[:200],
                                   attempt=attempt + 1)
                    print(f"      ❌ Gemini API 호출 실패: {error_msg[:200]}")
                    return None

        return None

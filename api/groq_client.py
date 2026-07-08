"""
Groq API 클라이언트
Gemini 폴백용 블로그 초안 생성
OpenAI SDK 호환 (base_url만 변경), 무료 티어
"""
import os
import time
from openai import OpenAI
from core import structured_logger as slog


class GroqClient:
    """Groq API 클라이언트"""

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = None
        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.groq.com/openai/v1"
            )
        self.model = "llama-3.3-70b-versatile"
        self.max_retries = 3
        self.retry_delay = 2  # 초
        self.last_error_permanent = False  # True면 이번 실행 내내 재시도해도 소용없는 실패 (예: 잘못된 키)
        self.last_error_too_large = False  # True면 요청 용량이 모델 한도를 초과 (압축 후 재시도하면 성공 가능)

    def is_available(self) -> bool:
        """API 키가 설정되어 사용 가능한지 확인"""
        return self.client is not None

    def generate_draft(self, prompt: str, json_content: str, instruction: str = None) -> str:
        """
        Groq를 사용하여 블로그 초안 생성 (재시도 로직 포함)

        Args:
            prompt: 프롬프트 (prompts 폴더의 md 파일 내용)
            json_content: JSON 파일 내용
            instruction: 마지막에 덧붙일 지시문 (기본: 블로그 초안 작성 요청).
                         압축 요약 등 다른 용도로 재사용할 때 오버라이드용

        Returns:
            str: 생성된 초안(또는 압축 결과) 텍스트, 실패 시 None
        """
        if not self.is_available():
            return None

        if instruction is None:
            instruction = "위 데이터를 바탕으로 블로그 초안을 작성해주세요."

        self.last_error_permanent = False
        self.last_error_too_large = False

        full_prompt = f"""{prompt}

다음은 참조할 데이터입니다:

```json
{json_content}
```

{instruction}

**중요: 출력은 반드시 한국어로만 작성하세요. 한자, 태국어, 일본어 등 다른 문자·언어를 절대 섞지 마세요.**
"""

        for attempt in range(self.max_retries):
            t = slog.start_timer()
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": full_prompt}
                    ]
                )

                duration = slog.elapsed_ms(t)
                result_text = response.choices[0].message.content
                slog.api_call("groq", "POST", "chat.completions",
                              200, duration, True,
                              model=self.model,
                              prompt_len=len(full_prompt),
                              response_len=len(result_text) if result_text else 0,
                              attempt=attempt + 1)
                return result_text

            except Exception as e:
                duration = slog.elapsed_ms(t)
                error_msg = str(e)

                # 인증 실패 (잘못된/만료된 키) - 재시도해도 소용없음
                is_auth_error = any(keyword in error_msg.lower() for keyword in
                                   ['invalid_api_key', 'unauthorized', '401'])

                # 요청 자체가 모델의 분당 토큰 한도보다 큼 - 대기해도 똑같이 실패하므로
                # 재시도 대신 압축 요약 후 재시도가 필요함 (AIClient가 처리)
                is_too_large = any(keyword in error_msg.lower() for keyword in
                                  ['request too large', 'too large for model', '413'])

                # 분당/일일 한도 등 rate limit (잠시 후 재시도하면 풀리는 경우가 많음)
                is_rate_limit = (not is_auth_error and not is_too_large) and any(
                    keyword in error_msg.lower() for keyword in ['rate limit', 'rate_limit', '429']
                )

                if is_auth_error:
                    self.last_error_permanent = True
                    slog.api_error("groq", "POST", "chat.completions",
                                   duration, error_msg[:200],
                                   reason="auth_error",
                                   attempt=attempt + 1)
                    print(f"      ❌ Groq 인증 실패 (API 키 확인 필요): {error_msg[:200]}")
                    return None

                if is_too_large:
                    # 대기 후 재시도해봤자 크기는 그대로라 무의미 - 즉시 포기하고
                    # 압축 요약 재시도는 AIClient가 담당
                    self.last_error_too_large = True
                    slog.api_error("groq", "POST", "chat.completions",
                                   duration, error_msg[:200],
                                   reason="request_too_large",
                                   attempt=attempt + 1)
                    print(f"      ❌ Groq 요청 용량 초과 (압축 후 재시도 예정): {error_msg[:200]}")
                    return None

                if is_rate_limit and attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    slog.warn("api_call", "api", api="groq",
                              method="POST", endpoint="chat.completions",
                              reason="rate_limit_retry",
                              attempt=attempt + 1, wait_seconds=wait_time)
                    print(f"      ⏳ Groq rate limit. {wait_time}초 대기 후 재시도... ({attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    slog.api_error("groq", "POST", "chat.completions",
                                   duration, error_msg[:200],
                                   attempt=attempt + 1)
                    print(f"      ❌ Groq API 호출 실패: {error_msg[:200]}")
                    return None

        return None

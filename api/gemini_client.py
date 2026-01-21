"""
Gemini API 클라이언트
블로그 초안 생성
"""
import os
import google.generativeai as genai


class GeminiClient:
    """Gemini API 클라이언트"""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-pro')

    def generate_draft(self, prompt: str, json_content: str) -> str:
        """
        Gemini를 사용하여 블로그 초안 생성

        Args:
            prompt: 프롬프트 (prompts 폴더의 md 파일 내용)
            json_content: JSON 파일 내용

        Returns:
            str: 생성된 초안 (마크다운)
        """
        # 전체 프롬프트 구성
        full_prompt = f"""{prompt}

다음은 참조할 데이터입니다:

```json
{json_content}
```

위 데이터를 바탕으로 블로그 초안을 작성해주세요.
"""

        try:
            # Gemini API 호출
            response = self.model.generate_content(full_prompt)

            # 응답 텍스트 반환
            return response.text

        except Exception as e:
            print(f"Gemini API 호출 실패: {str(e)}")
            return f"# 오류\n\n초안 생성 중 오류 발생: {str(e)}"

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

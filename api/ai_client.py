"""
통합 AI 클라이언트
Gemini를 1차로 시도하고, 실패 시 Perplexity로 폴백
"""
from api.gemini_client import GeminiClient
from api.perplexity_client import PerplexityClient


class AIClient:
    """Gemini → Perplexity 폴백을 가진 통합 AI 클라이언트"""

    def __init__(self):
        self.gemini = GeminiClient()
        self.perplexity = PerplexityClient()

        if self.perplexity.is_available():
            print("  [AI] Gemini + Perplexity 폴백 활성화")
        else:
            print("  [AI] Gemini 단독 모드 (PERPLEXITY_API_KEY 미설정)")

    def generate_draft(self, prompt: str, json_content: str) -> str:
        """
        블로그 초안 생성 (Gemini 우선, 실패 시 Perplexity 폴백)

        Args:
            prompt: 프롬프트 (prompts 폴더의 md 파일 내용)
            json_content: JSON 파일 내용

        Returns:
            str: 생성된 초안 (마크다운), 모두 실패 시 None
        """
        # 1차: Gemini 시도
        result = self.gemini.generate_draft(prompt, json_content)
        if result is not None:
            return result

        # 2차: Perplexity 폴백
        if not self.perplexity.is_available():
            return None

        print("      🔄 Gemini 실패 → Perplexity로 전환")
        return self.perplexity.generate_draft(prompt, json_content)

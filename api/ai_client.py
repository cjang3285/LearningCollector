"""
통합 AI 클라이언트
Gemini 단독 사용.

Groq 폴백은 한국어 생성 시 한자/태국어 등 다른 언어가 섞이는 품질 문제로
비활성화함. 아래 원래 로직(Groq 폴백 + 용량 초과 시 압축 재시도)은 주석
처리만 해두고 남겨뒀으니, 필요해지면 주석을 풀어 복구하면 됨.
"""
from api.gemini_client import GeminiClient
# from api.groq_client import GroqClient

# COMPRESS_INSTRUCTION = (
#     "위 JSON 데이터를 지시사항에 따라 압축해서, 같은 JSON 구조(키는 그대로 유지)로 "
#     "다시 출력해주세요. 코드 블록 표시나 다른 설명 없이 JSON 본문만 출력하세요."
# )


class AIClient:
    """Gemini 단독 클라이언트 (Groq 폴백 비활성화)"""

    def __init__(self):
        self.gemini = GeminiClient()
        # self.groq = GroqClient()
        # True면 이번 실행 내내 재시도해도 소용없는 상태 (일일 한도 초과 등)
        self.last_error_permanent = False
        # self.compression_prompt = self._load_compression_prompt()

        print("  [AI] Gemini 단독 모드 (Groq 폴백 비활성화)")

    # def _load_compression_prompt(self) -> str:
    #     """압축 요약용 프롬프트 로드"""
    #     prompt_path = Path(__file__).parent.parent / "prompts" / "대화_내용_압축_요약_프롬프트.md"
    #     with open(prompt_path, "r", encoding="utf-8") as f:
    #         return f.read()

    def generate_draft(self, prompt: str, json_content: str) -> str:
        """
        블로그 초안 생성 (Gemini 단독)

        Args:
            prompt: 프롬프트 (prompts 폴더의 md 파일 내용)
            json_content: JSON 파일 내용

        Returns:
            str: 생성된 초안 (마크다운), 실패 시 None
        """
        self.last_error_permanent = False

        result = self.gemini.generate_draft(prompt, json_content)
        if result is not None:
            return result

        self.last_error_permanent = self.gemini.last_error_permanent
        return None

        # --- Groq 폴백 + 압축 재시도 로직 (주석 처리, 필요 시 복구) ---
        #
        # # 2차: Groq 폴백
        # if not self.groq.is_available():
        #     # Groq가 없으면 Gemini 실패 사유가 곧 최종 사유
        #     self.last_error_permanent = self.gemini.last_error_permanent
        #     return None
        #
        # print("      🔄 Gemini 실패 → Groq로 전환")
        # result = self.groq.generate_draft(prompt, json_content)
        # if result is not None:
        #     return result
        #
        # # 3차: Groq가 "요청 용량 초과"로 실패한 경우 - 대기해도 소용없으므로
        # # Gemini로 원본 내용을 정보 손실 최소화하며 압축 요약한 뒤,
        # # 압축된 내용으로 Gemini에게 초안 생성을 다시 요청
        # if self.groq.last_error_too_large:
        #     compressed = self._compress_content(json_content)
        #     if compressed:
        #         print("      🔄 압축된 내용으로 Gemini 재요청...")
        #         result = self.gemini.generate_draft(prompt, compressed)
        #         if result is not None:
        #             return result
        #
        # # 모두 실패 - 둘 다 영구 실패일 때만 이번 실행을 포기할 가치가 있음
        # self.last_error_permanent = (
        #     self.gemini.last_error_permanent and self.groq.last_error_permanent
        # )
        # return None

    # def _compress_content(self, json_content: str) -> str:
    #     """
    #     대화량이 너무 커서 실패했을 때, Gemini로 핵심 정보를 보존하며 압축 요약.
    #     Gemini는 컨텍스트 한도가 훨씬 커서 원본을 그대로 읽을 수 있으므로 압축 용도로 사용.
    #     """
    #     print("      📦 내용이 너무 커서 핵심 정보를 보존하며 압축 요약 중...")
    #     return self.gemini.generate_draft(
    #         self.compression_prompt, json_content, instruction=COMPRESS_INSTRUCTION
    #     )

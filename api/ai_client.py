"""
통합 AI 클라이언트
Gemini 우선 사용, 일일 한도 초과 시 claude CLI(Claude Pro 구독)로 폴백.

Groq 폴백은 한국어 생성 시 한자/태국어 등 다른 언어가 섞이는 품질 문제로
비활성화함. 아래 원래 로직(Groq 폴백 + 용량 초과 시 압축 재시도)은 주석
처리만 해두고 남겨뒀으니, 필요해지면 주석을 풀어 복구하면 됨.
"""
import json
import re
import threading

from api.gemini_client import GeminiClient
from api.claude_code_client import ClaudeCodeClient
# from api.groq_client import GroqClient

# COMPRESS_INSTRUCTION = (
#     "위 JSON 데이터를 지시사항에 따라 압축해서, 같은 JSON 구조(키는 그대로 유지)로 "
#     "다시 출력해주세요. 코드 블록 표시나 다른 설명 없이 JSON 본문만 출력하세요."
# )

# 대화 하나에 서로 무관한 학습 주제가 섞여 있는지 판단하는 용도. 분류 작업이라
# 저렴한 모델로 충분하고, 실패해도 "분리 없음"으로 안전하게 폴백하므로 Claude
# 폴백은 두지 않는다 (Gemini 한도 초과 시엔 그냥 분리를 건너뜀).
SEGMENTATION_MODEL = "gemini-2.5-flash-lite"
SEGMENTATION_INSTRUCTION = (
    "위 대화를 분석해서 지시된 JSON 형식으로만 응답하세요. "
    "코드 블록 표시나 다른 설명 없이 JSON 본문만 출력하세요."
)


class SharedFlag:
    """여러 워커 스레드가 공유하는 스레드-세이프 플래그 (병렬 처리 시 사용)"""

    def __init__(self):
        self._value = False
        self._lock = threading.Lock()

    def get(self) -> bool:
        with self._lock:
            return self._value

    def set(self):
        with self._lock:
            self._value = True


class AIClient:
    """Gemini 우선 + claude CLI 폴백 클라이언트 (Groq 폴백은 비활성화)

    Args:
        gemini_exhausted_flag: 병렬 워커들이 공유하는 SharedFlag. 여러 AIClient를
            워커별로 만들 때 이 플래그를 공유시키면, 한 워커가 Gemini 일일 한도
            초과를 확인하는 즉시 다른 워커들도 Gemini를 건너뛰게 된다.
            넘기지 않으면 이 인스턴스 전용 플래그를 만든다(단일 워커용).
    """

    def __init__(self, gemini_exhausted_flag: SharedFlag = None):
        self.gemini = GeminiClient()
        self.claude_code = ClaudeCodeClient()
        # self.groq = GroqClient()
        # True면 이번 실행 내내 재시도해도 소용없는 상태 (일일 한도 초과 등)
        self.last_error_permanent = False
        # 이번 실행에서 Gemini 일일 한도 초과가 이미 확인되면, 남은 항목은
        # Gemini 재시도(및 대기 시간) 없이 곧바로 Claude Pro로만 처리
        self.gemini_exhausted_flag = gemini_exhausted_flag or SharedFlag()
        # self.compression_prompt = self._load_compression_prompt()

    def close(self):
        """파이프라인 종료 시 claude CLI 영속 프로세스 정리"""
        self.claude_code.close()

    # def _load_compression_prompt(self) -> str:
    #     """압축 요약용 프롬프트 로드"""
    #     prompt_path = Path(__file__).parent.parent / "prompts" / "대화_내용_압축_요약_프롬프트.md"
    #     with open(prompt_path, "r", encoding="utf-8") as f:
    #         return f.read()

    def generate_draft(self, prompt: str, json_content: str, model: str = None) -> str:
        """
        블로그 초안 생성 (Gemini 우선, 일일 한도 초과 시 claude CLI로 폴백)

        Args:
            prompt: 프롬프트 (prompts 폴더의 md 파일 내용)
            json_content: JSON 파일 내용
            model: Gemini 쪽에서 사용할 모델 (기본: gemini_client의 기본값).
                   Claude Pro 폴백은 claude CLI 자체 모델을 쓰므로 영향 없음.

        Returns:
            str: 생성된 초안 (마크다운), 실패 시 None
        """
        self.last_error_permanent = False

        if not self.gemini_exhausted_flag.get():
            result = self.gemini.generate_draft(prompt, json_content, model=model)
            if result is not None:
                return result

            # Gemini가 영구 실패(일일 한도 초과 등)가 아니면 이번 항목은 실패 처리
            if not self.gemini.last_error_permanent:
                self.last_error_permanent = False
                return None

            # 일일 한도 초과 확인 - 이번 실행의 나머지 항목은 Gemini를 건너뛰고 곧장 Claude Pro로
            self.gemini_exhausted_flag.set()
            print("      🔄 Gemini 한도 초과 → 이후 항목은 Claude Pro(claude CLI)로 처리")
        else:
            print("      🔄 (Gemini 한도 초과 상태) Claude Pro(claude CLI)로 처리")

        result = self.claude_code.generate_draft(prompt, json_content)
        if result is not None:
            return result

        # 폴백도 실패 - 둘 다 영구 실패일 때만 이번 실행을 포기할 가치가 있음
        self.last_error_permanent = (
            self.gemini.last_error_permanent and self.claude_code.last_error_permanent
        )
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

    def split_topics(self, segmentation_prompt: str, numbered_conversation: str) -> list:
        """
        대화 내용에 서로 무관한 학습 주제가 여러 개 섞여 있는지 판단해서 분리 지점을 반환.

        numbered_conversation은 각 줄 앞에 "N: " 형식으로 줄 번호가 붙어 있어야 하며,
        모델은 원문을 다시 생성하지 않고 주제별 제목과 시작 줄 번호만 JSON으로 답한다
        (원문을 그대로 재생성하게 하면 출력 토큰을 많이 쓰고 누락/변형 위험도 있음).

        Gemini 우선, 한도 초과 등으로 실패하면 Claude Pro(claude CLI)로 폴백한다 -
        Gemini 일일 한도는 자주 소진되는데, 그때마다 주제 분리 기능 자체가 통째로
        무력화되면 안 되기 때문. 이 보조 판단 실패는 병렬 워커 공유 상태
        (gemini_exhausted_flag)에 영향을 주지 않는다 - 그건 본 초안 생성 폴백
        전용이고, 여기서는 각 호출이 독립적으로 실패/폴백을 처리한다.
        최종적으로도 실패하면(둘 다 실패, 파싱 실패 등) 빈 리스트를 반환하며,
        호출 측은 이를 "분리 없음(단일 주제)"으로 안전하게 폴백 처리해야 한다.

        Args:
            segmentation_prompt: 프롬프트 (prompts/대화_주제_분리_프롬프트.md 내용)
            numbered_conversation: 줄 번호가 붙은 대화 원문

        Returns:
            list: [{"title": str, "start_line": int}, ...] (시작 줄 번호 오름차순),
                  분리할 필요가 없거나 실패하면 빈 리스트
        """
        result = self.gemini.generate_draft(
            segmentation_prompt,
            numbered_conversation,
            instruction=SEGMENTATION_INSTRUCTION,
            model=SEGMENTATION_MODEL,
        )
        if not result:
            result = self.claude_code.generate_draft(
                segmentation_prompt,
                numbered_conversation,
                instruction=SEGMENTATION_INSTRUCTION,
            )
        if not result:
            return []

        try:
            text = result.strip()
            if text.startswith("```"):
                text = re.sub(r"^```(json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()

            data = json.loads(text)
            topics = data.get("topics", [])

            if not isinstance(topics, list) or len(topics) < 2:
                return []

            topics = [
                t for t in topics
                if isinstance(t, dict) and isinstance(t.get("start_line"), int)
            ]
            topics.sort(key=lambda t: t["start_line"])
            return topics

        except Exception:
            return []

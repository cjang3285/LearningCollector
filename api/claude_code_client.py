"""
Claude Code CLI 클라이언트 (Claude Pro 구독 사용) - 영속 프로세스 버전
Gemini 일일 한도 초과 시 폴백으로 사용. 매 호출마다 새 프로세스를 띄우면 claude CLI
자체 기동 오버헤드(~9초/회)가 매번 발생하므로, claude -p --input-format stream-json
세션 하나를 계속 살려두고 재사용한다. 항목 사이에는 "/clear"로 대화 맥락만 리셋해서
서로 다른 JSON 데이터가 섞이지 않게 한다 (검증: /clear 이후 이전 턴 내용을 기억하지 못함).

인증은 CLAUDE_CODE_OAUTH_TOKEN 환경변수(claude setup-token으로 발급받은 장기 토큰)를
사용한다. 브라우저 OAuth 세션과 달리 무인(cron) 환경에서도 재인증 없이 계속 동작한다.
"""
import json
import os
import select
import subprocess
import time

from core import structured_logger as slog

TURN_TIMEOUT_SECONDS = 300
CLEAR_TIMEOUT_SECONDS = 30

# Claude Code 기본 시스템 프롬프트(자동 메모리 조회, 도구 탐색 등)를 완전히 대체한다.
# 기본 프롬프트를 쓰면 --tools ""로 도구를 꺼놔도 "메모리 파일을 읽겠다"는 식의
# 실행되지 않는 도구 호출을 텍스트로 narration해서 실제 초안 대신 출력되는 문제가 있었음.
SYSTEM_PROMPT = (
    "당신은 순수한 텍스트 생성 어시스턴트입니다. 도구를 호출하거나, 파일을 읽거나, "
    "메모리를 확인하거나, 명령을 실행하려 하지 마세요. "
    "오직 사용자의 요청에 대한 답변 텍스트만 바로 출력하세요."
)


class ClaudeCodeClient:
    """claude CLI(-p --input-format stream-json)를 영속 프로세스로 재사용하는 클라이언트"""

    def __init__(self):
        self.last_error_permanent = False
        self.oauth_token = os.getenv("CLAUDE_CODE_OAUTH_TOKEN")
        self._proc = None
        self._turns_sent = 0

    def _build_env(self) -> dict:
        env = os.environ.copy()
        if self.oauth_token:
            env["CLAUDE_CODE_OAUTH_TOKEN"] = self.oauth_token
        return env

    def _start_process(self):
        self._proc = subprocess.Popen(
            [
                "claude", "-p",
                "--input-format", "stream-json",
                "--output-format", "stream-json",
                "--system-prompt", SYSTEM_PROMPT,
                "--tools", "",
                "--no-session-persistence",
                "--setting-sources", "",
                "--verbose",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=self._build_env(),
        )
        self._turns_sent = 0

    def _ensure_process(self):
        if self._proc is None or self._proc.poll() is not None:
            self._start_process()

    def _restart(self):
        if self._proc is not None:
            try:
                self._proc.kill()
                self._proc.wait(timeout=5)
            except Exception:
                pass
        self._proc = None

    def _send_message(self, content: str):
        line = json.dumps(
            {"type": "user", "message": {"role": "user", "content": content}},
            ensure_ascii=False,
        )
        self._proc.stdin.write(line + "\n")
        self._proc.stdin.flush()

    def _read_turn_result(self, timeout_seconds: float):
        """
        다음 "result" 이벤트가 나올 때까지 stdout을 읽는다. 타임아웃/EOF 시 (None, None).

        도중에 나오는 "rate_limit_event"도 함께 추적한다 - Claude Pro 사용량
        한도(5시간 단위 등)가 실제로 소진되면 result.result 텍스트는 그냥 빈 문자열로
        오길래("empty output"), rate_limit_info.status가 "allowed"가 아닌지로
        진짜 한도 초과인지 판단해야 한다.

        Returns:
            (result_event: dict|None, rate_limit_info: dict|None)
        """
        deadline = time.monotonic() + timeout_seconds
        last_rate_limit_info = None
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None, last_rate_limit_info
            ready, _, _ = select.select([self._proc.stdout], [], [], remaining)
            if not ready:
                return None, last_rate_limit_info
            raw_line = self._proc.stdout.readline()
            if raw_line == "":
                return None, last_rate_limit_info  # 프로세스 종료(EOF)
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                event = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "rate_limit_event":
                last_rate_limit_info = event.get("rate_limit_info")
                continue
            if event.get("type") == "result":
                return event, last_rate_limit_info

    def generate_draft(self, prompt: str, json_content: str, instruction: str = None) -> str:
        """
        claude CLI(영속 프로세스)를 통해 블로그 초안 생성

        Args:
            prompt: 프롬프트 (prompts 폴더의 md 파일 내용)
            json_content: JSON 파일 내용
            instruction: 마지막에 덧붙일 지시문 (기본: 블로그 초안 작성 요청)

        Returns:
            str: 생성된 초안 텍스트, 실패 시 None
        """
        if instruction is None:
            instruction = "위 데이터를 바탕으로 블로그 초안을 작성해주세요."

        full_prompt = f"""{prompt}

다음은 참조할 데이터입니다:

```json
{json_content}
```

{instruction}
"""

        self.last_error_permanent = False
        t = slog.start_timer()

        try:
            self._ensure_process()

            # 이전 항목의 맥락이 섞이지 않도록, 첫 턴이 아니면 대화부터 초기화
            if self._turns_sent > 0:
                self._send_message("/clear")
                self._read_turn_result(CLEAR_TIMEOUT_SECONDS)

            self._send_message(full_prompt)
            self._turns_sent += 1
            result_event, rate_limit_info = self._read_turn_result(TURN_TIMEOUT_SECONDS)

            duration = slog.elapsed_ms(t)

            if result_event is None:
                slog.api_error("claude_code", "CLI", "stream-json", duration, "timeout_or_eof")
                print("      ❌ Claude CLI 응답 타임아웃/프로세스 종료 - 다음 호출에서 재시작")
                self._restart()
                return None

            text = (result_event.get("result") or "").strip()
            is_error = bool(result_event.get("is_error"))

            # rate_limit_info.status가 "allowed"가 아니면 실제로 사용량 한도에 걸린 것
            # (result 텍스트는 그냥 빈 문자열로 오기 때문에 텍스트 키워드만으로는 못 잡음)
            rate_limited = bool(rate_limit_info) and rate_limit_info.get("status") != "allowed"

            if not is_error and text and not rate_limited:
                slog.api_call("claude_code", "CLI", "stream-json", 200, duration, True,
                              prompt_len=len(full_prompt), response_len=len(text))
                return text

            error_msg = text or "empty output"
            is_usage_limit = rate_limited or any(keyword in error_msg.lower() for keyword in
                                                 ["usage limit", "rate limit", "quota", "429"])

            if is_usage_limit:
                self.last_error_permanent = True
                slog.api_error("claude_code", "CLI", "stream-json", duration, error_msg[:200],
                               reason="usage_limit_exceeded", rate_limit_info=rate_limit_info)
                print(f"      ❌ Claude Pro 사용량 한도 초과 ({rate_limit_info}).")
            else:
                slog.api_error("claude_code", "CLI", "stream-json", duration, error_msg[:200])
                print(f"      ❌ Claude CLI 호출 실패: {error_msg[:200]}")

            return None

        except (BrokenPipeError, OSError) as e:
            duration = slog.elapsed_ms(t)
            slog.api_error("claude_code", "CLI", "stream-json", duration, str(e))
            print(f"      ❌ Claude CLI 파이프 오류, 재시작: {e}")
            self._restart()
            return None

        except FileNotFoundError:
            self.last_error_permanent = True
            slog.api_error("claude_code", "CLI", "stream-json", 0, "claude command not found")
            print("      ❌ claude 명령어를 찾을 수 없습니다 (설치 확인 필요).")
            return None

    def close(self):
        """파이프라인 종료 시 프로세스 정리"""
        if self._proc is None:
            return
        try:
            self._proc.stdin.close()
            self._proc.wait(timeout=5)
        except Exception:
            try:
                self._proc.kill()
            except Exception:
                pass
        self._proc = None

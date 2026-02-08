"""
Promtail용 구조화된 JSONL 로거

Promtail → Loki → Grafana 파이프라인에서 LogQL 쿼리를 위한 구조화된 로그를 생성합니다.
기존 print() 출력은 그대로 유지하며, 별도의 JSONL 파일에 구조화된 로그를 병행 기록합니다.

출력 파일: log/promtail_feed.jsonl
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path


# 모듈 레벨 싱글톤
_log_file = None


def _get_log_file() -> Path:
    """로그 파일 경로 반환 (lazy init)"""
    global _log_file
    if _log_file is None:
        log_dir = Path(__file__).parent.parent / "log"
        log_dir.mkdir(parents=True, exist_ok=True)
        _log_file = log_dir / "promtail_feed.jsonl"
    return _log_file


def _write(record: dict):
    """JSONL 한 줄 기록"""
    record["ts"] = datetime.now(timezone.utc).isoformat()
    with open(_get_log_file(), "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ── 기본 로그 레벨 ─────────────────────────────────────────

def info(event: str, component: str, **kwargs):
    _write({"level": "INFO", "event": event, "component": component, **kwargs})


def warn(event: str, component: str, **kwargs):
    _write({"level": "WARN", "event": event, "component": component, **kwargs})


def error(event: str, component: str, **kwargs):
    _write({"level": "ERROR", "event": event, "component": component, **kwargs})


# ── 파이프라인 이벤트 ──────────────────────────────────────

def pipeline_start(mode: str):
    """파이프라인 시작"""
    info("pipeline_start", "main", mode=mode)


def pipeline_end(mode: str, success: bool, duration_ms: int, **kwargs):
    """파이프라인 종료"""
    level_fn = info if success else error
    level_fn("pipeline_end", "main", mode=mode, success=success,
             duration_ms=duration_ms, **kwargs)


# ── 수집 이벤트 ────────────────────────────────────────────

def collection_start(source: str):
    """데이터 소스별 수집 시작 (ai_chat, github)"""
    info("collection_start", "collector", source=source)


def collection_end(source: str, total_found: int, duplicates: int,
                   saved: int, duration_ms: int, **kwargs):
    """데이터 소스별 수집 종료"""
    info("collection_end", "collector", source=source,
         total_found=total_found, duplicates=duplicates,
         saved=saved, duration_ms=duration_ms, **kwargs)


# ── JSON 저장 이벤트 ───────────────────────────────────────

def json_saved(source: str, filename: str):
    """JSON 파일 저장 성공"""
    info("json_saved", "storage", source=source, filename=filename)


def json_save_summary(source: str, saved: int, duplicates: int):
    """JSON 저장 요약"""
    info("json_save_summary", "storage", source=source,
         saved=saved, duplicates=duplicates)


# ── 초안 생성 이벤트 ───────────────────────────────────────

def draft_start(draft_type: str, json_file: str):
    """초안 생성 시작"""
    info("draft_start", "draft_generator", draft_type=draft_type,
         json_file=json_file)


def draft_success(draft_type: str, json_file: str, draft_path: str):
    """초안 생성 성공"""
    info("draft_success", "draft_generator", draft_type=draft_type,
         json_file=json_file, draft_path=draft_path)


def draft_failure(draft_type: str, json_file: str, reason: str):
    """초안 생성 실패"""
    error("draft_failure", "draft_generator", draft_type=draft_type,
          json_file=json_file, reason=reason)


def draft_summary(draft_type: str, total: int, success: int,
                  failed: int, duplicates: int):
    """초안 생성 요약"""
    info("draft_summary", "draft_generator", draft_type=draft_type,
         total=total, success=success, failed=failed, duplicates=duplicates)


# ── 블로그 포스팅 이벤트 ───────────────────────────────────

def blog_post_success(title: str, url: str = ""):
    """블로그 포스팅 성공"""
    info("blog_post_success", "blog_api", title=title, url=url)


def blog_post_failure(draft_path: str, reason: str):
    """블로그 포스팅 실패"""
    error("blog_post_failure", "blog_api", draft_path=draft_path,
          reason=reason)


# ── API 호출 이벤트 ────────────────────────────────────────

def api_call(api: str, method: str, endpoint: str, status_code: int,
             duration_ms: int, success: bool, **kwargs):
    """API 호출 로그"""
    level_fn = info if success else warn
    level_fn("api_call", "api", api=api, method=method,
             endpoint=endpoint, status_code=status_code,
             duration_ms=duration_ms, success=success, **kwargs)


def api_error(api: str, method: str, endpoint: str,
              duration_ms: int, error_msg: str, **kwargs):
    """API 호출 예외 발생"""
    error("api_call", "api", api=api, method=method,
          endpoint=endpoint, status_code=0,
          duration_ms=duration_ms, success=False,
          error=error_msg, **kwargs)


# ── 타이밍 유틸리티 ────────────────────────────────────────

def start_timer() -> float:
    """타이머 시작 (monotonic clock)"""
    return time.monotonic()


def elapsed_ms(start: float) -> int:
    """시작 시간으로부터 경과 밀리초"""
    return round((time.monotonic() - start) * 1000)

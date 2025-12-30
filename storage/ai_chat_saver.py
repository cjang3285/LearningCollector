#!/usr/bin/env python3
"""
AI Chat Saver - AI 채팅 마크다운 대화 DB 저장

Claude, ChatGPT, Gemini 마크다운 내보내기 데이터 저장
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import json
from datetime import date
from typing import Dict, List
import logging

from storage.base_saver import BaseSaver
from config.settings import get_log_file
from config.logging_config import setup_logging

# 로깅 설정 (INFO/WARNING → stdout, ERROR → stderr)
logger = setup_logging(get_log_file('ai_chat_saver'), __name__)


class AIChatSaver(BaseSaver):
    """AI 채팅 마크다운 대화 DB 저장"""

    def check_duplicate(self, conversation_data: Dict) -> bool:
        """중복 대화 확인 (link 또는 provider+title+created_at)"""
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cur:
                # Link가 있으면 link로 중복 확인 (가장 확실함)
                if conversation_data.get('link'):
                    cur.execute(
                        """
                        SELECT id FROM learning.ai_chat_conversations
                        WHERE link = %s AND link IS NOT NULL
                        LIMIT 1
                        """,
                        (conversation_data.get('link'),)
                    )
                    if cur.fetchone():
                        logger.info(f"[중복] 링크로 감지: {conversation_data.get('link')}")
                        return True

                # Link가 없으면 provider + title + created_at으로 확인
                cur.execute(
                    """
                    SELECT id FROM learning.ai_chat_conversations
                    WHERE provider = %s
                      AND title = %s
                      AND (created_at = %s OR (created_at IS NULL AND %s IS NULL))
                    LIMIT 1
                    """,
                    (
                        conversation_data.get('provider'),
                        conversation_data.get('title'),
                        conversation_data.get('created_at'),
                        conversation_data.get('created_at')
                    )
                )
                if cur.fetchone():
                    logger.info(f"[중복] 제목+날짜로 감지: {conversation_data.get('title')[:50]}")
                    return True

                return False
        finally:
            conn.close()

    def save_conversation(self, artifact_id: int, conversation_data: Dict) -> int:
        """ai_chat_conversations 테이블에 저장"""
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cur:
                # messages를 JSONB로 변환 (DB 저장용)
                messages_json = json.dumps(conversation_data.get("messages", []))

                cur.execute(
                    """
                    INSERT INTO learning.ai_chat_conversations
                    (artifact_id, provider, title, link, user_messages, assistant_messages,
                     has_code, conversation_path, code_languages, code_blocks_count,
                     created_at, updated_at, messages)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """,
                    (
                        artifact_id,
                        conversation_data.get("provider"),
                        conversation_data.get("title"),
                        conversation_data.get("link"),
                        conversation_data.get("user_messages", 0),
                        conversation_data.get("assistant_messages", 0),
                        conversation_data.get("has_code", False),
                        conversation_data.get("conversation_path"),
                        conversation_data.get("code_languages", []),
                        conversation_data.get("code_blocks_count", 0),
                        conversation_data.get("created_at"),
                        conversation_data.get("updated_at"),
                        messages_json,
                    ),
                )
                result = cur.fetchone()
                conn.commit()

                if result:
                    conv_id = result[0]
                    logger.info(
                        f"[DB] ai_chat_conversations 저장: id={conv_id}, provider={conversation_data.get('provider')}, title={conversation_data.get('title')[:50]}"
                    )
                    return conv_id
                else:
                    logger.info(f"[DB] 대화 저장 실패")
                    return None
        finally:
            conn.close()

    def save_ai_chat_artifact(
        self, conversation_data: Dict, artifact_date: date
    ) -> int:
        """AI 채팅 대화 전체 저장 (파일 + DB)"""
        # 0. 중복 확인
        if self.check_duplicate(conversation_data):
            logger.warning(f"[SKIP] 중복 대화 건너뜀: {conversation_data.get('title', 'Untitled')[:50]}")
            return None

        # 1. 코드 언어 추출
        code_languages = []
        code_blocks = conversation_data.get("code_blocks", [])
        if code_blocks:
            code_languages = list(set(
                block.get("language", "unknown")
                for block in code_blocks
                if block.get("language")
            ))
        conversation_data["code_languages"] = code_languages
        conversation_data["code_blocks_count"] = len(code_blocks)

        # 2. 파일로 저장
        provider = conversation_data.get("provider", "unknown")
        title_safe = "".join(
            c for c in conversation_data.get("title", "untitled")[:50]
            if c.isalnum() or c in (' ', '-', '_')
        ).rstrip()
        filename = f"{provider}_{title_safe}_{artifact_date.strftime('%Y%m%d')}.json"
        storage_path = self.save_to_file(
            conversation_data, artifact_date, f"ai_chat_{provider}", filename
        )

        # 3. learning_artifacts에 저장
        artifact_id = self.save_artifact(
            artifact_date=artifact_date,
            source_type=f"ai_chat_{provider}",
            title=conversation_data.get("title", "Untitled")[:500],
            tags=[provider, "ai_chat"] + code_languages,
            storage_path=storage_path,
            summary=f"{provider} 대화: {conversation_data.get('total_messages', 0)}개 메시지",
            metadata={
                "provider": provider,
                "has_code": conversation_data.get("has_code", False),
                "messages": conversation_data.get("total_messages", 0),
                "link": conversation_data.get("link"),
            },
        )

        # 4. ai_chat_conversations에 저장
        conversation_data["conversation_path"] = storage_path
        conv_id = self.save_conversation(artifact_id, conversation_data)

        # 저장 완료 로그 (파일 경로 + DB ID)
        logger.info(
            f"✅ 저장 완료: artifact_id={artifact_id}, conv_id={conv_id}\n"
            f"   📄 파일: {storage_path}"
        )

        return artifact_id

    def save_all(self, conversations: List[Dict], artifact_date: date) -> List[int]:
        """여러 대화 일괄 저장"""
        artifact_ids = []
        skipped_count = 0
        error_count = 0

        for conversation in conversations:
            try:
                artifact_id = self.save_ai_chat_artifact(conversation, artifact_date)
                if artifact_id:
                    artifact_ids.append(artifact_id)
                else:
                    # artifact_id가 None이면 중복으로 스킵된 것
                    skipped_count += 1
            except Exception as e:
                error_count += 1
                logger.error(
                    f"❌ 대화 저장 실패 (provider={conversation.get('provider', 'unknown')}, "
                    f"title={conversation.get('title', 'unknown')[:50]}): {e}"
                )
                continue

        logger.info(
            f"💾 DB 저장 완료: 성공 {len(artifact_ids)}개, "
            f"중복 스킵 {skipped_count}개, 오류 {error_count}개"
        )
        return artifact_ids

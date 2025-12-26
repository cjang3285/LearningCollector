#!/usr/bin/env python3
"""
Claude Saver - Claude 대화 DB 저장
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

from db_savers.base_saver import BaseSaver
from config.settings import get_log_file

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(get_log_file('claude_saver')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ClaudeSaver(BaseSaver):
    """Claude 대화 DB 저장"""

    def save_conversation(self, artifact_id: int, conversation_data: Dict) -> int:
        """claude_conversations 테이블에 저장"""
        conn = self._get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO learning.claude_conversations
                    (artifact_id, uuid, name, summary, user_messages, assistant_messages,
                     has_code, duration_minutes, conversation_path, code_languages, code_blocks_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (uuid) DO NOTHING
                    RETURNING id
                """,
                    (
                        artifact_id,
                        conversation_data.get("uuid"),
                        conversation_data.get("name"),
                        conversation_data.get("summary"),
                        conversation_data.get("user_messages", 0),
                        conversation_data.get("assistant_messages", 0),
                        conversation_data.get("has_code", False),
                        conversation_data.get("duration_minutes"),
                        conversation_data.get("conversation_path"),
                        conversation_data.get("code_languages", []),
                        conversation_data.get("code_blocks_count", 0),
                    ),
                )
                result = cur.fetchone()
                conn.commit()

                if result:
                    conv_id = result[0]
                    logger.info(
                        f"[DB] claude_conversations 저장: id={conv_id}, uuid={conversation_data.get('uuid')}"
                    )
                    return conv_id
                else:
                    logger.info(f"[DB] 중복 대화 스킵: uuid={conversation_data.get('uuid')}")
                    return None
        finally:
            conn.close()

    def save_claude_artifact(
        self, conversation_data: Dict, artifact_date: date
    ) -> int:
        """Claude 대화 전체 저장 (파일 + DB)"""
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
        filename = f"conversation_{conversation_data['uuid']}.json"
        storage_path = self.save_to_file(
            conversation_data, artifact_date, "claude", filename
        )

        # 3. learning_artifacts에 저장
        artifact_id = self.save_artifact(
            artifact_date=artifact_date,
            source_type="claude",
            title=conversation_data.get("name", "Untitled")[:500],
            tags=["claude"] + code_languages,
            storage_path=storage_path,
            summary=conversation_data.get("summary"),
            metadata={
                "uuid": conversation_data["uuid"],
                "has_code": conversation_data.get("has_code", False),
                "messages": conversation_data.get("user_messages", 0) + conversation_data.get("assistant_messages", 0),
            },
        )

        # 4. claude_conversations에 저장
        conversation_data["conversation_path"] = storage_path
        self.save_conversation(artifact_id, conversation_data)

        return artifact_id

    def save_all(self, conversations: List[Dict], artifact_date: date) -> List[int]:
        """여러 대화 일괄 저장"""
        artifact_ids = []
        for conversation in conversations:
            try:
                artifact_id = self.save_claude_artifact(conversation, artifact_date)
                artifact_ids.append(artifact_id)
            except Exception as e:
                logger.error(
                    f"대화 저장 실패 (uuid={conversation.get('uuid', 'unknown')}): {e}"
                )
                continue

        logger.info(f"Claude 대화 {len(artifact_ids)}개 저장 완료")
        return artifact_ids

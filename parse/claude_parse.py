#!/usr/bin/env python3
"""
Claude Export 파서

conversations.zip을 파싱하여 대화 데이터를 추출합니다.
"""

import json
import zipfile
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class ConversationData:
    """파싱된 대화 데이터"""
    uuid: str
    name: str
    summary: str
    created_at: str
    updated_at: str
    user_messages: int
    assistant_messages: int
    total_chars: int
    has_code: bool
    code_blocks: List[Dict]
    duration_minutes: float
    
    def to_dict(self):
        return asdict(self)


class ClaudeParser:
    """Claude Export 파서"""
    
    def parse_zip(self, zip_path: str) -> List[Dict]:
        """ZIP 파일에서 conversations.json 파싱"""
        with zipfile.ZipFile(zip_path, 'r') as z:
            if 'conversations.json' not in z.namelist():
                raise ValueError("conversations.json을 찾을 수 없음")
            
            with z.open('conversations.json') as f:
                data = json.load(f)
        
        return data
    
    def parse_json(self, json_path: str) -> List[Dict]:
        """JSON 파일 직접 파싱"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    
    def filter_by_date(
        self, 
        conversations: List[Dict], 
        after: Optional[datetime] = None,
        before: Optional[datetime] = None,
        min_messages: int = 2
    ) -> List[Dict]:
        """날짜로 필터링"""
        filtered = []
        for conv in conversations:
            updated_at = datetime.fromisoformat(
                conv['updated_at'].replace('Z', '+00:00')
            )
            
            if after and updated_at < after:
                continue
            if before and updated_at > before:
                continue
            
            if len(conv['chat_messages']) < min_messages:
                continue
            
            filtered.append(conv)
        
        return filtered
    
    def extract_code_blocks(self, conv: Dict) -> List[Dict]:
        """코드 블록 추출"""
        blocks = []
        for msg in conv['chat_messages']:
            text = msg['text']
            parts = text.split('```')
            
            for i in range(1, len(parts), 2):
                if i < len(parts):
                    lines = parts[i].split('\n', 1)
                    language = lines[0].strip() if lines else ''
                    code = lines[1] if len(lines) > 1 else parts[i]
                    
                    blocks.append({
                        'language': language,
                        'code': code,
                        'lines': code.count('\n') + 1,
                        'sender': msg['sender']
                    })
        
        return blocks
    
    def parse_conversation(self, conv: Dict) -> ConversationData:
        """대화를 ConversationData로 변환"""
        user_msgs = sum(
            1 for msg in conv['chat_messages'] 
            if msg['sender'] == 'human'
        )
        assistant_msgs = sum(
            1 for msg in conv['chat_messages'] 
            if msg['sender'] == 'assistant'
        )
        
        total_chars = sum(
            len(msg['text']) 
            for msg in conv['chat_messages']
        )
        
        has_code = any(
            '```' in msg['text'] 
            for msg in conv['chat_messages']
        )
        
        code_blocks = self.extract_code_blocks(conv)
        
        created = datetime.fromisoformat(
            conv['created_at'].replace('Z', '+00:00')
        )
        updated = datetime.fromisoformat(
            conv['updated_at'].replace('Z', '+00:00')
        )
        
        duration = (updated - created).total_seconds() / 60
        
        return ConversationData(
            uuid=conv['uuid'],
            name=conv['name'],
            summary=conv.get('summary', ''),
            created_at=conv['created_at'],
            updated_at=conv['updated_at'],
            user_messages=user_msgs,
            assistant_messages=assistant_msgs,
            total_chars=total_chars,
            has_code=has_code,
            code_blocks=code_blocks,
            duration_minutes=duration
        )


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("사용법: python claude_parse.py <conversations.zip>")
        sys.exit(1)
    
    parser = ClaudeParser()
    conversations = parser.parse_zip(sys.argv[1])
    
    print(f"총 {len(conversations)}개 대화 로드됨")

"""
Gemini Draft 생성 모듈 (메인 흐름)
지난 실행 시간 이후로 수집된 JSON을 참조하여 3가지 초안을 생성하고 VS Code로 연다
"""
import os
import subprocess
from pathlib import Path
from typing import List, Tuple

# API 모듈 임포트
from api.ai_client import AIClient
from api.blog_api import BlogAPIClient

# 정책 모듈 임포트
from policies.storage.draft_saver import DraftSaver


class GeminiDraftGenerator:
    """Gemini를 사용한 초안 생성 클래스"""

    def __init__(self):
        self.ai_client = AIClient()
        self.blog_client = BlogAPIClient()
        self.draft_saver = DraftSaver()
        self.editor_command = os.getenv("EDITOR_COMMAND", "nano")
        self.quota_exhausted = False  # 일일 한도 초과 플래그

    def generate_drafts(
        self,
        ai_chat_jsons: List[str],
        baekjoon_jsons: List[str],
        commit_jsons: List[str]
    ) -> Tuple[List[str], List[str]]:
        """
        3가지 초안 생성
        1. 백준 풀이 초안
        2. 개발 진척 초안
        3. AI 대화 공부 초안

        Returns:
            Tuple[List[str], List[str]]:
                - 생성된 draft 파일 경로 리스트
                - 초안 생성에 성공한 JSON 파일명 리스트
        """
        all_drafts = []
        all_succeeded_jsons = []

        # 1. 백준 풀이 초안 작성
        if baekjoon_jsons:
            print(f"  백준 풀이 초안 생성 중... ({len(baekjoon_jsons)}개)")
            baekjoon_drafts, succeeded = self._generate_baekjoon_drafts(baekjoon_jsons)
            all_drafts.extend(baekjoon_drafts)
            all_succeeded_jsons.extend(succeeded)
            print(f"    → {len(baekjoon_drafts)}개 생성 완료")

        # 2. 개발 진척 초안 작성
        if commit_jsons:
            print(f"  개발 진척 초안 생성 중... ({len(commit_jsons)}개)")
            dev_drafts, succeeded = self._generate_dev_drafts(commit_jsons)
            all_drafts.extend(dev_drafts)
            all_succeeded_jsons.extend(succeeded)
            print(f"    → {len(dev_drafts)}개 생성 완료")

        # 3. AI 대화 공부 초안 작성
        if ai_chat_jsons:
            print(f"  AI 대화 공부 초안 생성 중... ({len(ai_chat_jsons)}개)")
            study_drafts, succeeded = self._generate_study_drafts(ai_chat_jsons)
            all_drafts.extend(study_drafts)
            all_succeeded_jsons.extend(succeeded)
            print(f"    → {len(study_drafts)}개 생성 완료")

        # 4. 블로그 포스팅 (초안 생성 직후)
        if all_drafts:
            print(f"\n  블로그 포스팅 중... ({len(all_drafts)}개)")
            self._post_to_blog(all_drafts)

        # 5. 에디터로 열기 (맨 마지막)
        if all_drafts:
            self._open_in_editor(all_drafts)

        return all_drafts, all_succeeded_jsons

    def _generate_baekjoon_drafts(self, json_files: List[str]) -> Tuple[List[str], List[str]]:
        """백준 풀이 초안 생성

        Returns:
            Tuple[List[str], List[str]]: (draft 파일 경로 리스트, 성공한 JSON 파일명 리스트)
        """
        drafts = []
        succeeded_jsons = []
        duplicates = []

        print(f"    총 {len(json_files)}개의 백준 JSON 발견")

        for json_file in json_files:
            # 일일 한도 초과 시 나머지 스킵
            if self.quota_exhausted:
                print(f"    한도 초과로 스킵: {json_file}")
                continue

            # 중복 체크
            if self.draft_saver.is_duplicate_draft(json_file, "algorithm"):
                duplicates.append(json_file)
                succeeded_jsons.append(json_file)
                continue

            print(f"    처리 중: {json_file}")

            # Gemini로 초안 생성
            prompt = self._load_prompt("알고리즘_풀이_포스팅_프롬프트.md")
            json_content = self._load_json(json_file)

            draft_content = self.ai_client.generate_draft(prompt, json_content)

            # 생성 실패 시 스킵
            if draft_content is None:
                self.quota_exhausted = True  # 모든 AI 제공자 실패
                print(f"    ⚠️  AI API 모두 실패. 나머지 백준 draft 생성 중단")
                break

            # Draft 저장
            draft_path = self.draft_saver.save_draft(
                draft_type="algorithm",
                content=draft_content,
                source_json=json_file
            )
            drafts.append(draft_path)
            succeeded_jsons.append(json_file)
            print(f"    ✅ 성공: {draft_path}")

        # 중복 로깅
        if duplicates:
            print(f"    ⚠️  중복 제외: {len(duplicates)}개 (이미 draft 생성됨)")
            for dup in duplicates:
                print(f"      - {dup}")

        return drafts, succeeded_jsons

    def _generate_dev_drafts(self, json_files: List[str]) -> Tuple[List[str], List[str]]:
        """개발 진척 초안 생성

        Returns:
            Tuple[List[str], List[str]]: (draft 파일 경로 리스트, 성공한 JSON 파일명 리스트)
        """
        drafts = []
        succeeded_jsons = []
        duplicates = []

        print(f"    총 {len(json_files)}개의 개발 커밋 JSON 발견")

        for json_file in json_files:
            # 일일 한도 초과 시 나머지 스킵
            if self.quota_exhausted:
                print(f"    한도 초과로 스킵: {json_file}")
                continue

            # 중복 체크
            if self.draft_saver.is_duplicate_draft(json_file, "dev"):
                duplicates.append(json_file)
                succeeded_jsons.append(json_file)
                continue

            print(f"    처리 중: {json_file}")

            # Gemini로 초안 생성
            prompt = self._load_prompt("프로젝트_진척_및_의사결정_요약_프롬프트.md")
            json_content = self._load_json(json_file)

            draft_content = self.ai_client.generate_draft(prompt, json_content)

            # 생성 실패 시 스킵
            if draft_content is None:
                self.quota_exhausted = True  # 모든 AI 제공자 실패
                print(f"    ⚠️  AI API 모두 실패. 나머지 개발 draft 생성 중단")
                break

            # Draft 저장
            draft_path = self.draft_saver.save_draft(
                draft_type="dev",
                content=draft_content,
                source_json=json_file
            )
            drafts.append(draft_path)
            succeeded_jsons.append(json_file)
            print(f"    ✅ 성공: {draft_path}")

        # 중복 로깅
        if duplicates:
            print(f"    ⚠️  중복 제외: {len(duplicates)}개 (이미 draft 생성됨)")
            for dup in duplicates:
                print(f"      - {dup}")

        return drafts, succeeded_jsons

    def _generate_study_drafts(self, json_files: List[str]) -> Tuple[List[str], List[str]]:
        """AI 대화 공부 초안 생성

        Returns:
            Tuple[List[str], List[str]]: (draft 파일 경로 리스트, 성공한 JSON 파일명 리스트)
        """
        drafts = []
        succeeded_jsons = []
        duplicates = []

        print(f"    총 {len(json_files)}개의 AI Chat JSON 발견")

        for json_file in json_files:
            # 일일 한도 초과 시 나머지 스킵
            if self.quota_exhausted:
                print(f"    한도 초과로 스킵: {json_file}")
                continue

            # 중복 체크
            if self.draft_saver.is_duplicate_draft(json_file, "study"):
                duplicates.append(json_file)
                succeeded_jsons.append(json_file)
                continue

            print(f"    처리 중: {json_file}")

            # Gemini로 초안 생성
            prompt = self._load_prompt("당일_공부_요약_프롬프트.md")
            json_content = self._load_json(json_file)

            draft_content = self.ai_client.generate_draft(prompt, json_content)

            # 생성 실패 시 스킵
            if draft_content is None:
                self.quota_exhausted = True  # 모든 AI 제공자 실패
                print(f"    ⚠️  AI API 모두 실패. 나머지 학습 draft 생성 중단")
                break

            # Draft 저장
            draft_path = self.draft_saver.save_draft(
                draft_type="study",
                content=draft_content,
                source_json=json_file
            )
            drafts.append(draft_path)
            succeeded_jsons.append(json_file)
            print(f"    ✅ 성공: {draft_path}")

        # 중복 로깅
        if duplicates:
            print(f"    ⚠️  중복 제외: {len(duplicates)}개 (이미 draft 생성됨)")
            for dup in duplicates:
                print(f"      - {dup}")

        return drafts, succeeded_jsons

    def _load_prompt(self, prompt_filename: str) -> str:
        """프롬프트 파일 로드"""
        prompt_path = Path(__file__).parent.parent / "prompts" / prompt_filename
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _load_json(self, json_filename: str) -> str:
        """JSON 파일 로드"""
        # data/ 폴더에서 JSON 파일 찾기
        data_dir = Path(__file__).parent.parent / "data"

        # baekjoon, commits, ai_chat 폴더에서 검색
        for subdir in ["baekjoon", "commits", "ai_chat"]:
            json_path = data_dir / subdir / json_filename
            if json_path.exists():
                with open(json_path, "r", encoding="utf-8") as f:
                    return f.read()

        raise FileNotFoundError(f"JSON 파일을 찾을 수 없습니다: {json_filename}")

    def _open_in_editor(self, draft_paths: List[str]):
        """생성된 초안들을 에디터로 열기"""
        if not draft_paths:
            return

        try:
            # nano는 한 번에 여러 파일 지원하지 않으므로 첫 번째 파일만 열기
            if self.editor_command == "nano":
                print(f"\n  에디터로 첫 번째 파일 열기: {draft_paths[0]}")
                subprocess.run([self.editor_command, draft_paths[0]])
            else:
                # code, vim 등은 여러 파일 지원
                subprocess.run([self.editor_command] + draft_paths, check=True)
                print(f"\n  에디터로 {len(draft_paths)}개 파일 열기 완료")
        except subprocess.CalledProcessError as e:
            print(f"  에디터 실행 실패: {str(e)}")
        except FileNotFoundError:
            print(f"  에디터를 찾을 수 없습니다: {self.editor_command}")

    def _post_to_blog(self, draft_paths: List[str]):
        """블로그에 포스팅"""
        for draft_path in draft_paths:
            try:
                # Draft 파일에서 메타데이터 추출 (H1 제목, 첫 문단 등)
                result = self.blog_client.create_post_from_draft(draft_path)

                if result.get("success"):
                    print(f"    ✅ 블로그 포스팅 완료: {result.get('title', 'Unknown')}")
                    if result.get("url"):
                        print(f"       URL: {result['url']}")
                else:
                    print(f"    ❌ 블로그 포스팅 실패: {draft_path}")
                    print(f"       오류: {result.get('message', 'Unknown error')}")

            except Exception as e:
                print(f"    ❌ 블로그 포스팅 예외 발생: {draft_path} - {str(e)}")

    def _extract_title(self, markdown_content: str) -> str:
        """마크다운에서 제목 추출"""
        lines = markdown_content.split("\n")
        for line in lines:
            if line.startswith("# "):
                return line[2:].strip()
        return "제목 없음"


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    generator = GeminiDraftGenerator()
    generator.generate_drafts(
        ai_chat_jsons=["example_chat.json"],
        baekjoon_jsons=["example_baekjoon.json"],
        commit_jsons=["example_commit.json"]
    )

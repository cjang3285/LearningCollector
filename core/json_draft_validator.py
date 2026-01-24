"""
JSON + Draft 통합 검증 모듈
data/ 폴더의 모든 JSON 파일과 Draft 파일을 정책에 의거하여 검증
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import json
import re
from typing import Dict, List, Tuple
from dataclasses import dataclass

from policies.validation.schema_policy import SchemaPolicy


@dataclass
class ValidationResult:
    """검증 결과 데이터 클래스"""
    file_path: str
    file_type: str  # json_type (baekjoon, commits, ai_chat) 또는 draft_type (algorithm, dev, study)
    is_valid: bool
    errors: List[str]


class JSONDraftValidator:
    """JSON + Draft 통합 검증 클래스"""

    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / "data"
        self.schema_policy = SchemaPolicy()
        self.draft_rules = SchemaPolicy.DRAFT_VALIDATION_RULES

    def validate_all(self) -> Dict[str, Dict[str, List[ValidationResult]]]:
        """
        모든 JSON 파일과 Draft 파일 검증

        Returns:
            Dict[str, Dict[str, List[ValidationResult]]]:
            {
                "json": {"baekjoon": [...], "commits": [...], "ai_chat": [...]},
                "draft": {"algorithm": [...], "dev": [...], "study": [...]}
            }
        """
        results = {
            "json": {
                "baekjoon": [],
                "commits": [],
                "ai_chat": []
            },
            "draft": {
                "algorithm": [],
                "dev": [],
                "study": []
            }
        }

        # JSON 검증
        for json_type in ["baekjoon", "commits", "ai_chat"]:
            folder = self.data_dir / json_type
            if not folder.exists():
                print(f"⚠️  JSON 폴더가 존재하지 않습니다: {folder}")
                continue

            json_files = list(folder.glob("*.json"))
            for json_file in json_files:
                result = self._validate_json_file(json_file, json_type)
                results["json"][json_type].append(result)

        # Draft 검증
        draft_dir = self.data_dir / "draft"
        if not draft_dir.exists():
            print(f"⚠️  Draft 폴더가 존재하지 않습니다: {draft_dir}")
        else:
            for draft_type in ["algorithm", "dev", "study"]:
                draft_folder = draft_dir / draft_type
                if not draft_folder.exists():
                    print(f"⚠️  Draft 타입 폴더가 존재하지 않습니다: {draft_folder}")
                    continue

                draft_files = list(draft_folder.glob("*.md"))
                for draft_file in draft_files:
                    result = self._validate_draft_file(draft_file, draft_type)
                    results["draft"][draft_type].append(result)

        # JSON-Draft 매핑 검증
        mapping_results = self._validate_json_draft_mapping(results)

        # 매핑 검증 결과를 draft 결과에 추가
        for draft_type, mapping_errors in mapping_results.items():
            results["draft"][draft_type].extend(mapping_errors)

        return results

    def _validate_json_file(self, file_path: Path, json_type: str) -> ValidationResult:
        """단일 JSON 파일 검증"""
        try:
            # JSON 파일 읽기
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 스키마 검증
            is_valid, errors = self.schema_policy.validate_json(data, json_type)

            return ValidationResult(
                file_path=str(file_path),
                file_type=json_type,
                is_valid=is_valid,
                errors=errors
            )

        except json.JSONDecodeError as e:
            return ValidationResult(
                file_path=str(file_path),
                file_type=json_type,
                is_valid=False,
                errors=[f"JSON 파싱 오류: {str(e)}"]
            )
        except Exception as e:
            return ValidationResult(
                file_path=str(file_path),
                file_type=json_type,
                is_valid=False,
                errors=[f"파일 읽기 오류: {str(e)}"]
            )

    def _validate_draft_file(self, file_path: Path, draft_type: str) -> ValidationResult:
        """단일 Draft 파일 검증"""
        errors = []

        try:
            # 1. 파일명 규칙 검증
            filename = file_path.name
            filename_pattern = self.draft_rules["filename_pattern"]
            if not re.match(filename_pattern, filename):
                errors.append(f"파일명 패턴 불일치: {filename_pattern}")

            # 2. 파일명 prefix와 폴더명 일치 검증
            if not filename.startswith(draft_type + "_"):
                errors.append(f"파일명 prefix와 폴더명 불일치 (예상: {draft_type}_xxx.md)")

            # 파일 내용 읽기
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 3. 최소 글자 수 검증
            min_length = self.draft_rules["min_length"]
            if len(content) < min_length:
                errors.append(f"최소 글자 수 미달 ({len(content)}자 < {min_length}자)")

            # 4. H1 제목 존재 검증
            h1_pattern = self.draft_rules["h1_pattern"]
            if not re.search(h1_pattern, content, re.MULTILINE):
                errors.append("H1 제목(# )이 없습니다")

            # 5. H2 섹션 존재 검증
            h2_pattern = self.draft_rules["h2_pattern"]
            if not re.search(h2_pattern, content, re.MULTILINE):
                errors.append("H2 섹션(## )이 없습니다")

            # 6. 오류 키워드 감지
            error_keywords = self.draft_rules["error_keywords"]
            # 첫 10줄만 체크
            lines = content.split("\n")[:10]
            first_10_lines = "\n".join(lines)

            for keyword in error_keywords:
                if keyword in first_10_lines:
                    errors.append(f"오류 키워드 감지: '{keyword}'")
                    break

            return ValidationResult(
                file_path=str(file_path),
                file_type=draft_type,
                is_valid=len(errors) == 0,
                errors=errors
            )

        except Exception as e:
            return ValidationResult(
                file_path=str(file_path),
                file_type=draft_type,
                is_valid=False,
                errors=[f"파일 읽기 오류: {str(e)}"]
            )

    def _validate_json_draft_mapping(self, results: Dict) -> Dict[str, List[ValidationResult]]:
        """
        JSON-Draft 매핑 검증
        JSON 파일이 있는데 해당하는 Draft 파일이 없으면 검증 실패

        Returns:
            Dict[str, List[ValidationResult]]: draft_type별 매핑 검증 실패 결과
        """
        mapping_errors = {
            "algorithm": [],
            "dev": [],
            "study": []
        }

        draft_type_mapping = self.draft_rules["draft_type_mapping"]

        # JSON 타입별로 순회
        for json_type, json_results in results["json"].items():
            draft_type = draft_type_mapping.get(json_type)
            if not draft_type:
                continue

            # 해당 JSON 타입의 valid한 JSON 파일들만 체크
            valid_json_files = [
                r for r in json_results if r.is_valid
            ]

            # 해당 draft 타입의 모든 draft 파일명 수집
            draft_results = results["draft"].get(draft_type, [])
            existing_drafts = set()

            for draft_result in draft_results:
                draft_path = Path(draft_result.file_path)
                # draft 파일명에서 "draft_type_" prefix 제거
                draft_name = draft_path.stem.replace(f"{draft_type}_", "")
                existing_drafts.add(draft_name)

            # JSON 파일마다 대응하는 draft가 있는지 확인
            for json_result in valid_json_files:
                json_path = Path(json_result.file_path)
                json_name = json_path.stem  # .json 제거

                if json_name not in existing_drafts:
                    # Draft가 없음 - 검증 실패
                    mapping_errors[draft_type].append(
                        ValidationResult(
                            file_path=f"[매핑 오류] {json_path.name}",
                            file_type=draft_type,
                            is_valid=False,
                            errors=[f"JSON 파일에 대응하는 Draft가 없습니다: {json_path.name}"]
                        )
                    )

        return mapping_errors

    def print_report(self, results: Dict[str, Dict[str, List[ValidationResult]]]):
        """검증 결과 출력"""
        print("\n" + "=" * 80)
        print("JSON + Draft 통합 검증 보고서")
        print("=" * 80 + "\n")

        # JSON 검증 결과
        print("📄 JSON 검증 결과")
        print("-" * 80)

        json_total_files = 0
        json_total_valid = 0
        json_total_invalid = 0

        for json_type, type_results in results["json"].items():
            if not type_results:
                print(f"[{json_type}] 검증할 파일 없음")
                continue

            valid_count = sum(1 for r in type_results if r.is_valid)
            invalid_count = len(type_results) - valid_count

            json_total_files += len(type_results)
            json_total_valid += valid_count
            json_total_invalid += invalid_count

            print(f"\n[{json_type}]")
            print(f"  총 파일: {len(type_results)}개")
            print(f"  ✅ 통과: {valid_count}개")
            print(f"  ❌ 실패: {invalid_count}개")

            # 실패 상세
            if invalid_count > 0:
                print(f"\n  실패 상세:")
                for result in type_results:
                    if not result.is_valid:
                        filename = Path(result.file_path).name
                        print(f"\n    📄 {filename}")
                        for error in result.errors:
                            print(f"       - {error}")

        print("\n" + "-" * 80)
        print(f"JSON 요약: {json_total_files}개 파일 중 ✅ {json_total_valid}개 통과, ❌ {json_total_invalid}개 실패")
        print()

        # Draft 검증 결과
        print("\n📝 Draft 검증 결과")
        print("-" * 80)

        draft_total_files = 0
        draft_total_valid = 0
        draft_total_invalid = 0

        for draft_type, type_results in results["draft"].items():
            if not type_results:
                print(f"[{draft_type}] 검증할 파일 없음")
                continue

            valid_count = sum(1 for r in type_results if r.is_valid)
            invalid_count = len(type_results) - valid_count

            draft_total_files += len(type_results)
            draft_total_valid += valid_count
            draft_total_invalid += invalid_count

            print(f"\n[{draft_type}]")
            print(f"  총 파일: {len(type_results)}개")
            print(f"  ✅ 통과: {valid_count}개")
            print(f"  ❌ 실패: {invalid_count}개")

            # 실패 상세
            if invalid_count > 0:
                print(f"\n  실패 상세:")
                for result in type_results:
                    if not result.is_valid:
                        # 매핑 오류인 경우 특별 표시
                        if result.file_path.startswith("[매핑 오류]"):
                            print(f"\n    🔗 {result.file_path}")
                        else:
                            filename = Path(result.file_path).name
                            print(f"\n    📝 {filename}")
                        for error in result.errors:
                            print(f"       - {error}")

        print("\n" + "-" * 80)
        print(f"Draft 요약: {draft_total_files}개 파일 중 ✅ {draft_total_valid}개 통과, ❌ {draft_total_invalid}개 실패")
        print()

        # 전체 요약
        print("\n" + "=" * 80)
        total_files = json_total_files + draft_total_files
        total_valid = json_total_valid + draft_total_valid
        total_invalid = json_total_invalid + draft_total_invalid
        print(f"전체 요약: {total_files}개 파일 중 ✅ {total_valid}개 통과, ❌ {total_invalid}개 실패")
        print("=" * 80 + "\n")

    def get_failed_files(self, results: Dict[str, Dict[str, List[ValidationResult]]]) -> List[str]:
        """검증 실패 파일 경로 리스트 반환 (JSON + Draft 합산)"""
        failed_files = []

        # JSON 실패 파일
        for json_type, type_results in results["json"].items():
            for result in type_results:
                if not result.is_valid:
                    failed_files.append(result.file_path)

        # Draft 실패 파일 (매핑 오류 제외)
        for draft_type, type_results in results["draft"].items():
            for result in type_results:
                if not result.is_valid and not result.file_path.startswith("[매핑 오류]"):
                    failed_files.append(result.file_path)

        return failed_files


if __name__ == "__main__":
    # 검증 실행
    validator = JSONDraftValidator()
    print("🔍 JSON + Draft 파일 검증 시작...\n")
    results = validator.validate_all()
    validator.print_report(results)

    # 실패 파일 처리
    failed_files = validator.get_failed_files(results)

    if failed_files:
        response = input(f"\n⚠️  {len(failed_files)}개의 실패 파일을 삭제하시겠습니까? (y/n): ")
        if response.lower() in ['y', 'yes']:
            import os
            deleted_count = 0
            for file_path in failed_files:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                    print(f"삭제: {Path(file_path).name}")
                except Exception as e:
                    print(f"삭제 실패: {file_path} - {str(e)}")
            print(f"\n🗑️  {deleted_count}개 파일 삭제 완료")
    else:
        print("\n✅ 모든 파일이 검증을 통과했습니다!")

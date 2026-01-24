"""
JSON 검증 모듈
data/ 폴더의 모든 JSON 파일을 정책에 의거하여 검증
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import json
from typing import Dict, List, Tuple
from dataclasses import dataclass

from policies.validation.schema_policy import SchemaPolicy


@dataclass
class ValidationResult:
    """검증 결과 데이터 클래스"""
    file_path: str
    json_type: str
    is_valid: bool
    errors: List[str]


class JSONValidator:
    """JSON 검증 클래스"""

    def __init__(self):
        self.data_dir = Path(__file__).parent.parent / "data"
        self.schema_policy = SchemaPolicy()

    def validate_all(self) -> Dict[str, List[ValidationResult]]:
        """
        모든 JSON 파일 검증

        Returns:
            Dict[str, List[ValidationResult]]: JSON 타입별 검증 결과
        """
        results = {
            "baekjoon": [],
            "commits": [],
            "ai_chat": []
        }

        # 각 폴더별 검증
        for json_type in ["baekjoon", "commits", "ai_chat"]:
            folder = self.data_dir / json_type
            if not folder.exists():
                print(f"⚠️  폴더가 존재하지 않습니다: {folder}")
                continue

            # JSON 파일 검증
            json_files = list(folder.glob("*.json"))
            for json_file in json_files:
                result = self._validate_file(json_file, json_type)
                results[json_type].append(result)

        return results

    def _validate_file(self, file_path: Path, json_type: str) -> ValidationResult:
        """단일 JSON 파일 검증"""
        try:
            # JSON 파일 읽기
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 스키마 검증
            is_valid, errors = self.schema_policy.validate_json(data, json_type)

            return ValidationResult(
                file_path=str(file_path),
                json_type=json_type,
                is_valid=is_valid,
                errors=errors
            )

        except json.JSONDecodeError as e:
            return ValidationResult(
                file_path=str(file_path),
                json_type=json_type,
                is_valid=False,
                errors=[f"JSON 파싱 오류: {str(e)}"]
            )
        except Exception as e:
            return ValidationResult(
                file_path=str(file_path),
                json_type=json_type,
                is_valid=False,
                errors=[f"파일 읽기 오류: {str(e)}"]
            )

    def print_report(self, results: Dict[str, List[ValidationResult]]):
        """검증 결과 출력"""
        print("\n" + "=" * 80)
        print("JSON 검증 보고서")
        print("=" * 80 + "\n")

        total_files = 0
        total_valid = 0
        total_invalid = 0

        for json_type, type_results in results.items():
            if not type_results:
                print(f"[{json_type}] 검증할 파일 없음\n")
                continue

            valid_count = sum(1 for r in type_results if r.is_valid)
            invalid_count = len(type_results) - valid_count

            total_files += len(type_results)
            total_valid += valid_count
            total_invalid += invalid_count

            # 타입별 요약
            print(f"[{json_type}]")
            print(f"  총 파일: {len(type_results)}개")
            print(f"  ✅ 통과: {valid_count}개")
            print(f"  ❌ 실패: {invalid_count}개")

            # 실패한 파일 상세
            if invalid_count > 0:
                print(f"\n  실패 상세:")
                for result in type_results:
                    if not result.is_valid:
                        filename = Path(result.file_path).name
                        print(f"\n    📄 {filename}")
                        for error in result.errors:
                            print(f"       - {error}")

            print()

        # 전체 요약
        print("=" * 80)
        print(f"전체 요약: {total_files}개 파일 중 ✅ {total_valid}개 통과, ❌ {total_invalid}개 실패")
        print("=" * 80 + "\n")

    def print_schema_guide(self):
        """스키마 가이드 출력"""
        print("\n" + "=" * 80)
        print("JSON 스키마 가이드")
        print("=" * 80 + "\n")

        for json_type in ["baekjoon", "commits", "ai_chat"]:
            schema = self.schema_policy.get_schema(json_type)
            print(f"[{json_type}]")

            for field_name, field_schema in schema.items():
                required = "필수" if field_schema["required"] else "선택"
                type_name = field_schema["type"].__name__
                description = field_schema.get("description", "")
                pattern = field_schema.get("pattern", "")

                print(f"  • {field_name} ({required}, {type_name})")
                if description:
                    print(f"    설명: {description}")
                if pattern:
                    print(f"    패턴: {pattern}")

            print()


def run_validator():
    """검증 실행"""
    validator = JSONValidator()

    print("🔍 JSON 파일 검증 시작...\n")

    # 검증 실행
    results = validator.validate_all()

    # 결과 출력
    validator.print_report(results)

    # 스키마 가이드 출력 (옵션)
    # validator.print_schema_guide()


if __name__ == "__main__":
    run_validator()

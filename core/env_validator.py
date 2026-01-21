"""
환경변수 검증 모듈
각 환경변수가 메인 기능 전반에 사용되어 주요 기능 실행에 에러를 발생시키지 않는지 확인
"""
import os
from pathlib import Path
from tkinter import messagebox
import requests


class EnvValidator:
    """환경변수 검증 클래스"""

    def __init__(self):
        self.errors = []

    def validate_all(self):
        """모든 환경변수 검증"""
        self.errors = []

        # Module 1: 인증 정보 검증
        self._validate_github_token()
        self._validate_gemini_api_key()

        # Module 2: 감시 경로 검증
        self._validate_ai_chat_download_dir()
        self._validate_log_file_path()

        # Module 3: 필터링 및 환경 설정 검증
        self._validate_github_username()
        self._validate_editor_command()

        return len(self.errors) == 0, self.errors

    def _validate_github_token(self):
        """GitHub Token 검증"""
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            self.errors.append("GITHUB_TOKEN이 설정되지 않았습니다.")
            return

        # GitHub API로 토큰 유효성 확인
        try:
            headers = {"Authorization": f"token {token}"}
            response = requests.get("https://api.github.com/user", headers=headers, timeout=10)
            if response.status_code != 200:
                self.errors.append("GITHUB_TOKEN이 유효하지 않습니다. (API 응답 실패)")
        except Exception as e:
            self.errors.append(f"GITHUB_TOKEN 검증 중 오류 발생: {str(e)}")

    def _validate_gemini_api_key(self):
        """Gemini API Key 검증"""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self.errors.append("GEMINI_API_KEY가 설정되지 않았습니다.")
            return

        # API 키 형식 간단 검증
        if not api_key.startswith("AI"):
            self.errors.append("GEMINI_API_KEY 형식이 올바르지 않습니다.")

    def _validate_ai_chat_download_dir(self):
        """AI Chat 다운로드 디렉터리 검증"""
        download_dir = os.getenv("AI_CHAT_DOWNLOAD_DIR")
        if not download_dir:
            self.errors.append("AI_CHAT_DOWNLOAD_DIR이 설정되지 않았습니다.")
            return

        # 경로 존재 여부 확인
        path = Path(download_dir)
        if not path.exists():
            self.errors.append(f"AI_CHAT_DOWNLOAD_DIR 경로가 존재하지 않습니다: {download_dir}")
        elif not path.is_dir():
            self.errors.append(f"AI_CHAT_DOWNLOAD_DIR이 디렉터리가 아닙니다: {download_dir}")

    def _validate_log_file_path(self):
        """로그 파일 경로 검증"""
        log_path = os.getenv("LOG_FILE_PATH", "./log/err.log")

        # 로그 디렉터리 생성 가능 여부 확인
        log_file = Path(log_path)
        log_dir = log_file.parent

        try:
            log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.errors.append(f"로그 디렉터리를 생성할 수 없습니다: {str(e)}")

    def _validate_github_username(self):
        """GitHub 사용자명 검증"""
        username = os.getenv("GITHUB_USERNAME")
        if not username:
            self.errors.append("GITHUB_USERNAME이 설정되지 않았습니다.")
            return

        # GitHub API로 사용자 존재 여부 확인
        try:
            response = requests.get(f"https://api.github.com/users/{username}", timeout=10)
            if response.status_code == 404:
                self.errors.append(f"GitHub 사용자를 찾을 수 없습니다: {username}")
            elif response.status_code != 200:
                self.errors.append(f"GitHub 사용자명 검증 실패: HTTP {response.status_code}")
        except Exception as e:
            self.errors.append(f"GITHUB_USERNAME 검증 중 오류 발생: {str(e)}")

    def _validate_editor_command(self):
        """에디터 명령어 검증"""
        editor_cmd = os.getenv("EDITOR_COMMAND", "code")

        # 명령어 존재 여부 확인 (간단한 체크)
        import shutil
        if not shutil.which(editor_cmd):
            self.errors.append(f"에디터 명령어를 찾을 수 없습니다: {editor_cmd}")

    def show_validation_result(self, is_valid, errors):
        """검증 결과를 UI로 표시"""
        if is_valid:
            messagebox.showinfo("성공", "모든 환경변수가 정상적으로 검증되었습니다.")
            return True
        else:
            error_message = "다음 문제를 해결해주세요:\n\n" + "\n".join(f"• {error}" for error in errors)
            messagebox.showerror("검증 실패", error_message)
            return False


def validate_env():
    """환경변수 검증 함수"""
    validator = EnvValidator()
    is_valid, errors = validator.validate_all()
    return validator.show_validation_result(is_valid, errors)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    validate_env()

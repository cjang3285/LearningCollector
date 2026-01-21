"""
환경변수 입력 UI 모듈
사용자로부터 환경변수를 입력받아 .env 파일에 저장
"""
import tkinter as tk
from tkinter import filedialog, messagebox
import os
from pathlib import Path


class EnvSetupUI:
    """환경변수 설정 UI"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("LearningCollector - 환경변수 설정")
        self.root.geometry("600x500")

        # 환경변수 저장용 딕셔너리
        self.env_vars = {}

        # UI 요소 저장용
        self.entries = {}

        self._create_widgets()

    def _create_widgets(self):
        """UI 위젯 생성"""
        # 제목
        title_label = tk.Label(
            self.root,
            text="환경변수 설정",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=10)

        # 스크롤 가능한 프레임
        canvas = tk.Canvas(self.root)
        scrollbar = tk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Module 1: 인증 정보
        self._create_section(scrollable_frame, "Module 1: 인증 정보", [
            ("GITHUB_TOKEN", "GitHub Personal Access Token", False),
            ("GEMINI_API_KEY", "Gemini API Key", False)
        ])

        # Module 2: 감시
        self._create_section(scrollable_frame, "Module 2: 감시", [
            ("AI_CHAT_DOWNLOAD_DIR", "AI Chat 다운로드 폴더 경로", True),
            ("LOG_FILE_PATH", "로그 파일 경로 (기본값: ./log/err.log)", False)
        ])

        # Module 3: 필터링 및 환경 설정
        self._create_section(scrollable_frame, "Module 3: 필터링 및 환경 설정", [
            ("GITHUB_USERNAME", "GitHub 사용자명", False),
            ("EDITOR_COMMAND", "에디터 명령어 (기본값: code)", False)
        ])

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 저장 버튼
        save_button = tk.Button(
            self.root,
            text="저장",
            command=self._save_env,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 12, "bold"),
            padx=20,
            pady=10
        )
        save_button.pack(pady=10)

    def _create_section(self, parent, title, fields):
        """섹션 생성"""
        # 섹션 제목
        section_frame = tk.LabelFrame(parent, text=title, font=("Arial", 12, "bold"))
        section_frame.pack(fill="x", padx=10, pady=5)

        for var_name, label_text, is_dir in fields:
            self._create_field(section_frame, var_name, label_text, is_dir)

    def _create_field(self, parent, var_name, label_text, is_dir=False):
        """입력 필드 생성"""
        frame = tk.Frame(parent)
        frame.pack(fill="x", padx=10, pady=5)

        # 레이블
        label = tk.Label(frame, text=label_text, width=30, anchor="w")
        label.pack(side="left")

        # 입력 필드
        entry = tk.Entry(frame, width=40)
        entry.pack(side="left", padx=5)
        self.entries[var_name] = entry

        # 디렉터리 선택 버튼 (필요한 경우)
        if is_dir:
            browse_button = tk.Button(
                frame,
                text="찾아보기",
                command=lambda: self._browse_directory(var_name)
            )
            browse_button.pack(side="left")

    def _browse_directory(self, var_name):
        """디렉터리 선택 대화상자"""
        directory = filedialog.askdirectory()
        if directory:
            self.entries[var_name].delete(0, tk.END)
            self.entries[var_name].insert(0, directory)

    def _save_env(self):
        """환경변수를 .env 파일에 저장"""
        # 입력값 수집
        for var_name, entry in self.entries.items():
            value = entry.get().strip()
            if value:
                self.env_vars[var_name] = value

        # 필수 필드 검증
        required_fields = ["GITHUB_TOKEN", "GEMINI_API_KEY", "AI_CHAT_DOWNLOAD_DIR", "GITHUB_USERNAME"]
        missing_fields = [field for field in required_fields if field not in self.env_vars]

        if missing_fields:
            messagebox.showerror(
                "오류",
                f"다음 필수 필드를 입력해주세요:\n" + "\n".join(missing_fields)
            )
            return

        # 기본값 설정
        if "LOG_FILE_PATH" not in self.env_vars:
            self.env_vars["LOG_FILE_PATH"] = "./log/err.log"
        if "EDITOR_COMMAND" not in self.env_vars:
            self.env_vars["EDITOR_COMMAND"] = "code"

        # .env 파일 작성
        env_path = Path(__file__).parent.parent / ".env"
        try:
            with open(env_path, "w", encoding="utf-8") as f:
                for key, value in self.env_vars.items():
                    f.write(f"{key}={value}\n")

            messagebox.showinfo("성공", ".env 파일이 저장되었습니다.")
            self.root.destroy()
        except Exception as e:
            messagebox.showerror("오류", f".env 파일 저장 중 오류 발생:\n{str(e)}")

    def run(self):
        """UI 실행"""
        self.root.mainloop()
        return self.env_vars


def show_env_setup_ui():
    """환경변수 설정 UI 표시"""
    ui = EnvSetupUI()
    return ui.run()


if __name__ == "__main__":
    show_env_setup_ui()

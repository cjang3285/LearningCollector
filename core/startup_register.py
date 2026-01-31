"""
시작프로그램 등록 모듈
프로그램의 메인 기능이 매일 자정 실행되도록 시작프로그램으로 등록
"""
import os
import sys
import platform
from pathlib import Path


class StartupRegister:
    """시작프로그램 등록 클래스"""

    def __init__(self):
        self.system = platform.system()
        self.script_path = Path(__file__).parent.parent / "main.py"

    def register(self):
        """OS별 시작프로그램 등록"""
        if self.system == "Windows":
            return self._register_windows()
        elif self.system == "Linux":
            return self._register_linux()
        elif self.system == "Darwin":  # macOS
            return self._register_macos()
        else:
            print(f"지원하지 않는 운영체제입니다: {self.system}")
            return False

    def _register_windows(self):
        """Windows 작업 스케줄러에 등록"""
        import subprocess

        task_name = "LearningCollector"
        python_path = sys.executable
        script_path = str(self.script_path.absolute())

        # XML 작업 스케줄러 정의
        task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2024-01-01T00:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Actions>
    <Exec>
      <Command>{python_path}</Command>
      <Arguments>{script_path} --auto</Arguments>
    </Exec>
  </Actions>
</Task>"""

        # XML 파일 임시 저장
        temp_xml_path = Path.home() / "temp_task.xml"
        with open(temp_xml_path, "w", encoding="utf-16") as f:
            f.write(task_xml)

        try:
            # 기존 작업 삭제 (있을 경우)
            subprocess.run(
                ["schtasks", "/delete", "/tn", task_name, "/f"],
                capture_output=True,
                check=False
            )

            # 새 작업 등록
            result = subprocess.run(
                ["schtasks", "/create", "/tn", task_name, "/xml", str(temp_xml_path)],
                capture_output=True,
                text=True,
                check=True
            )

            print(f"Windows 작업 스케줄러에 등록 완료: {task_name}")
            return True

        except subprocess.CalledProcessError as e:
            print(f"Windows 작업 스케줄러 등록 실패: {e.stderr}")
            return False

        finally:
            # 임시 파일 삭제
            if temp_xml_path.exists():
                temp_xml_path.unlink()

    def _register_linux(self):
        """Linux cron에 등록"""
        from crontab import CronTab

        # 실제 프로젝트 경로 (라즈베리파이 기준)
        project_dir = "/home/jcw/LearningCollector_v1.0"
        log_file = f"{project_dir}/log/cron.log"

        # 가상환경 활성화 + 스크립트 실행 명령
        command = f"cd {project_dir} && source venv/bin/activate && python main.py --auto >> {log_file} 2>&1"

        try:
            # 사용자 crontab 가져오기
            cron = CronTab(user=True)

            # 기존 작업 제거
            cron.remove_all(comment="LearningCollector")

            # 새 작업 추가 (매일 자정, auto 모드)
            job = cron.new(
                command=command,
                comment="LearningCollector"
            )
            job.setall("0 0 * * *")  # 매일 자정

            # crontab 저장
            cron.write()

            print("Linux cron에 등록 완료 (매일 자정 실행)")
            print(f"  경로: {project_dir}")
            print(f"  로그: {log_file}")
            return True

        except Exception as e:
            print(f"Linux cron 등록 실패: {str(e)}")
            return False

    def _register_macos(self):
        """macOS launchd에 등록"""
        import plistlib

        python_path = sys.executable
        script_path = str(self.script_path.absolute())

        plist_name = "com.learningcollector.daily"
        plist_path = Path.home() / "Library" / "LaunchAgents" / f"{plist_name}.plist"

        # plist 내용 정의
        plist_content = {
            "Label": plist_name,
            "ProgramArguments": [python_path, script_path, "--auto"],
            "StartCalendarInterval": {
                "Hour": 0,
                "Minute": 0
            },
            "RunAtLoad": False
        }

        try:
            # LaunchAgents 디렉터리 생성
            plist_path.parent.mkdir(parents=True, exist_ok=True)

            # plist 파일 작성
            with open(plist_path, "wb") as f:
                plistlib.dump(plist_content, f)

            # launchctl에 등록
            import subprocess
            subprocess.run(["launchctl", "load", str(plist_path)], check=True)

            print(f"macOS launchd에 등록 완료: {plist_path}")
            return True

        except Exception as e:
            print(f"macOS launchd 등록 실패: {str(e)}")
            return False


def register_startup():
    """시작프로그램 등록 함수"""
    registrar = StartupRegister()
    return registrar.register()


if __name__ == "__main__":
    register_startup()

import os
import sys
import venv
import time
import subprocess
from logger import setup_logging
import logging

setup_logging()


def create_or_get_venv(venv_name):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    venv_path = os.path.join(current_dir, venv_name)

    if not os.path.exists(venv_path):
        logging.info(f"正在创建虚拟环境: {venv_name}")
        venv.create(venv_path, with_pip=True)
        return venv_path, True
    return venv_path, False


def get_venv_python(venv_path):
    if sys.platform == "win32":
        return os.path.join(venv_path, "Scripts", "python.exe")
    else:
        return os.path.join(venv_path, "bin", "python")


def install_requirements(venv_python):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    requirements_path = os.path.join(current_dir, "requirements.txt")
    if os.path.exists(requirements_path):
        logging.info("正在安装依赖包...")
        subprocess.check_call(
            [venv_python, "-m", "pip", "install", "-r", requirements_path]
        )
    else:
        logging.warning("未找到requirements.txt文件。跳过包安装。")


def main():
    logging.info("开始执行main函数")
    try:
        venv_name = "plantuml_viewer_env"
        venv_path, is_new_venv = create_or_get_venv(venv_name)
        venv_python = get_venv_python(venv_path)

        if is_new_venv:
            install_requirements(venv_python)
        else:
            logging.info("使用现有虚拟环境，跳过依赖安装")

        current_dir = os.path.dirname(os.path.abspath(__file__))
        central_app_path = os.path.join(current_dir, "central_app.py")

        logging.info(f"准备运行central_app.py，路径：{central_app_path}")

        env = os.environ.copy()
        if sys.platform == "win32":
            site_packages = os.path.join(venv_path, "Lib", "site-packages")
        else:
            site_packages = os.path.join(
                venv_path,
                "lib",
                f"python{sys.version_info.major}.{sys.version_info.minor}",
                "site-packages",
            )
        env["PYTHONPATH"] = f"{site_packages}:{env.get('PYTHONPATH', '')}"

        result = subprocess.run(
            [venv_python, central_app_path],
            env=env,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            logging.error(f"central_app.py 执行失败，返回码：{result.returncode}")
            logging.error(f"错误输出：{result.stderr}")
        else:
            logging.info("central_app.py 执行成功")

        logging.info(f"central_app.py 输出：\n{result.stdout}")

    except Exception as e:
        logging.exception(f"main函数中发生异常: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

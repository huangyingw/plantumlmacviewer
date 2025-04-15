import os
import sys
import venv
import time
import subprocess
from logger import setup_logging
import logging
import platform

setup_logging()


def get_python_executable():
    """获取合适的Python可执行文件路径"""
    # 首先尝试使用系统Python
    system_python = "/usr/bin/python3"
    if os.path.exists(system_python):
        return system_python

    # 如果系统Python不存在，尝试使用当前运行的Python
    return sys.executable


def check_venv_health(venv_path):
    """检查虚拟环境是否健康"""
    try:
        python_path = get_venv_python(venv_path)
        if not os.path.exists(python_path):
            return False, "Python解释器不存在"

        # 使用pip list检查包是否已安装
        pip_path = os.path.join(os.path.dirname(python_path), "pip")
        result = subprocess.run(
            [pip_path, "list"],
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            return False, f"无法获取已安装的包列表: {result.stderr}"
            
        installed_packages = result.stdout.lower()
        required_packages = ['pyqt5', 'watchdog', 'pyobjc']
        
        for package in required_packages:
            if package not in installed_packages:
                return False, f"包 {package} 未安装"

        return True, "虚拟环境正常"
    except Exception as e:
        return False, f"检查失败: {str(e)}"


def create_or_get_venv(venv_name):
    """创建或获取虚拟环境，只在必要时重新创建"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    venv_path = os.path.join(current_dir, venv_name)

    if os.path.exists(venv_path):
        # 检查现有环境是否健康
        is_healthy, message = check_venv_health(venv_path)
        if is_healthy:
            logging.info("使用现有虚拟环境")
            return venv_path, False
        else:
            logging.warning(f"虚拟环境不健康: {message}，将重新创建")
            # 在删除之前确保没有进程在使用虚拟环境
            if platform.system() == "Windows":
                os.system(f'taskkill /F /IM python.exe')
            else:
                os.system('pkill -f "python3.*plantuml_viewer_env"')
            import shutil
            shutil.rmtree(venv_path)

    logging.info(f"正在创建虚拟环境: {venv_name}")
    try:
        python_executable = get_python_executable()
        subprocess.check_call([python_executable, "-m", "venv", venv_path])
        return venv_path, True
    except subprocess.CalledProcessError as e:
        logging.error(f"创建虚拟环境失败: {str(e)}")
        raise


def get_venv_python(venv_path):
    if platform.system() == "Windows":
        return os.path.join(venv_path, "Scripts", "python.exe")
    else:
        return os.path.join(venv_path, "bin", "python3")


def install_requirements(venv_python):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    requirements_path = os.path.join(current_dir, "requirements.txt")
    if os.path.exists(requirements_path):
        logging.info("正在安装依赖包...")
        try:
            # 先升级pip
            subprocess.check_call(
                [venv_python, "-m", "pip", "install", "--upgrade", "pip"]
            )
            # 安装依赖
            subprocess.check_call(
                [venv_python, "-m", "pip", "install", "-r", requirements_path]
            )
        except subprocess.CalledProcessError as e:
            logging.error(f"安装依赖失败: {str(e)}")
            raise
    else:
        logging.warning("未找到requirements.txt文件。跳过包安装。")


def main():
    logging.info("开始执行main函数")
    try:
        venv_name = "plantuml_viewer_env"
        current_dir = os.path.dirname(os.path.abspath(__file__))

        venv_path, is_new_venv = create_or_get_venv(venv_name)
        venv_python = get_venv_python(venv_path)

        if is_new_venv:
            install_requirements(venv_python)

        central_app_path = os.path.join(current_dir, "central_app.py")
        logging.info(f"准备运行central_app.py，路径：{central_app_path}")

        env = os.environ.copy()
        if platform.system() == "Windows":
            site_packages = os.path.join(venv_path, "Lib", "site-packages")
        else:
            python_version = (
                f"{sys.version_info.major}.{sys.version_info.minor}"
            )
            site_packages = os.path.join(
                venv_path, "lib", f"python{python_version}", "site-packages"
            )

        env["PYTHONPATH"] = f"{site_packages}:{env.get('PYTHONPATH', '')}"

        process = subprocess.Popen(
            [venv_python, central_app_path],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )

        time.sleep(2)
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            logging.error(f"central_app.py 启动失败")
            logging.error(f"标准输出：{stdout}")
            logging.error(f"错误输出：{stderr}")
            return 1
        else:
            logging.info("central_app.py 成功启动")
            return 0

    except Exception as e:
        logging.exception(f"main函数中发生异常: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

import os
import subprocess
from urllib.parse import urlparse

from memwin import XProcess
from PySide2.QtCore import  QThread, Signal
from PySide2.QtWidgets import QDialog, QMessageBox

from .file_download_module import download_file
from .utils import calculate_file_md5, file_remove, compare_versions
from . import update_image_rc
from .wnd_update import Ui_Form


BACKUP_CDN_BASE_URL = 'http://ytdownload.soult.cn'
OFFICIAL_WEBSITE_URL = 'https://yt.soult.cn'
DOWNLOAD_CONNECT_TIMEOUT_SECONDS = 3
DOWNLOAD_READ_TIMEOUT_SECONDS = 5


def build_backup_download_url(primary_url: str) -> str:
    if not primary_url:
        return ''
    try:
        parsed = urlparse(primary_url)
        if not parsed.path:
            return ''
        return f"{BACKUP_CDN_BASE_URL.rstrip('/')}{parsed.path}"
    except Exception as e:
        print(f"构建备用下载链接失败: {e}")
        return ''


class WndUpdateSoftware(QDialog, Ui_Form):
    sig_update_finish = Signal()  # 更新完成重启
    def __init__(self, parent=None, client_version="v0.1.0"):
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowTitle('软件更新')
        self.resize(600, 360)
        
        self.btn_azgx.setFixedSize(80, 25)
        self.btn_tgbb.setFixedSize(80, 25)
        self.btn_ok.setFixedSize(80, 25)
        
        # 绑定按钮事件
        self.btn_azgx.clicked.connect(self.install_update)
        self.btn_tgbb.clicked.connect(self.close)
        self.btn_ok.clicked.connect(self.close)

        # 隐藏更新进度条和状态编辑框
        self.progressBar.hide()
        self.progressBar.setValue(0)
        self.progressBar.setRange(0, 100)
        self.label_zt.hide()
        self.btn_ok.hide()
        self.btn_azgx.setEnabled(False)
        self.btn_tgbb.setEnabled(False)
        # textEdit 禁止编辑
        self.textEdit.setReadOnly(True)
        self.textEdit.setText("正在检查更新...")

        self.client_version = client_version
        latest_version = "查询中..."
        self.label_2.setText(latest_version)
        self.label_bbh.setText(f'最新版本:{latest_version}    当前版本: {self.client_version}')

    def on_resp_update(self, data: dict):
        latest_version = data.get('latest_version', '')
        self.label_bbh.setText(f'最新版本:{latest_version}    当前版本: {self.client_version}')
        self.textEdit.setPlainText(data.get('update_info'))
        self.patcher_download_url = data.get('patcher_download_url')
        self.installer_download_url = data.get('installer_download_url')
        self.md5 = data.get('md5')
        force_update = data.get('force_update', False)
        print(f'force_update:{force_update}')

        if compare_versions(self.client_version, latest_version) >= 0 or latest_version == '':
            self.label_2.setText("你使用的是最新版本")
            self.btn_azgx.hide()
            self.btn_tgbb.hide()
            self.btn_ok.show()
            return

        self.btn_azgx.show()
        self.btn_tgbb.show()
        self.btn_ok.hide()
        self.btn_azgx.setEnabled(True)
        self.btn_tgbb.setEnabled(True)
        self.label_2.setText("发现新版本")
        if force_update:
            self.show()

    def install_update(self):
        self.progressBar.show()
        self.label_zt.show()
        self.label_zt.setText('更新中...')
        self.btn_azgx.setEnabled(False)
        self.btn_tgbb.setEnabled(False)

        fallback_download_url = build_backup_download_url(self.installer_download_url)

        self.thd_download_file = ThdDownloadFile(
            download_urls=[u for u in [self.installer_download_url, fallback_download_url] if u],
            wnd=self,
            edt=self.label_zt,
            process_bar=self.progressBar,
        )
        self.thd_download_file.sig_download_finish.connect(self.on_download_file_finish)
        self.thd_download_file.start()

    def on_download_file_finish(self, download_result, save_path):
        installer_path = save_path
        if not download_result:
            self.label_zt.setText(
                f'<html><head/><body><p><a href="{OFFICIAL_WEBSITE_URL}"><span style=" text-decoration: underline; color:#0000ff;">下载更新失败, 请到官网下载(直接覆盖安装, 不需要卸载)</span></a></p></body></html>')
            file_remove(installer_path)
            return
        
        # 使用批处理脚本启动安装包，避免被杀软拦截
        bat_content = f'''@echo off
timeout /t 3 /nobreak >nul
start "" "{installer_path}"
del "%~f0"
'''
        bat_path = os.path.join(os.environ['TEMP'], 'ql_update.bat')
        try:
            with open(bat_path, 'w', encoding='gbk') as f:
                f.write(bat_content)
            # 后台启动批处理脚本，不等待
            subprocess.Popen(['cmd', '/c', bat_path],
                           creationflags=subprocess.CREATE_NO_WINDOW)
            self.label_zt.setText('更新包准备完成，软件即将关闭并自动安装...')
        except Exception as e:
            print(f"创建批处理脚本失败: {e}")
            # 降级方案：直接启动安装包
            XProcess.create_process(installer_path)
        
        self.sig_update_finish.emit()
        


class ThdDownloadFile(QThread):
    # 下载文件线程
    sig_refresh_process_bar = Signal(int, str)  # 进度 提示文本
    sig_download_finish = Signal(bool, str)

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.wnd = kwargs.get('wnd')
        self.download_urls = kwargs.get('download_urls') or []
        self.edt = kwargs.get('edt')
        self.process_bar = kwargs.get('process_bar')
        self.sig_refresh_process_bar.connect(self.refresh_ui)
        self.save_path = os.path.join('C:/TEMP', 'qlinstaller.exe')

    def run(self):
        self.edt.setText('开始下载')
        # 如果之前的还在, 删除掉
        file_remove(self.save_path)
        if not self.download_urls:
            print("请传入下载地址")
            self.sig_download_finish.emit(False, self.save_path)
            return

        def callback(progress_percent, already_download_size, file_size, download_rate, time_left):
            info = f"文件大小 {file_size}MB, 速度 {download_rate}MB/s, 剩余时间 {time_left}秒"
            self.sig_refresh_process_bar.emit(progress_percent, info)

        self.download_result = False
        for idx, url in enumerate(self.download_urls):
            if idx == 0:
                self.edt.setText('使用主线路下载中...')
            else:
                self.edt.setText('主线路失败，切换备用线路下载中...')

            try:
                download_file(
                    url,
                    self.save_path,
                    callback,
                    timeout=(DOWNLOAD_CONNECT_TIMEOUT_SECONDS, DOWNLOAD_READ_TIMEOUT_SECONDS),
                )
                self.download_result = True
                print(f"下载成功: {url}")
                break
            except Exception as e:
                print(f"下载文件异常({url}): {e}")
                file_remove(self.save_path)

        print("下载结果:", self.download_result)
        print("保存地址:", self.save_path)
        if self.download_result:
            self.edt.setText('安装包下载完成')
        self.sig_download_finish.emit(self.download_result, self.save_path)

    def refresh_ui(self, progress_percent, info):
        if self.edt:
            self.edt.setText(str(info))
        if self.process_bar:
            self.process_bar.setValue(int(progress_percent))

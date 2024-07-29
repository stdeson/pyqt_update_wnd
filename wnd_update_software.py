import os

from memwin import XProcess
from PySide2.QtCore import  QThread, Signal
from PySide2.QtWidgets import QDialog, QMessageBox

from .file_download_module import download_file
from .utils import calculate_file_md5, file_remove
from . import update_image_rc
from .ui_winUpdate import Ui_Form


class WndUpdateSoftware(QDialog, Ui_Form):
    sig_update_finish_restart = Signal()  # 更新完成重启
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
        self.label_bbh.setText(f'最新版本:{latest_version} 当前版本: {self.client_version}')

    def on_resp_update(self, data: dict):
        latest_version = data.get('latest_version', '')
        self.label_bbh.setText(f'最新版本:{latest_version} 当前版本: {self.client_version}')
        self.textEdit.setPlainText(data.get('update_info'))
        self.patcher_download_url = data.get('patcher_download_url')
        self.installer_download_url = data.get('installer_download_url')
        self.md5 = data.get('md5')

        if latest_version == self.client_version or latest_version == '':
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
        self.show()

    def install_update(self):
        self.progressBar.show()
        self.label_zt.show()
        self.label_zt.setText('更新中...')
        self.btn_azgx.setEnabled(False)
        self.btn_tgbb.setEnabled(False)

        self.thd_download_file = ThdDownloadFile(
            download_url=self.installer_download_url,
            wnd=self,
            edt=self.label_zt,
            process_bar=self.progressBar,
        )
        self.thd_download_file.sig_download_finish.connect(self.on_download_file_finish)
        self.thd_download_file.start()

    def on_download_file_finish(self, download_result, save_path):
        installer_path = save_path
        if not download_result:
            self.label_zt.setText("下载更新失败")
            file_remove(installer_path)
            return
        # # 校验md5
        # download_md5 = calculate_file_md5(installer_path)
        # print(f"计算出的md5: {download_md5}, 实际应该的md5: {self.md5}")
        # if download_md5 != self.md5:
        #     self.label_zt.setText("安装包下载不完整, 请重新下载")
        #     file_remove(installer_path)
        #     return
        # 打开安装包
        XProcess.create_process(installer_path)
        QMessageBox.information(self, "提示", "更新准备就绪, 请关闭软件后直接安装")


class ThdDownloadFile(QThread):
    # 下载文件线程
    sig_refresh_process_bar = Signal(int, str)  # 进度 提示文本
    sig_download_finish = Signal(bool, str)

    def __init__(self, *args, **kwargs):
        super().__init__()
        self.wnd = kwargs.get('wnd')
        self.download_url = kwargs.get('download_url')
        self.edt = kwargs.get('edt')
        self.process_bar = kwargs.get('process_bar')
        self.sig_refresh_process_bar.connect(self.refresh_ui)
        self.save_path = os.path.join(os.environ['USERPROFILE'], 'Downloads', 'qlinstaller.exe')

    def run(self):
        self.edt.setText('开始下载')
        # 如果之前的还在, 删除掉
        file_remove(self.save_path)
        if self.download_url == None:
            print("请传入下载地址")
            return

        def callback(progress_percent, already_download_size, file_size, download_rate, time_left):
            info = f"文件大小 {file_size}MB, 速度 {download_rate}MB/s, 剩余时间 {time_left}秒"
            self.sig_refresh_process_bar.emit(progress_percent, info)

        try:
            download_file(self.download_url, self.save_path, callback)
            self.download_result = True
        except Exception as e:
            print(f"下载文件异常: {e}")
            self.download_result = False

        print("下载结果:", self.download_result)
        print("保存地址:", self.save_path)
        self.edt.setText(f"补丁包下载完成")
        self.sig_download_finish.emit(self.download_result, self.save_path)

    def refresh_ui(self, progress_percent, info):
        if self.edt:
            self.edt.setText(str(info))
        if self.process_bar:
            self.process_bar.setValue(int(progress_percent))
import ctypes
from ctypes import wintypes
import hashlib
import os


def run_exe(exe_name, is_activate=False):
    start_info = ctypes.create_string_buffer(68)
    if not is_activate:  # 新创建的进程不会自动激活, 抢占焦点
        start_info.dwFlags = 0x00000080  # STARTF_FORCEOFFFEEDBACK
    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("hProcess", wintypes.HANDLE),
            ("hThread", wintypes.HANDLE),
            ("dwProcessId", wintypes.DWORD),
            ("dwThreadId", wintypes.DWORD)
        ]
    process_info = PROCESS_INFORMATION()
    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32
    if not kernel32.CreateProcessW(None, ctypes.c_wchar_p(exe_name), None, None, False, 0, None, None, ctypes.byref(start_info), ctypes.byref(process_info)):
        return False
    user32.WaitForInputIdle(process_info.hProcess, 0xFFFFFFFF)
    kernel32.CloseHandle(process_info.hThread)
    kernel32.CloseHandle(process_info.hProcess)
    return True
    
def calculate_file_md5(file_path):
    with open(file_path, "rb") as f:
        content = f.read()
        md5 = hashlib.md5(content).hexdigest()
        return md5
    
def path_exist(path: str):
    if os.path.exists(path):
        return True
    return False
    
def file_remove(path: str):
    if path_exist(path):
        os.remove(path)
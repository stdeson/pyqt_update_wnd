import ctypes
from ctypes import wintypes
import hashlib
import os
import shutil


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
        
def copy_tree_safe(target_dir, source_dir):
    try:
        print("正在复制目录 '%s' 到 '%s'..." % (source_dir, target_dir))
        if os.path.exists(target_dir):
            print("目标目录 '%s' 已存在，正在删除..." % target_dir)
            shutil.rmtree(target_dir)
        shutil.copytree(source_dir, target_dir)
        print("目录 '%s' 复制完成" % target_dir)
        return True
    except Exception as e:
        print("shutil.copytree: ", e)
        return False

def remove_dir_safe(path):  
    """  
    安全删除目录，如果目录不存在则不会报错。  
    :param path: 要删除的目录路径  
    """  
    if os.path.exists(path) and os.path.isdir(path):  
        try:  
            shutil.rmtree(path)  
            print(f"目录 {path} 已成功删除。")  
        except Exception as e:  
            print(f"删除目录 {path} 时出错：{e}")  
    else:  
        print(f"目录 {path} 不存在。")  
        

def compare_versions(v1: str, v2: str) -> int:
    """
    比较版本号：
      返回 1 ：v1 > v2
      返回 0 ：v1 == v2
      返回 -1：v1 < v2
    支持前缀 'v' 或 'V'，不足位补 0 比较
    """
    def norm(v):
        # 去掉前缀并切分
        v = v.lstrip('vV')
        parts = [int(x) for x in v.split('.')]
        return parts

    p1 = norm(v1)
    p2 = norm(v2)
    # 对齐长度，不足补0
    n = max(len(p1), len(p2))
    p1 += [0] * (n - len(p1))
    p2 += [0] * (n - len(p2))

    for a, b in zip(p1, p2):
        if a > b:
            return 1
        if a < b:
            return -1
    return 0

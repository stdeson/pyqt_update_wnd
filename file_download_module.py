import requests
import time

def download_file(url, save_path, callback_func=None, timeout=(10, 15)):
    start_time = time.time()
    print('开始下载:', url)
    r = requests.get(url, stream=True, verify=False, proxies={  # 忽略系统代理
        'http': None,
        'https': None
    }, timeout=timeout)
    r.raise_for_status()
    with open(save_path, 'wb') as f:
        total_length_header = r.headers.get('content-length')
        total_length = int(total_length_header) if total_length_header else 0
        for chunk in r.iter_content(chunk_size=10 * 1024):
            if chunk:
                f.write(chunk)
                f.flush()
                if callback_func:
                    progress_percent = int(f.tell() * 100 / total_length) if total_length > 0 else 0
                    downloaded_size = f.tell() / 1024 / 1024
                    file_size_mb = total_length / 1024 / 1024 if total_length > 0 else 0
                    elapsed = max(time.time() - start_time, 0.001)
                    download_rate_mb = downloaded_size / elapsed
                    # 获取剩余时间取秒
                    if total_length > 0 and download_rate_mb > 0:
                        left_seconds = int((file_size_mb - downloaded_size) / download_rate_mb)
                    else:
                        left_seconds = 0
                    # 所有数据保留两位小数
                    download_rate_mb = round(download_rate_mb, 2)
                    file_size_mb = round(file_size_mb, 2)
                    downloaded_size = round(downloaded_size, 2)
                    progress_percent = round(progress_percent, 2)
                    callback_func(progress_percent, downloaded_size, file_size_mb, download_rate_mb, left_seconds)
    return True

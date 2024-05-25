import requests
import time

def download_file(url, save_path, callback_func=None):
    if callback_func:
        start_time = time.time()
    print('开始下载:', url)
    r = requests.get(url, stream=True, verify=False)
    with open(save_path, 'wb') as f:
        total_length = int(r.headers.get('content-length'))
        for chunk in r.iter_content(chunk_size=10 * 1024):
            if chunk:
                f.write(chunk)
                f.flush()
                if callback_func:
                    progress_percent = int(f.tell() * 100 / total_length)
                    downloaded_size = f.tell() / 1024 / 1024
                    file_size_mb = total_length / 1024 / 1024
                    download_rate_mb = downloaded_size / (time.time() - start_time)
                    # 获取剩余时间取秒
                    left_seconds = int((file_size_mb - downloaded_size) / download_rate_mb)
                    # 所有数据保留两位小数
                    download_rate_mb = round(download_rate_mb, 2)
                    file_size_mb = round(file_size_mb, 2)
                    downloaded_size = round(downloaded_size, 2)
                    progress_percent = round(progress_percent, 2)
                    callback_func(progress_percent, downloaded_size, file_size_mb, download_rate_mb, left_seconds)
    return True

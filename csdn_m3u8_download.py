import requests
from multiprocessing import Pool
import re
import os
from tqdm import tqdm
from Crypto.Cipher import AES

# 创建临时文件夹
dirs = 'ts_list_need_to_merge/'
os.makedirs(dirs, exist_ok=True)

headers = {
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'Connection': 'keep-alive',
    'Origin': 'http://www.kpd510.me',
    'Referer': 'http://www.kpd510.me/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'cross-site',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.69',
    'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Microsoft Edge";v="116"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}


def parse_m3u8_text(m3u8_text):
    m3u8_text = m3u8_text.split()
    encode_info = [line for line in m3u8_text if line.startswith('#EXT-X-KEY:')][0]
    pattern = r"#EXT-X-KEY:METHOD=(.*),URI=\"(.*)\""

    ## 获得加密method 和 key.key的url
    match = re.search(pattern, encode_info)
    if match:
        method = match.group(1)
        key_url = match.group(2)
    else:
        raise '解析失败'

    ## 获得ts文件url
    ts_list = [line for line in m3u8_text if line.endswith('ts')]
    return method, key_url, ts_list


def decrypt_content_and_save_file(filename, content, decrypter):
    with open(filename, mode='wb') as f:
        f.write(decrypter.decrypt(content))


def merge_ts_to_mp4(filename, ts_file_list):
    with open(filename, mode='ab') as f1:
        for ts_file in ts_file_list:
            with open(ts_file, mode='rb') as f2:
                f1.write(f2.read())
    print(filename, '完成！')


def process_one_url(ts_url, key):
    decrypter = AES.new(key, AES.MODE_CBC)
    filename = dirs + os.path.split(ts_url)[-1]
    content = requests.get(ts_url, headers=headers).content
    decrypt_content_and_save_file(filename, content, decrypter)
    return filename


def download_method_1(ts_list, key):
    # 普通次序一个一个下载，耗时11分钟
    ts_file_list = []
    for ts_url in tqdm(ts_list):
        filename = process_one_url(ts_url=ts_url, key=key)
        ts_file_list.append(filename)
    return ts_file_list


def download_method_2(ts_list, key, processes_nums=2):
    # 多进程下载， 耗时1分钟
    class CallBack:
        def __init__(self, nums) -> None:
            self.pbar = tqdm(total=nums)
            self.filenames = []

        def callback(self, filename):
            self.pbar.update(1)
            self.filenames.append(filename)

    callback = CallBack(len(ts_list))
    pool = Pool(processes=processes_nums)
    for ts_url in ts_list:
        pool.apply_async(process_one_url, (ts_url, key), error_callback=print, callback=callback.callback)
    pool.close()
    pool.join()
    callback.pbar.close()
    return [dirs + os.path.split(ts_url)[-1] for ts_url in ts_list]


if __name__ == "__main__":
    m3u8_url = 'https://play.bo262626.com/20231108/xV1bY9Cn/700kb/hls/index.m3u8'
    response = requests.get(m3u8_url, headers=headers)
    m3u8 = response.text
    method, key_url, ts_list = parse_m3u8_text(m3u8)

    key_url = 'https://play.bo262626.com' + key_url
    ts_list = ['https://play.bo262626.com' + item for item in ts_list]

    key = requests.get(key_url, headers=headers).content
    ts_file_list = download_method_2(ts_list, key=key, processes_nums=10)

    merge_ts_to_mp4('test.mp4', ts_file_list)

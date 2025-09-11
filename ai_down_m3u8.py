# python
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
    """
    返回: method, key_uri, ts_list, media_sequence (int), iv_hex_or_None
    """
    lines = [line.strip() for line in m3u8_text.splitlines() if line.strip() != '']
    # 媒体序号（可选）
    media_seq = 0
    for line in lines:
        if line.startswith('#EXT-X-MEDIA-SEQUENCE'):
            try:
                media_seq = int(line.split(':', 1)[1])
            except Exception:
                media_seq = 0
            break

    # 找到 KEY 行
    key_lines = [line for line in lines if line.startswith('#EXT-X-KEY:')]
    if not key_lines:
        raise Exception('解析失败: 找不到 #EXT-X-KEY')
    key_line = key_lines[0][len('#EXT-X-KEY:'):]
    # 解析属性，形如 METHOD=AES-128,URI="...",IV=0x...
    attrs = {}
    for part in re.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)', key_line):
        if '=' in part:
            k, v = part.split('=', 1)
            attrs[k.strip()] = v.strip().strip('"')
    method = attrs.get('METHOD')
    key_uri = attrs.get('URI')
    iv = attrs.get('IV')  # 例如 0x1234...
    # 收集 ts 列表（不包含注释）
    ts_list = [line for line in lines if not line.startswith('#') and line.endswith('.ts')]
    if not method or not key_uri or not ts_list:
        raise Exception('解析失败: 缺少 METHOD/URI/TS 列表')
    return method, key_uri, ts_list, media_seq, iv


def pkcs7_unpad(data: bytes) -> bytes:
    if not data:
        return data
    pad_len = data[-1]
    if 1 <= pad_len <= AES.block_size and data[-pad_len:] == bytes([pad_len]) * pad_len:
        return data[:-pad_len]
    return data


def decrypt_content_and_save_file(filename, content, key, iv):
    try:
        decrypter = AES.new(key, AES.MODE_CBC, iv=iv)
    except Exception as e:
        raise
    # content 长度应该是 16 的倍数，若不是尝试不报错直接解密（依赖库）
    decrypted = decrypter.decrypt(content)
    # 去 PKCS7 填充（如果有）
    decrypted = pkcs7_unpad(decrypted)
    with open(filename, mode='wb') as f:
        f.write(decrypted)


def merge_ts_to_mp4(filename, ts_file_list):
    with open(filename, mode='ab') as f1:
        for ts_file in ts_file_list:
            with open(ts_file, mode='rb') as f2:
                f1.write(f2.read())
    print(filename, '完成！')


def process_one_url(ts_url, key, iv):
    """
    下载并解密单个 ts，返回保存的文件名
    iv: bytes length 16
    """
    filename = dirs + os.path.split(ts_url)[-1]
    try:
        resp = requests.get(ts_url, headers=headers, timeout=20)
        resp.raise_for_status()
        content = resp.content
        decrypt_content_and_save_file(filename, content, key, iv)
    except Exception as e:
        # 若失败，删除可能的残留文件
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except Exception:
                pass
        print('下载或解密失败:', ts_url, e)
        return None
    return filename


def download_method_1(ts_list, key, media_sequence=0):
    ts_file_list = []
    for idx, ts_url in enumerate(tqdm(ts_list)):
        seq = media_sequence + idx
        iv = seq.to_bytes(16, 'big')
        filename = process_one_url(ts_url=ts_url, key=key, iv=iv)
        ts_file_list.append(filename)
    return ts_file_list


def download_method_2(ts_list, key, media_sequence=0, processes_nums=2):
    class CallBack:
        def __init__(self, nums) -> None:
            self.pbar = tqdm(total=nums)
            self.filenames = []

        def callback(self, filename):
            self.pbar.update(1)
            if filename:
                self.filenames.append(filename)

    callback = CallBack(len(ts_list))
    pool = Pool(processes=processes_nums)
    for idx, ts_url in enumerate(ts_list):
        seq = media_sequence + idx
        iv = seq.to_bytes(16, 'big')
        pool.apply_async(process_one_url, (ts_url, key, iv), error_callback=print, callback=callback.callback)
    pool.close()
    pool.join()
    callback.pbar.close()
    # 保持原始顺序返回文件名（若某些任务失败返回 None）
    return [dirs + os.path.split(ts_url)[-1] for ts_url in ts_list]


if __name__ == "__main__":
    m3u8_url = 'https://play.bo262626.com/20231108/xV1bY9Cn/700kb/hls/index.m3u8'
    response = requests.get(m3u8_url, headers=headers)
    response.raise_for_status()
    m3u8 = response.text
    method, key_url, ts_list, media_seq, iv_hex = parse_m3u8_text(m3u8)

    # 处理 key_url 和 ts_list 的相对路径（根据实际 m3u8 调整）
    if key_url.startswith('/'):
        base = re.match(r'^(https?://[^/]+)', m3u8_url)
        if base:
            key_url = base.group(1) + key_url
    if not key_url.startswith('http'):
        # 尝试与 m3u8 同域拼接
        base = re.match(r'^(https?://.*/)', m3u8_url)
        if base:
            key_url = base.group(1) + key_url

    ts_list_full = []
    for item in ts_list:
        if item.startswith('http'):
            ts_list_full.append(item)
        elif item.startswith('/'):
            base = re.match(r'^(https?://[^/]+)', m3u8_url)
            ts_list_full.append((base.group(1) + item) if base else item)
        else:
            base = re.match(r'^(https?://.*/)', m3u8_url)
            ts_list_full.append((base.group(1) + item) if base else item)

    key_resp = requests.get(key_url, headers=headers)
    key_resp.raise_for_status()
    key = key_resp.content
    if isinstance(iv_hex, str) and iv_hex.startswith('0x'):
        iv = bytes.fromhex(iv_hex[2:])
        if len(iv) < 16:
            iv = (b'\x00' * (16 - len(iv))) + iv
    else:
        iv = None  # 不直接使用此 iv，改用每段序号生成 iv

    # 使用多进程下载并解密，每段用序号生成 IV（若 m3u8 提供了 IV，也可改为使用固定 iv）
    ts_file_list = download_method_2(ts_list_full, key=key, media_sequence=media_seq, processes_nums=10)

    merge_ts_to_mp4('test.mp4', ts_file_list)

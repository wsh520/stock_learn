import re
import os
import requests
from pathlib import Path
import shutil
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# 使用 Selenium 自动获取 B 站 cookie
def get_bilibili_cookie():
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # 无头模式
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')

    driver = webdriver.Chrome(options=chrome_options)
    driver.get('https://www.bilibili.com/')

    # 等待页面加载完成，可根据网络情况适当增加时间
    driver.implicitly_wait(5)

    cookies = driver.get_cookies()
    driver.quit()

    # 拼接为 requests 可用的 cookie 字符串
    cookie_str = '; '.join([f"{c['name']}={c['value']}" for c in cookies])
    return cookie_str

# 构建请求头
def get_headers():
    cookie = get_bilibili_cookie()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cookie": cookie,
        "Referer": "https://www.bilibili.com/"
    }
    return headers

# 解析 BV 号
def extract_bvid(url: str):
    match = re.search(r"BV[\w]+", url)
    if match:
        return match.group(0)
    raise ValueError("未能解析到 BVID，请确认输入的是具体视频地址")

# 获取视频播放信息
def get_play_info(bvid: str, headers):
    api = f"https://api.bilibili.com/x/player/pagelist?bvid={bvid}&jsonp=jsonp"
    resp = requests.get(api, headers=headers)
    data = resp.json()
    if data["code"] != 0:
        raise Exception(f"接口请求失败: {data}")
    return data["data"]

# 获取视频下载地址
def get_download_url(bvid: str, cid: int, headers):
    api = f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn=80&fnval=16"
    resp = requests.get(api, headers=headers).json()
    if resp["code"] != 0:
        raise Exception(f"播放地址请求失败: {resp}")

    try:
        video_url = resp["data"]["dash"]["video"][0]["baseUrl"]
        audio_url = resp["data"]["dash"]["audio"][0]["baseUrl"]
        return video_url, audio_url
    except KeyError:
        durl = resp["data"]["durl"]
        return durl[0]["url"], None

# 下载文件
def download_file(url: str, filename: str, headers):
    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        with open(filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk:
                    f.write(chunk)
    print(f"下载完成: {filename}")

# 合并音视频
def merge_av(video_file: str, audio_file: str, output_file: str):
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        raise EnvironmentError("未检测到 ffmpeg，请先安装并添加到系统 PATH")
    cmd = [ffmpeg_path, "-y", "-i", video_file, "-i", audio_file, "-c:v", "copy", "-c:a", "aac", output_file]
    subprocess.run(cmd, check=True)

# 主函数
def bilibili_downloader(url: str):
    headers = get_headers()
    bvid = extract_bvid(url)
    print(f"解析到视频 BV 号: {bvid}")
    pages = get_play_info(bvid, headers)
    print(f"该视频共有 {len(pages)} 个分P：")

    output_dir = Path(bvid)
    output_dir.mkdir(exist_ok=True)

    for page in pages:
        cid = page["cid"]
        part_title = page["part"]
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', part_title)
        print(f"正在下载分P: {part_title} (CID={cid})")

        video_url, audio_url = get_download_url(bvid, cid, headers)
        video_file = output_dir / f"{safe_title}_video.mp4"

        if audio_url:
            audio_file = output_dir / f"{safe_title}_audio.mp4"
            output_file = output_dir / f"{safe_title}.mp4"

            download_file(video_url, str(video_file), headers)
            download_file(audio_url, str(audio_file), headers)
            merge_av(str(video_file), str(audio_file), str(output_file))

            os.remove(video_file)
            os.remove(audio_file)
        else:
            download_file(video_url, output_dir / f"{safe_title}.mp4", headers)

if __name__ == "__main__":
    url = input("请输入B站视频网址: ").strip()
    bilibili_downloader(url)

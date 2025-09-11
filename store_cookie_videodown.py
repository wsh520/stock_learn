import re
import os
import requests
from pathlib import Path
import shutil
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import sys
import json
import time

# Cookie 缓存文件名和有效期
COOKIE_FILE = "bilibili_cookie.json"
COOKIE_EXPIRY_HOURS = 8


# 检查依赖
def check_dependencies():
    try:
        import selenium
        import requests
        import tqdm
    except ImportError as e:
        print(f"缺少必要的Python库：{e.name}。请安装：pip install -r requirements.txt")
        sys.exit(1)

    if shutil.which("ffmpeg") is None:
        print("未检测到 FFmpeg，请先安装并将其添加到系统 PATH 中。")
        sys.exit(1)


def get_bilibili_cookie_via_selenium():
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get('https://www.bilibili.com/')
        driver.implicitly_wait(5)
        cookies = driver.get_cookies()
        driver.quit()
        cookie_str = '; '.join([f"{c['name']}={c['value']}" for c in cookies])
        return cookie_str
    except Exception as e:
        print(f"使用 Selenium 获取 Cookie 失败，请确保已安装 ChromeDriver 并与 Chrome 浏览器版本匹配。错误信息: {e}")
        sys.exit(1)


def get_bilibili_cookie():
    if os.path.exists(COOKIE_FILE):
        try:
            with open(COOKIE_FILE, 'r') as f:
                data = json.load(f)
                creation_time = data.get("timestamp", 0)
                cookie = data.get("cookie", "")

            # 检查 Cookie 是否在有效期内
            if time.time() - creation_time < COOKIE_EXPIRY_HOURS * 3600:
                print("使用本地缓存的有效 Cookie。")
                return cookie
            else:
                print("本地 Cookie 已过期，正在重新获取...")
        except (IOError, json.JSONDecodeError):
            print("读取本地 Cookie 文件失败，正在重新获取...")

    print("未找到有效 Cookie，正在通过 Selenium 获取...")
    cookie_str = get_bilibili_cookie_via_selenium()

    # 保存新的 Cookie 到本地
    with open(COOKIE_FILE, 'w') as f:
        json.dump({
            "cookie": cookie_str,
            "timestamp": time.time()
        }, f)

    print("新的 Cookie 已成功获取并保存。")
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
    try:
        resp = requests.get(api, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if data["code"] != 0:
            raise Exception(f"API请求失败: {data}")
        return data["data"]
    except requests.exceptions.RequestException as e:
        raise Exception(f"网络请求失败: {e}")


# 获取视频下载地址
def get_download_url(bvid: str, cid: int, headers):
    api = f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn=80&fnval=16"
    try:
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
    except requests.exceptions.RequestException as e:
        raise Exception(f"网络请求失败: {e}")


# 下载文件
def download_file(url: str, filename: str, headers, desc: str):
    try:
        with requests.get(url, headers=headers, stream=True) as r:
            r.raise_for_status()
            total_size = int(r.headers.get('content-length', 0))
            block_size = 1024
            with open(filename, "wb") as f, tqdm(
                    total=total_size, unit='B', unit_scale=True, desc=desc, ncols=70
            ) as t:
                for chunk in r.iter_content(chunk_size=block_size):
                    if chunk:
                        f.write(chunk)
                        t.update(len(chunk))
    except requests.exceptions.RequestException as e:
        raise Exception(f"下载文件失败: {e}")


# 合并音视频
def merge_av(video_file: str, audio_file: str, output_file: str):
    ffmpeg_path = shutil.which("ffmpeg")
    cmd = [ffmpeg_path, "-y", "-i", video_file, "-i", audio_file, "-c:v", "copy", "-c:a", "aac", output_file]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg 合并失败: {e}")
        print(f"stdout: {e.stdout.decode('utf-8')}")
        print(f"stderr: {e.stderr.decode('utf-8')}")
        raise


def download_part(page, bvid, headers, output_dir):
    cid = page["cid"]
    part_title = page["part"]
    safe_title = re.sub(r'[\\/:*?"<>|]', '_', part_title)
    print(f"\n开始下载分P: {part_title} (CID={cid})")

    try:
        video_url, audio_url = get_download_url(bvid, cid, headers)
        output_path = output_dir / f"{safe_title}.mp4"

        if audio_url:
            video_file = output_dir / f"{safe_title}_video.mp4"
            audio_file = output_dir / f"{safe_title}_audio.mp4"

            download_file(video_url, str(video_file), headers, f"{safe_title} - 视频")
            download_file(audio_url, str(audio_file), headers, f"{safe_title} - 音频")

            print(f"\n正在合并音视频: {output_path.name}")
            merge_av(str(video_file), str(audio_file), str(output_path))

            os.remove(video_file)
            os.remove(audio_file)
            print(f"合并完成并清理临时文件: {output_path.name}")
        else:
            download_file(video_url, output_path, headers, f"{safe_title}")
            print(f"下载完成: {output_path.name}")

    except Exception as e:
        print(f"下载分P '{part_title}' 失败: {e}")


# 主函数
def bilibili_downloader(urls: list):
    check_dependencies()
    headers = get_headers()

    for url in urls:
        try:
            bvid = extract_bvid(url)
            print(f"\n--- 解析到视频 BV 号: {bvid} ---")
            pages = get_play_info(bvid, headers)
            print(f"该视频共有 {len(pages)} 个分P。")

            output_dir = Path(bvid)
            output_dir.mkdir(exist_ok=True)

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(download_part, page, bvid, headers, output_dir) for page in pages]
                for future in as_completed(futures):
                    future.result()

        except Exception as e:
            print(f"处理URL '{url}' 失败: {e}")


if __name__ == "__main__":
    urls_input = input("请输入B站视频网址（可输入多个，用空格或逗号分隔）: ").strip()
    urls = [url.strip() for url in re.split(r'[,\s]+', urls_input) if url.strip()]
    if not urls:
        print("未输入任何网址，程序退出。")
    else:
        bilibili_downloader(urls)
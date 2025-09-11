#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用网页视频获取脚本（尽可能覆盖多类型）：
- 直链文件：.mp4 .webm .mov .mkv .flv .ts
- HLS：.m3u8（未加密或可公开解密）
- DASH：.mpd（未加密）
- <video> / <source> 标签中的 src
- 网页脚本中的直链（正则提取）

可选：使用无头浏览器抓取（需要安装 selenium 或 selenium-wire），用于动态页面与真实网络请求获取 m3u8/mpd。

⚠️ 注意：本工具仅用于合法合规场景。不会也不应绕过 DRM/加密、登录墙、付费墙或其他访问控制。
"""

import argparse
import os
import re
import sys
import time
import json
import shutil
import subprocess
from urllib.parse import urljoin, urlparse
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ---------------------------- 配置项 ----------------------------
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
SUPPORTED_DIRECT_EXT = {".mp4", ".webm", ".mov", ".mkv", ".flv", ".ts"}
REQUEST_TIMEOUT = 20
CHUNK_SIZE = 1024 * 1024  # 1MB
DELAY_BETWEEN_DOWNLOADS = 1.0  # 秒，防止过快请求


# ---------------------------- 工具函数 ----------------------------

def sanitize_filename(name: str) -> str:
    name = re.sub(r"[\\/:*?\"<>|]", "_", name)
    return name.strip() or "video"


def ensure_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise EnvironmentError("未检测到 ffmpeg，请先安装并加入 PATH")
    return path


def make_header_string(headers: dict) -> str:
    """将 headers 转为 ffmpeg -headers 参数字符串（以 \r\n 分隔）。"""
    return "\r\n".join(f"{k}: {v}" for k, v in headers.items()) + "\r\n"


def request_get(url: str, headers: dict) -> requests.Response:
    r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r


# ---------------------------- 解析网页 ----------------------------

def extract_media_urls(page_url: str, html: str) -> dict:
    """从 HTML 中提取可能的视频链接，返回 dict 分类结果。"""
    soup = BeautifulSoup(html, "html.parser")
    base = page_url

    direct_files = set()
    m3u8_list = set()
    mpd_list = set()

    def add_url(u: str):
        if not u:
            return
        abs_u = urljoin(base, u)
        lower = abs_u.split("?")[0].lower()
        if lower.endswith(".m3u8"):
            m3u8_list.add(abs_u)
        elif lower.endswith(".mpd"):
            mpd_list.add(abs_u)
        else:
            # 根据后缀判断直链
            ext = os.path.splitext(urlparse(abs_u).path)[1].lower()
            if ext in SUPPORTED_DIRECT_EXT:
                direct_files.add(abs_u)

    # 1) <video src>, <source src>
    for tag in soup.find_all(["video", "source"]):
        add_url(tag.get("src"))
        # data-src 等懒加载
        for key in ["data-src", "data-url", "data-video", "data-mp4"]:
            add_url(tag.get(key))

    # 2) <a href> 中的直链
    for a in soup.find_all("a"):
        add_url(a.get("href"))

    # 3) 文本与脚本里的直链（正则）
    text = soup.get_text("\n") + "\n".join(s.get_text("\n") for s in soup.find_all("script") if s)
    # 通用匹配 .m3u8/.mpd/直链
    for pat in [
        r"https?://[^\s'\"<>]+?\.m3u8[^\s'\"<>]*",
        r"https?://[^\s'\"<>]+?\.mpd[^\s'\"<>]*",
        r"https?://[^\s'\"<>]+?\.(?:mp4|webm|mov|mkv|flv|ts)(?:[^\s'\"<>]*)",
    ]:
        for m in re.findall(pat, text, flags=re.IGNORECASE):
            add_url(m)

    return {
        "direct": sorted(direct_files),
        "m3u8": sorted(m3u8_list),
        "mpd": sorted(mpd_list),
    }


# ---------------------------- 下载方法 ----------------------------

def download_direct(url: str, out_dir: Path, headers: dict) -> Path:
    local_name = sanitize_filename(os.path.basename(urlparse(url).path) or "video.mp4")
    out_path = out_dir / local_name
    with requests.get(url, headers=headers, stream=True, timeout=REQUEST_TIMEOUT) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
    print(f"[OK] 已下载直链: {out_path}")
    return out_path


def download_stream_with_ffmpeg(stream_url: str, out_dir: Path, headers: dict, prefer_mp4=True) -> Path:
    ffmpeg = ensure_ffmpeg()
    # 输出文件名
    base_name = sanitize_filename(os.path.basename(urlparse(stream_url).path)) or "stream"
    if prefer_mp4 and not base_name.lower().endswith(".mp4"):
        base_name += ".mp4"
    out_path = out_dir / base_name

    # 为 ffmpeg 传 headers（含 UA / Referer / Cookie）
    header_str = make_header_string(headers)
    cmd = [
        ffmpeg,
        "-y",
        "-headers", header_str,
        "-i", stream_url,
        "-c", "copy",
        "-bsf:a", "aac_adtstoasc",
        str(out_path),
    ]
    print("运行:", " ".join([c if "\n" not in c else "<headers>" for c in cmd]))
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        # 简单识别 DRM/加密
        print("[WARN] ffmpeg 下载失败，可能为加密流或受 DRM 保护: ", e)
        raise
    print(f"[OK] 已保存流媒体: {out_path}")
    return out_path


# ---------------------------- 可选：浏览器抓取 ----------------------------

def try_browser_capture(page_url: str, headers: dict, duration_sec: int = 10) -> dict:
    """可选功能：用 selenium-wire 抓取网络请求，搜集 m3u8/mpd/直链。
    仅在安装 selenium-wire 时启用。"""
    try:
        from seleniumwire import webdriver  # type: ignore
        from selenium.webdriver.chrome.options import Options
    except Exception:
        print("[INFO] 未安装 selenium-wire，跳过浏览器抓取。pip install selenium-wire")
        return {"direct": [], "m3u8": [], "mpd": []}

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument(f"--user-agent={headers.get('User-Agent', DEFAULT_UA)}")

    driver = webdriver.Chrome(options=opts)
    driver.get(page_url)
    time.sleep(duration_sec)

    direct, m3u8s, mpds = set(), set(), set()
    for req in driver.requests:
        url = req.url
        if not url:
            continue
        lower = url.lower()
        if ".m3u8" in lower:
            m3u8s.add(url)
        elif ".mpd" in lower:
            mpds.add(url)
        else:
            ext = os.path.splitext(urlparse(url).path)[1].lower()
            if ext in SUPPORTED_DIRECT_EXT:
                direct.add(url)

    driver.quit()
    return {"direct": sorted(direct), "m3u8": sorted(m3u8s), "mpd": sorted(mpds)}


# ---------------------------- 主流程 ----------------------------

def fetch_all_videos(page_url: str, out_dir: Path, headers: dict, use_browser: bool = False):
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) 拉取页面 HTML
    resp = request_get(page_url, headers)
    html = resp.text

    # 2) 解析静态 HTML
    found = extract_media_urls(page_url, html)

    # 3) 可选：浏览器抓取网络请求
    if use_browser:
        captured = try_browser_capture(page_url, headers)
        # 合并
        for key in ["direct", "m3u8", "mpd"]:
            found[key] = sorted({*found[key], *captured.get(key, [])})

    print(json.dumps(found, ensure_ascii=False, indent=2))

    # 4) 逐类下载
    downloaded = []

    # 直链
    for url in found["direct"]:
        try:
            path = download_direct(url, out_dir, headers)
            downloaded.append(str(path))
            time.sleep(DELAY_BETWEEN_DOWNLOADS)
        except Exception as e:
            print(f"[ERR] 直链下载失败 {url}: {e}")

    # HLS
    for url in found["m3u8"]:
        try:
            path = download_stream_with_ffmpeg(url, out_dir, headers)
            downloaded.append(str(path))
            time.sleep(DELAY_BETWEEN_DOWNLOADS)
        except Exception as e:
            print(f"[ERR] m3u8 下载失败 {url}: {e}")

    # DASH
    for url in found["mpd"]:
        try:
            path = download_stream_with_ffmpeg(url, out_dir, headers)
            downloaded.append(str(path))
            time.sleep(DELAY_BETWEEN_DOWNLOADS)
        except Exception as e:
            print(f"[ERR] mpd 下载失败 {url}: {e}")

    print("\n[完成] 输出文件:")
    for p in downloaded:
        print(" -", p)


def build_headers(args) -> dict:
    headers = {"User-Agent": args.ua or DEFAULT_UA}
    if args.referer:
        headers["Referer"] = args.referer
    # 可选 cookie
    if args.cookie:
        headers["Cookie"] = args.cookie
    return headers


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs="https://www.bilibili.com/video/BV1ieNXzBEZC/?spm_id_from=333.1007.tianma.4-1-11.click&vd_source=8717dbc54e2861596ea522ce66955e88", help="视频页面的URL")
    parser.add_argument("--out", default="./downloads", help="输出目录")
    parser.add_argument("--ua", help="User-Agent")
    parser.add_argument("--referer", help="Referer")
    parser.add_argument("--cookie", help="Cookie")
    parser.add_argument("--browser", action="store_true", help="是否使用浏览器cookie")

    args = parser.parse_args()
    out_dir = Path(args.out).resolve()
    headers = build_headers(args)

    try:
        fetch_all_videos(args.url, out_dir, headers, use_browser=args.browser)
    except Exception as e:
        print("[FATAL] 处理失败:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()

import re
import os
import requests

# 示例 Cookie，请替换为你自己浏览器中的 B 站登录 Cookie
COOKIE = "buvid3=5CDBF43D-F13E-29EF-092A-A862C32C6C1347212infoc; b_nut=1737632347; _uuid=910F772E4-E34D-67D8-9A3A-55941022757A549187infoc; enable_web_push=DISABLE; enable_feed_channel=DISABLE; buvid4=B8ABBE61-AD0D-9D26-31EE-A099606FE60848001-025012311-x69p5Dk8wgGkFuB2ZMf1Aw%3D%3D; buvid_fp=278c459cce689e174c928b9582e4f426; header_theme_version=CLOSE; rpdid=|(u)mml|Yl~|0J'u~J~YJkR~J; CURRENT_QUALITY=120; theme-tip-show=SHOWED; DedeUserID=4359600; DedeUserID__ckMd5=f65af20070001bc8; b_lsid=59D21888_198CA64BBC3; bsource=search_google; home_feed_column=4; browser_resolution=920-1165; bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTYwMDE0NjQsImlhdCI6MTc1NTc0MjIwNCwicGx0IjotMX0.ZFaOvLdHaTAr_ht7aCkLhhKKYYl4Y9zzcn6z_OXJMV4; bili_ticket_expires=1756001404; SESSDATA=e4b485ef%2C1771294270%2Cf4008%2A81CjAJJv725GtxdMGO7Rl9ozNNAIxLPRfTAuYiNvpkNRFCoQ2VFc6PKmoG5zuogYc93dESVmQzbThKMzI0UmJNUHNuVUxXV1BjRWtBeFRLTWF1emJndko1dk1qeUdodVljLTNrSmJuOHltY1ZPcTZNNGRweFZVQkJXOTFucXhndUZiaDlUWUFsM1FBIIEC; bili_jct=6a7d5e6849595173116038c75387d35d; sid=p3ygpnoq; CURRENT_FNVAL=2000"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Cookie": COOKIE,
    "Referer": "https://www.bilibili.com/"
}

# 解析 BV 号
def extract_bvid(url: str):
    match = re.search(r"BV[\w]+", url)
    if match:
        return match.group(0)
    raise ValueError("未能解析到 BVID，请确认输入的是具体视频地址，例如：https://www.bilibili.com/video/BV1xx411c7mD")

# 获取视频播放信息（分P列表）
def get_play_info(bvid: str):
    api = f"https://api.bilibili.com/x/player/pagelist?bvid={bvid}&jsonp=jsonp"
    resp = requests.get(api, headers=HEADERS)
    data = resp.json()
    if data["code"] != 0:
        raise Exception(f"接口请求失败: {data}")
    return data["data"]

# 获取视频下载地址（flv或mp4）
def get_download_url(bvid: str, cid: int):
    api = f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn=80&fnval=16"
    resp = requests.get(api, headers=HEADERS).json()
    if resp["code"] != 0:
        raise Exception(f"播放地址请求失败: {resp}")

    # 尝试获取 dash 流的 video+audio
    try:
        video_url = resp["data"]["dash"]["video"][0]["baseUrl"]
        audio_url = resp["data"]["dash"]["audio"][0]["baseUrl"]
        return video_url, audio_url
    except KeyError:
        # fallback 获取 durl 流
        durl = resp["data"]["durl"]
        return durl[0]["url"], None

# 下载文件
def download_file(url: str, filename: str):
    with requests.get(url, headers=HEADERS, stream=True) as r:
        r.raise_for_status()
        with open(filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk:
                    f.write(chunk)
    print(f"下载完成: {filename}")

# 合并音视频（需 ffmpeg 已安装）
def merge_av(video_file: str, audio_file: str, output_file: str):
    import subprocess
    cmd = ["ffmpeg", "-y", "-i", video_file, "-i", audio_file, "-c:v", "copy", "-c:a", "aac", output_file]
    subprocess.run(cmd, check=True)

# 主函数
def bilibili_downloader(url: str):
    try:
        bvid = extract_bvid(url)
    except ValueError as e:
        print(e)
        return

    print(f"解析到视频 BV 号: {bvid}")
    pages = get_play_info(bvid)
    print(f"该视频共有 {len(pages)} 个分P：")

    os.makedirs(bvid, exist_ok=True)

    for page in pages:
        cid = page["cid"]
        part_title = page["part"]
        safe_title = re.sub(r'[\\/:*?"<>|]', '_', part_title)
        print(f"正在下载分P: {part_title} (CID={cid})")

        video_url, audio_url = get_download_url(bvid, cid)
        video_file = os.path.join(bvid, f"{safe_title}_video.mp4")
        if audio_url:
            audio_file = os.path.join(bvid, f"{safe_title}_audio.mp4")
            output_file = os.path.join(bvid, f"{safe_title}.mp4")

            download_file(video_url, video_file)
            download_file(audio_url, audio_file)
            merge_av(video_file, audio_file, output_file)

            # 删除临时文件
            os.remove(video_file)
            os.remove(audio_file)
        else:
            # 单流直接下载
            download_file(video_url, os.path.join(bvid, f"{safe_title}.mp4"))

if __name__ == "__main__":
    url = input("请输入B站视频网址: ").strip()
    bilibili_downloader(url)

import re
import os
import requests
from pathlib import Path
import shutil
import subprocess


# ----------------- MODIFIED START -----------------

# 构建请求头，现在需要手动传入cookie
def get_headers(cookie: str):
    """
    根据用户提供的cookie构建请求头
    """
    if not cookie:
        raise ValueError("Cookie 不能为空，请提供有效的B站Cookie")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cookie": cookie,
        "Referer": "https://www.bilibili.com/"
    }
    return headers


# ----------------- MODIFIED END -----------------

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
    resp.raise_for_status()  # 确保请求成功
    data = resp.json()
    if data["code"] != 0:
        raise Exception(f"获取视频分页信息失败: {data.get('message', '未知错误')}")
    return data["data"]


# 获取视频下载地址
def get_download_url(bvid: str, cid: int, headers):
    # qn=112 为 1080P 高码率, qn=80 为 1080P 高清。可以按需调整
    # fnval=16 表示请求DASH格式的流
    api = f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn=80&fnval=16"
    resp = requests.get(api, headers=headers)
    resp.raise_for_status()
    resp_json = resp.json()
    if resp_json["code"] != 0:
        raise Exception(f"获取播放地址失败: {resp_json.get('message', '未知错误')}")

    try:
        video_url = resp_json["data"]["dash"]["video"][0]["baseUrl"]
        audio_url = resp_json["data"]["dash"]["audio"][0]["baseUrl"]
        return video_url, audio_url
    except (KeyError, IndexError):
        # 兼容一些老视频可能没有DASH格式
        durl = resp_json["data"]["durl"]
        if durl:
            return durl[0]["url"], None
        raise Exception("无法解析到有效的视频下载地址")


# 下载文件
def download_file(url: str, filename: str, headers):
    print(f"开始下载: {Path(filename).name}")
    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        with open(filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):  # 1MB per chunk
                if chunk:
                    f.write(chunk)
    print(f"下载完成: {Path(filename).name}")


# 合并音视频
def merge_av(video_file: str, audio_file: str, output_file: str):
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        raise EnvironmentError("未检测到 ffmpeg，请先安装并将其路径添加到系统环境变量(PATH)中")

    print(f"正在合并音视频到: {Path(output_file).name}")
    cmd = [
        ffmpeg_path,
        "-y",  # 覆盖已存在的文件
        "-i", video_file,
        "-i", audio_file,
        "-c:v", "copy",  # 直接复制视频流，不重新编码
        "-c:a", "copy",  # 直接复制音频流，不重新编码
        output_file
    ]
    # 使用 subprocess.PIPE 来捕获输出，避免在控制台打印过多ffmpeg信息
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    if result.returncode != 0:
        print("FFmpeg 错误信息:", result.stderr)
    print("合并完成！")


# 主函数
def bilibili_downloader(url: str, cookie: str):
    try:
        headers = get_headers(cookie)
        bvid = extract_bvid(url)
        print(f"解析到视频 BV 号: {bvid}")

        pages = get_play_info(bvid, headers)
        print(f"该视频共有 {len(pages)} 个分P。")

        output_dir = Path(bvid)
        output_dir.mkdir(exist_ok=True)

        for i, page in enumerate(pages, 1):
            cid = page["cid"]
            part_title = page["part"]
            # 替换文件名中的非法字符
            safe_title = re.sub(r'[\\/:*?"<>|]', '_', part_title)
            print("-" * 50)
            print(f"[{i}/{len(pages)}] 正在下载分P: {part_title} (CID={cid})")

            output_file = output_dir / f"{safe_title}.mp4"
            if output_file.exists():
                print(f"文件 '{output_file.name}' 已存在，跳过下载。")
                continue

            video_url, audio_url = get_download_url(bvid, cid, headers)
            video_file = output_dir / f"{safe_title}_video.m4s"

            if audio_url:
                audio_file = output_dir / f"{safe_title}_audio.m4s"

                download_file(video_url, str(video_file), headers)
                download_file(audio_url, str(audio_file), headers)
                merge_av(str(video_file), str(audio_file), str(output_file))

                # 清理临时文件
                os.remove(video_file)
                os.remove(audio_file)
            else:
                # 处理没有独立音轨的老视频
                download_file(video_url, output_file, headers)

        print("-" * 50)
        print(f"所有任务完成！视频已保存到 '{bvid}' 文件夹中。")

    except Exception as e:
        print(f"发生错误: {e}")


if __name__ == "__main__":
    # video_url = "https://www.bilibili.com/video/BV1JVtnzGEj6/?spm_id_from=333.337.search-card.all.click&vd_source=8717dbc54e2861596ea522ce66955e88"
    video_url = "https://www.bilibili.com/video/BV1qFbzzoEN9/?spm_id_from=333.337.search-card.all.click"

    # 增加手动输入 Cookie 的环节
    print("\n" + "=" * 60)
    print("请提供您的B站Cookie。")
    print("获取方法请参考说明文档。")
    print("=" * 60)
    user_cookie = "buvid3=5CDBF43D-F13E-29EF-092A-A862C32C6C1347212infoc; b_nut=1737632347; _uuid=910F772E4-E34D-67D8-9A3A-55941022757A549187infoc; enable_web_push=DISABLE; enable_feed_channel=DISABLE; buvid4=B8ABBE61-AD0D-9D26-31EE-A099606FE60848001-025012311-x69p5Dk8wgGkFuB2ZMf1Aw%3D%3D; buvid_fp=278c459cce689e174c928b9582e4f426; header_theme_version=CLOSE; rpdid=|(u)mml|Yl~|0J'u~J~YJkR~J; CURRENT_QUALITY=120; theme-tip-show=SHOWED; DedeUserID=4359600; DedeUserID__ckMd5=f65af20070001bc8; theme-avatar-tip-show=SHOWED; b_lsid=C6C2CF610_19918BCA6B9; bsource=search_google; home_feed_column=5; browser_resolution=2000-1165; SESSDATA=68a3726b%2C1772608642%2C8fdb1%2A91CjDI22ro7fghjFafqLNv0EAVPol6d_phgqoq0ysmYFDPFauCigPiG4ShEXVTTtxJ3fESVnNKbmZOVHp4NE5vZTFIUnpTNU9wZmNvUmstWjR5QjViQU9kcUQ2ZC1nQ1ROMnVNRGVaSG1oeUpLYURxQ19mazR1el9IREh1bXQteFkyV0RIcjl1bzlnIIEC; bili_jct=5d24b05fa98887f9ea8c428213270aa6; sid=8j8ruzer; bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NTczMTU4NDgsImlhdCI6MTc1NzA1NjU4OCwicGx0IjotMX0.o1CF3f5ETb_gTIEPn_1yCXpx6MfoAaN_sEeFoHN8QPM; bili_ticket_expires=1757315788; CURRENT_FNVAL=4048; bp_t_offset_4359600=1109043568955097088"

    if video_url and user_cookie:
        bilibili_downloader(video_url, user_cookie)
    else:
        print("视频网址和Cookie均不能为空。")
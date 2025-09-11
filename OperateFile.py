def write_scores(file_path):
    """写入学生成绩"""
    scores = [
        "Alice,85",
        "Bob,92",
        "Charlie,78"
    ]
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            for line in scores:
                f.write(line + "\n")
        print(f"✅ 成绩写入文件 {file_path} 成功")
    except Exception as e:
        print(f"❌ 写入文件失败: {e}")


def read_scores(file_path):
    """读取学生成绩"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                name, score = line.strip().split(",")
                print(f"学生：{name}，成绩：{score}")
    except FileNotFoundError:
        print("❌ 文件不存在，无法读取！")
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
    finally:
        print("📖 文件读取结束")


if __name__ == "__main__":
    file_name = "scores.txt"
    write_scores(file_name)
    read_scores(file_name)

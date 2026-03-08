import re
import sqlite3
import requests
import threading
import numpy as np
import pyautogui
import easyocr
import wordninja
from PIL import ImageGrab
from pynput import keyboard
from plyer import notification
from datetime import datetime

# ================= 核心配置区 =================
DB_NAME = "my_vocabulary.db"

print("⏳ 正在加载 PyTorch 深度学习 OCR 模型 (首次运行可能需要下载权重文件)...")
# 初始化 EasyOCR，只加载英文模型以提高速度。gpu=True 表示尝试使用显卡加速
reader = easyocr.Reader(['en'], gpu=True) 
print("✅ 模型加载完毕！")
# ==============================================

class WordHunter:
    def __init__(self):
        self.setup_db()
        self.is_processing = False 
        print("✨ WordHunter (EasyOCR 智能坐标版) 已启动！")
        print("👉 玩法：将鼠标停在屏幕上任何你不认识的英文单词上，按下 Ctrl+Alt+Q")

    def setup_db(self):
        """初始化数据库：创建 7 个完整的列"""
        conn = sqlite3.connect(DB_NAME)
        conn.execute('''CREATE TABLE IF NOT EXISTS vocab 
                        (word TEXT PRIMARY KEY, 
                         phonetic TEXT, 
                         meaning TEXT, 
                         context TEXT, 
                         count INTEGER, 
                         created_at DATETIME, 
                         last_seen DATETIME)''')
        conn.close()

    def fetch_and_save(self, word):
        """后台线程：负责查词和存库，拦截无效乱码"""
        try:
            url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
            
            # 尝试联网查词
            try:
                res = requests.get(url, timeout=4)
                # 🌟 核心拦截器：如果 API 明确说找不到这个词 (返回 404)，说明可能是乱码
                if res.status_code == 404:
                    print(f"🛑 拦截乱码或无效词汇: '{word}'，不存入数据库。")
                    self.notify("未能识别含义", f"'{word}' 不是一个有效的单词")
                    return # 直接结束，不存库
                
                if res.status_code == 200:
                    data = res.json()[0]
                    phonetic = data.get('phonetic', 'N/A')
                    meaning = data['meanings'][0]['definitions'][0]['definition']
                else:
                    phonetic, meaning = "N/A", "未找到在线释义"

            except requests.RequestException:
                # 只有在网络彻底断开时，才勉强存一下，防止漏记
                phonetic, meaning = "N/A", "网络超时，暂存单词"
                print(f"⚠️ 网络连接异常，单词已暂存: {word}")

            # 存入数据库
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute('''
                INSERT INTO vocab (word, phonetic, meaning, context, count, created_at, last_seen) 
                VALUES (?, ?, ?, ?, 1, ?, ?)
                ON CONFLICT(word) DO UPDATE SET 
                    count = count + 1, 
                    last_seen = excluded.last_seen
            ''', (word, phonetic, meaning, "屏幕拾取", now, now))
            
            conn.commit()
            conn.close()

            self.notify(f"✅ 成功收录: {word}", f"[{phonetic}] {meaning[:50]}...")
            print(f"入库成功: {word} | 释义: {meaning[:30]}...")

        except Exception as e:
            print(f"❌ 后台处理错误: {e}")
        finally:
            self.is_processing = False
    def notify(self, title, message):
        """发送系统桌面弹窗"""
        notification.notify(title=title, message=message, app_name="WordHunter", timeout=2)

    def fast_capture(self):
        """核心截图与 EasyOCR 智能空间定位逻辑"""
        if self.is_processing: 
            print("⏳ 正在处理，请勿频繁按键...")
            return
        
        self.is_processing = True

        try:
            x, y = pyautogui.position()
            box_w, box_h = 300, 100
            bbox = (x - box_w//2, y - box_h//2, x + box_w//2, y + box_h//2) 
            
            img = ImageGrab.grab(bbox)
            img_array = np.array(img)
            
            # 🌟 核心修复区：加上 mag_ratio (放大图像) 和 width_ths (降低合并容忍度)
            # mag_ratio=2.5 会让引擎把图片放大 2.5 倍再看，空格会变得非常明显
            # width_ths=0.3 严禁引擎把稍微靠近的两个框合并
            results = reader.readtext(img_array, detail=1, mag_ratio=2.5, width_ths=0.3)

            if not results:
                print("⚠️ 未在鼠标附近识别到文字")
                self.is_processing = False
                return

            target_word = None
            center_x, center_y = box_w // 2, box_h // 2

            # 智能坐标碰撞检测
            for (bbox_coords, text, prob) in results:
                top_left = bbox_coords[0]
                bottom_right = bbox_coords[2]
                min_x, min_y = top_left[0], top_left[1]
                max_x, max_y = bottom_right[0], bottom_right[1]
                
                # 如果鼠标在单词框内
                if (min_x <= center_x <= max_x) and (min_y <= center_y <= max_y):
                    # 1. 提取纯字母串 (例如此时可能拿到了 "problemoff")
                    raw_alpha = "".join(re.findall(r'[a-zA-Z]+', text))
                    
                    if len(raw_alpha) >= 2:
                        # 2. 🥷 核心补丁：呼叫 WordNinja 斩断连体词
                        # 它会把 "problemoff" 变成列表: ["problem", "off"]
                        split_words = wordninja.split(raw_alpha)
                        
                        if len(split_words) > 1:
                            print(f"🔪 触发智能分词: 连体词 '{raw_alpha}' 被切分为 {split_words}")
                            # 3. 策略：连体词被切开后，我们选最长的那一个去查词！
                            # 比如 ["problem", "off"] 会选中 "problem"
                            # 这样可以自动过滤掉 of, a, the, in 等介词杂音
                            target_word = max(split_words, key=len)
                        else:
                            # 如果没被切开，说明本来就是个正常的单字
                            target_word = split_words[0]
                            
                        break # 命中目标，跳出循环

            if target_word:
                print(f"🎯 像素级锁定单词: '{target_word}'，正在后台查词...")
                threading.Thread(target=self.fetch_and_save, args=(target_word,)).start()
            else:
                print("⚠️ 鼠标未对准有效的英文单词。")
                self.is_processing = False

        except Exception as e:
            print(f"❌ 识别流程失败: {e}")
            self.is_processing = False
    def run(self):
        """启动全局键盘监听"""
        with keyboard.GlobalHotKeys({'<ctrl>+<alt>+q': self.fast_capture}) as h:
            h.join()

if __name__ == "__main__":
    app = WordHunter()
    app.run()
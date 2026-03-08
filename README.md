# WordHunter 🎯 - 智能屏幕划词翻译与生词本

WordHunter 是一款轻量级、智能化的屏幕单词捕获与翻译工具。只需将鼠标悬停在屏幕上的任意英文单词上并按下快捷键，程序便会自动利用深度学习 OCR 技术精准提取单词，联网查询释义，并将其持久化保存到本地数据库中，为你打造专属的生词本。

## ✨ 核心特性

* 🚀 **深度学习 OCR**：底层采用基于 PyTorch 的 `EasyOCR`，支持复杂背景和极小字体的精准识别，完胜传统 Tesseract 引擎。
* 🎯 **像素级坐标锁定**：独创的空间碰撞算法，仅提取鼠标指针正下方的一个单词，彻底解决全屏 OCR 带来的上下文噪音。
* 🥷 **智能 NLP 分词**：引入 `wordninja`，完美解决 OCR 将相邻单词“粘连”的问题（例如自动将 `problemoff` 切分为 `problem` 和 `off` 并提取主词）。
* 📖 **自动云端查词**：接入 Free Dictionary API，自动获取美式音标及权威英文释义，并自带乱码/无效词拦截机制。
* 💾 **本地持久化与高频词统计**：使用轻量级 `SQLite` 数据库。自动过滤重复收录，并在重复查询时增加“查词频次”权重，方便日后重点复习。
* 🔔 **无感系统通知**：后台静默运行，识别成功后通过系统原生弹窗反馈结果，不打断阅读心流。

---

## 🛠️ 环境要求与准备工作

### 1. 运行环境
* Python 3.8 或更高版本
* *(可选但推荐)* 搭载 NVIDIA 显卡并配置好 CUDA 环境（EasyOCR 会自动调用 GPU 加速，实现毫秒级识别）。

### 2. 依赖安装 (终端运行)
```bash
pip install easyocr pyautogui pynput requests plyer pillow numpy wordninja

```

> **注意：** 首次运行程序时，`EasyOCR` 会自动从网络下载预训练的神经网络权重文件（约 70MB），请保持网络畅通并耐心等待。

### 3. 🧩 核心技术栈 (代码引入清单)

本项目的核心底层逻辑依赖以下模块，开发前请确保环境均已配置完毕：

```python
import re                  # 正则表达式，用于清洗纯英文字母
import sqlite3             # 轻量级本地数据库，用于生词本持久化
import requests            # 发送网络请求，调用在线词典 API
import threading           # 多线程，用于后台查词防卡顿
import numpy as np         # 矩阵运算，配合图像处理
import pyautogui           # 获取鼠标实时坐标
import easyocr             # 核心组件：PyTorch 深度学习 OCR 引擎
import wordninja           # 核心组件：基于概率的 NLP 英文自动分词
from PIL import ImageGrab  # 屏幕局部快速截图
from pynput import keyboard# 注册与监听全局快捷键
from plyer import notification # 发送操作系统级原生弹窗通知
from datetime import datetime  # 获取记录时间

```

---

## 🚀 快速开始

1. **克隆项目到本地**
```bash
git clone [https://github.com/你的用户名/你的仓库名.git](https://github.com/你的用户名/你的仓库名.git)
cd 你的仓库名

```


2. **运行主程序**
```bash
python word_collector.py

```


3. **开始捕获生词**
* 程序启动后将在后台运行全局键盘监听。
* 打开任意英文网页、PDF 甚至带有复杂背景的图片。
* 将鼠标光标**直接悬停在**你不认识的英文单词上方。
* 按下全局快捷键：`Ctrl + Alt + Q`。
* 屏幕右下角将弹出系统通知，显示该单词的音标与释义，数据已自动存入数据库！



---

## 🗄️ 数据库结构

程序首次运行时，会在同级目录下自动生成 `my_vocabulary.db` 文件。核心表 `vocab` 的结构如下：

| 字段名 | 类型 | 说明 |
| --- | --- | --- |
| `word` | TEXT | 单词本体 (主键) |
| `phonetic` | TEXT | 音标 |
| `meaning` | TEXT | 英文释义 |
| `context` | TEXT | 单词被捕获时的来源标签 (如：屏幕拾取) |
| `count` | INTEGER | 历史查询次数 (重复对同一单词按快捷键会自动 +1) |
| `created_at` | DATETIME | 首次收录时间 |
| `last_seen` | DATETIME | 最后一次查询时间 |

---

## 💡 常见问题与踩坑指南 (FAQ)

本项目的开发过程中经历了多次迭代，如果你在二次开发或运行中遇到问题，请参考以下避坑指南：

### 1. 数据库报错：`table vocab has 7 columns but 6 values were supplied`

* **现象**：后台处理出错，提示列数与提供的值不匹配；或者提示 `no such column: meaning`。
* **原因**：代码更新后，数据库的表结构（Schema）增加了新字段，但本地遗留的旧 `.db` 文件并未同步更新，导致插入数据时“坑位”对应不上。
* **解决办法**：进入项目根目录，**直接删除旧的 `my_vocabulary.db` 文件**。重新运行程序，代码会按照最新的结构重新建表。

### 2. OCR 引擎把多个单词粘连在一起（如：`problemoff` 或 `offoodand`）

* **现象**：当网页上的单词间距较小时，OCR 可能会将相邻的词识别为一个连体词。
* **原因**：默认情况下的合并阈值容忍度较高，且缺乏针对英文特征的二次拆分。
* **解决办法**：本项目已引入双重防线完美解决此问题：
1. 在 `readtext` 中配置 `mag_ratio=2.5` 和 `width_ths=0.3`，在内存中放大图像并降低识别框合并的概率。
2. 引入 `wordninja` 库进行 NLP 级二次清洗。它可以基于英文词频概率统计模型，自动将 `problemoff` 精准切分为 `['problem', 'off']`，并智能提取你真正想查的主词。



### 3. 为什么放弃 Tesseract 而使用 EasyOCR？

* **现象**：在早期版本使用 Tesseract 时，极易遇到路径配置报错（`tesseract.exe is not installed or it's not in your PATH`），且遇到代码编辑器等复杂环境时经常识别出无关杂音。
* **原因**：Tesseract 属于传统 OCR 引擎，依赖本地系统环境变量配置，且无法自动输出高质量的单词级边界框（Bounding Box）。
* **选择 EasyOCR**：EasyOCR 是基于 PyTorch 的端到端深度学习模型（CRNN），不仅开箱即用，更自带高精度的坐标输出，这是实现本项目“像素级空间坐标锁定”算法的核心基础。

---

## 📝 许可证

MIT License

```

***

你可以把你在网页上看到的那个带括号的 `git clone` 网址替换为你真正的 GitHub 仓库链接。要不要我接着教你怎么用 Git 命令行把这些文件传到你的 GitHub 上？

```

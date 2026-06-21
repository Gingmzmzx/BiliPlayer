# BiliPlayer | B站音乐播放器

---

## 介绍视频
[B站 XzyStudio1 【我回来辣！！！】 ](https://www.bilibili.com/video/BV1QgEz6CEtB/?share_source=copy_web&vd_source=6550d40762e4dc7c8327189d8582544b)

## 特性
1. 指定用户UID和收藏夹名后，程序会自动读取收藏夹内的视频，并播放音频
2. 右侧进度条，将鼠标移动到进度条上会显示当前正在播放的歌曲信息。进度条是置顶显示的，占地小巧，不会影响您当前的工作，同时让您沉浸于歌曲之中
3. 您可以拖动进度条改变进度，一首播放完后会自动切换下一首（随机切）。点击进度条上那个按钮可以暂停/开始
4. 播放器核心使用playwright-python，并非直接请求接口，稳定高效
5. 您可以针对特定的视频指定播放特定的P，或者仅播放视频中的某一段（目前需要手动编辑`BiliPlayer/config.py`）

## 使用
目前还没打包，功能还在完善。您可以克隆本仓库后在项目根目录下直接执行`main.py`  
哦对了，你还需要`playwright`和`PyQt6`，`playwright`需要提前装好`chromium`  
本项目基于Python3.8编写

## 特别声明
本项目采用Apache License 2.0，不得商用。  

# 基于 BiliBili 平台推荐算法机制反向推导用户画像系统

## 项目简介

这是一个基于 B站首页推荐视频数据,通过分析用户获得的推荐内容来反向推导用户画像的系统。系统会自动爬取 B站首页推荐的视频数据,并通过网络爬行、关键词提取和词向量模型等方法分析这些数据,生成用户画像报告。

## 主要功能

- 自动爬取 B站首页推荐视频数据
- 分析视频内容类别分布
- 识别热门话题和关键词
- 统计视频热度分布
- 分析 UP主分布情况
- 生成详细的用户画像报告
- 可视化数据展示

## 技术栈

- 后端: Python + Flask
- 前端: HTML + JavaScript + ECharts
- 爬虫: Selenium
- 数据分析: jieba + gensim

## 安装说明

1. 克隆项目到本地: 
```bash
git clone 
cd System_for_Reverse_Engineering_User_Profiles_Based_on_BiliBili-s_Recommendation_Algorithm
```

2. 安装依赖: 
```bash
pip install -r requirements.txt
```

3. 下载词向量模型:
- 下载 [wiki.zh.vec](https://dl.fbaipublicfiles.com/fasttext/vectors-wiki/wiki.zh.vec) 文件
- 将文件放在项目根目录

4. 安装 Chrome 浏览器和对应版本的 ChromeDriver

## 使用方法

1. 启动服务器:
```bash
python app.py
```

2. 访问 [http://127.0.0.1:5000](http://127.0.0.1:5000) 查看结果


2. 打开浏览器访问: `http://localhost:5000`

3. 使用步骤:
   - 输入需要爬取的视频数量(10-1000)
   - 点击"开始爬取数据"按钮
   - 使用 B站手机 APP 扫描二维码登录
   - 等待数据爬取完成
   - 点击"分析数据"按钮查看分析结果

## 分析结果说明

系统会生成以下分析结果:

1. 用户画像描述
   - 主要关注领域
   - 用户特点
   - 推荐策略

2. 内容分类分布
   - 以饼图形式展示各类内容占比
   - 包括技术、游戏、数码等分类

3. 热门话题分布
   - 以柱状图展示热门话题分布
   - 展示最受关注的话题领域

4. 视频热度分析
   - 平均播放量
   - 最高播放量
   - 播放量分布情况

## 注意事项

1. 首次使用需要下载词向量模型文件(wiki.zh.vec)
2. 需要安装 Chrome 浏览器和对应版本的 ChromeDriver
3. 确保网络连接稳定
4. B站登录状态会定期失效,需要重新登录
5. 建议每次爬取数量不要超过 500 个

## 项目结构
```
project/
├── app.py # Flask 应用主文件
├── BilibiliSpider.py # B站爬虫模块
├── bilibili_analyzer.py # 数据分析模块
├── templates/ # 前端模板
│ └── index.html # 主页面
├── wiki.zh.vec # 词向量模型(需下载)
└── requirements.txt # 项目依赖
```

## 贡献指南

欢迎提交 Issue 和 Pull Request 来帮助改进项目。

## 许可证

MIT License
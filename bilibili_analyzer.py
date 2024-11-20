import json
from collections import Counter
import jieba
import jieba.analyse
import numpy as np
from gensim.models import KeyedVectors
from collections import defaultdict

class BilibiliAnalyzer:
    def __init__(self, json_file='bilibili_videos.json', status_queue=None, word_vectors=None):
        self.videos = self._load_json(json_file)
        self.status_queue = status_queue
        
        # 定义类别关键词
        self.category_keywords = {
            '技术': {
                'core': ['编程', '开发', '技术', '代码', '软件', '工程', '计算机', '程序', '教程'],
                'related': [
                    'python', 'java', 'c++', 'javascript', 'golang', 'rust', 'php', 'sql',
                    '前端', '后端', '全栈', '移动开发', 'web开发', '桌面开发', '游戏开发',
                    '人工智能', '机器学习', '深度学习', '数据分析', '云计算', '大数据', '区块链',
                    '数据库', '服务器', '运维', '架构', '网络', '安全', '测试', '运维',
                    'vue', 'react', 'spring', 'django', 'flask', 'docker', 'kubernetes',
                    '算法', '数据结构', '设计模式', '编程思想', '源码分析',
                    'git', 'linux', '部署', '调优', '重构', '项目管理'
                ]
            },
            '游戏': {
                'core': ['游戏', '通关', '攻略', '测评', '实况', '解说', '主机', '手游'],
                'related': [
                    'pc游戏', '主机游戏', '手机游戏', 'ps5', 'xbox', 'switch', 'steam',
                    'mmorpg', 'fps', 'moba', '卡牌游戏', '策略游戏', '动作游戏', '冒险游戏',
                    '原神', '星穹铁道', '王者荣耀', '英雄联盟', 'csgo', 'minecraft', '塞尔达',
                    '开荒', '副本', 'pvp', 'pve', '氪金', '抽卡', '肝', '练度',
                    '剧情', '角色', '装备', '技能', '关卡', '成就', '任务', '挑战',
                    '电竞', '赛事', '主播', '联机', '单机', '氪金', '测试服'
                ]
            },
            '数码': {
                'core': ['数码', '科技', '手机', '电脑', '智能', '硬件', '评测'],
                'related': [
                    '苹果', '华为', '小米', 'oppo', 'vivo', '三星', '荣耀', 'realme',
                    'cpu', '显卡', '主板', '内存', '固态', '机箱', '电源', '散热',
                    '键盘', '鼠标', '耳机', '音响', '显示器', '摄像头', '麦克风',
                    '智能手表', '平板', '可穿戴', '智能家居', '路由器', '充电器',
                    'ios', '安卓', 'windows', 'macos', '鸿蒙', '系统更新',
                    '评测', '开箱', '上手', '体验', '对比', '跑分', '续航'
                ]
            },
            '影视': {
                'core': ['电影', '电视剧', '视频', '剧情', '解说', '影视', '动漫'],
                'related': [
                    '动作片', '喜剧片', '科幻片', '恐怖片', '纪录片', '动画片', '剧情片',
                    '导演', '演员', '编剧', '制片', '摄影', '剪辑', '特效', '配音',
                    '番剧', '动画', '漫画改编', '声优', '热血', '治愈', '后宫',
                    '剪辑', '特效', '调色', '分镜', '转场', '字幕', '混音',
                    '预告片', '花絮', '幕后', '采访', '首映', '票房', '收视率'
                ]
            },
            '生活': {
                'core': ['vlog', '日常', '美食', '旅游', '生活'],
                'related': [
                    '探店', '测评', '开箱', '美妆', '穿搭', '护肤', '健身', 
                    '运动', '美甲', '发型', '化妆', '护理', '美容', '减肥', 
                    '瘦身', '健康', '养生', '美体', '美发', '护发'
                ]
            },
            '知识': {
                'core': ['科普', '历史', '知识', '学习', '教育'],
                'related': [
                    '考古', '医学', '物理', '化学', '科学', '地理', '生物', 
                    '天文', '数学', '文学', '哲学', '心理', '考研', '课程', 
                    '讲座', '公开课', '学术', '研究', '实验'
                ]
            },
            '娱乐': {
                'core': ['搞笑', '鬼畜', '娱乐', '音乐'],
                'related': [
                    '整活', '沙雕', '梗', '舞蹈', '唱歌', '乐器', '说唱', 
                    '饶舌', '演奏', '综艺', '明星', '艺人', '网红', '主播', 
                    '直播', '热点', '八卦'
                ]
            }
        }
        
        # 使用传入的词向量模型或加载新模型
        try:
            self._send_status({"type": "analyze_progress", "data": {"message": "正在准备词向量模型...", "progress": 10}})
            self.word_vectors = word_vectors if word_vectors is not None else KeyedVectors.load_word2vec_format('wiki.zh.vec')
            self._send_status({"type": "analyze_progress", "data": {"message": "词向量模型准备完成", "progress": 20}})
        except Exception as e:
            self._send_status({"type": "analyze_progress", "data": {"message": f"词向量模型准备失败: {str(e)}", "progress": 0}})
            print("词向量模型准备失败")
            raise

    def _send_status(self, message):
        """发送状态消息的内部方法"""
        if self.status_queue:
            self.status_queue.put(message)
        if isinstance(message, dict) and message.get("type") == "analyze_progress":
            print(f"分析进度: {message['data']['message']} ({message['data']['progress']}%)")

    def _load_json(self, file_path):
        """加载JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载JSON文件失败: {e}")
            return []

    def extract_keywords(self, text, topK=5):
        """使用TextRank算法提取关键词"""
        return jieba.analyse.textrank(text, topK=topK)

    def calculate_similarity(self, keywords, category):
        """计算关键词与类别的相似度"""
        similarities = []
        
        # 计算与核心词的相似度
        for keyword in keywords:
            if keyword in self.word_vectors:
                core_sims = [
                    self.word_vectors.similarity(keyword, core_word)
                    for core_word in self.category_keywords[category]['core']
                    if core_word in self.word_vectors
                ]
                if core_sims:
                    similarities.append(max(core_sims) * 1.5)  # 核心词相似度权重更高
                    
        # 计算与相关词的相似度
        for keyword in keywords:
            if keyword in self.word_vectors:
                related_sims = [
                    self.word_vectors.similarity(keyword, related_word)
                    for related_word in self.category_keywords[category]['related']
                    if related_word in self.word_vectors
                ]
                if related_sims:
                    similarities.append(max(related_sims))
                    
        return np.mean(similarities) if similarities else 0

    def analyze_content_categories(self):
        """使用语义分析的方式分析视频内容类别"""
        self._send_status({"type": "analyze_progress", "data": {"message": "正在分析内容类别...", "progress": 30}})
        video_categories = defaultdict(int)
        uncategorized = []
        
        for video in self.videos:
            # 合并标题和UP主名称以提供更多上下文
            text = f"{video['title']} {video['up_name']}"
            
            # 提取关键词
            keywords = self.extract_keywords(text)
            print(keywords)
            # 计算每个类别的相似度得分
            category_scores = {
                category: self.calculate_similarity(keywords, category)
                for category in self.category_keywords.keys()
            }
            
            # 找出得分最高的类别
            max_score = max(category_scores.values())
            if max_score > 0.3:  # 设置阈值，避免强行分类
                best_category = max(category_scores.items(), key=lambda x: x[1])[0]
                video_categories[best_category] += 1
            else:
                video_categories['其他'] += 1
                uncategorized.append({
                    'title': video['title'],
                    'keywords': keywords,
                    'scores': category_scores
                })
                
        # 打印未分类视频的信息以供分析
        if uncategorized:
            print("\n未能准确分类的视频:")
            for video in uncategorized[:5]:  # 只显示前5个作为示例
                print(f"\n标题: {video['title']}")
                print(f"提取的关键词: {', '.join(video['keywords'])}")
                print("各类别得分:", {k: f"{v:.3f}" for k, v in video['scores'].items()})
                
        self._send_status({"type": "analyze_progress", "data": {"message": "内容类别分析完成", "progress": 50}})
        return dict(video_categories)

    def analyze_up_distribution(self):
        """分析UP主分布"""
        self._send_status({"type": "analyze_progress", "data": {"message": "正在分析UP主分布...", "progress": 60}})
        up_names = [video['up_name'] for video in self.videos if video['up_name'] and video['up_name'] != '未知']
        up_counts = Counter(up_names)
        self._send_status({"type": "analyze_progress", "data": {"message": "UP主分布分析完成", "progress": 70}})
        return up_counts

    def analyze_popular_topics(self):
        """分析热门话题"""
        self._send_status({"type": "analyze_progress", "data": {"message": "正在分析热门话题...", "progress": 80}})
        # 定义话题关键词映射
        topic_keywords = {
            'AI与人工智能': [
                'ai', '人工智能', 'gpt', '大模型', '机器学习', '深度学习', 'chatgpt',
                '神经网络', '自然语言处理', '计算机视觉', '语音识别', '强化学习',
                'stable diffusion', 'midjourney', 'dall-e', '人工智能应用'
            ],
            '编程开发': [
                'python', 'java', '编程', '代码', '开发', '程序', '算法', '前端', '后端',
                '全栈', '框架', 'web开发', '移动开发', '游戏开发', '数据库', 'api',
                '开源项目', '代码review', '程序设计', '软件工程'
            ],
            '游戏': [
                '游戏', '原神', 'minecraft', '我的世界', '联机', '手游', '攻略', '通关',
                '主机游戏', '端游', '网游', '单机', '开荒', 'mmorpg', 'fps', 'moba',
                '赛事', '电竞', '主播', '实况'
            ],
            '数码科技': ['手机', '电脑', '数码', '硬件', 'iphone', '华为', '小米', '苹果'],
            '教育学习': ['教程', '学习', '考试', '考研', '讲解', '知识', '入门', '教学'],
            '生活日常': ['生活', '日常', 'vlog', '美食', '旅游', '开箱', '测评'],
            '影视动漫': ['电影', '视频', '动画', '番剧', '解说', '剧情', '动漫'],
            '网络文化': ['梗', '鬼畜', '整活', '搞笑', '网红', '直播', '热点']
        }
        
        topic_counts = defaultdict(int)
        
        for video in self.videos:
            title = video['title'].lower()
            # 对每个标题，判断属于哪个话题
            for topic, keywords in topic_keywords.items():
                if any(keyword in title for keyword in keywords):
                    topic_counts[topic] += 1
                    break  # 每个视频只归类到一个主话题
        
        # 按出现次数排序
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        self._send_status({"type": "analyze_progress", "data": {"message": "热门话题分析完成", "progress": 90}})
        return sorted_topics

    def analyze_video_popularity(self):
        """分析视频热度分布"""
        def convert_play_count(count):
            if isinstance(count, str):
                if '万' in count:
                    return float(count.replace('万', '')) * 10000
                try:
                    return float(count)
                except:
                    return 0
            return 0

        play_counts = [convert_play_count(video['play_count']) for video in self.videos if video['play_count'] != '未知']
        if play_counts:
            avg_plays = sum(play_counts) / len(play_counts)
            max_plays = max(play_counts)
            return {
                '平均播放量': avg_plays,
                '最高播放量': int(max_plays),
                '播放量分布': {
                    '10万+': sum(1 for x in play_counts if x >= 100000),
                    '1万-10万': sum(1 for x in play_counts if 10000 <= x < 100000),
                    '1千-1万': sum(1 for x in play_counts if 1000 <= x < 10000),
                    '1千以下': sum(1 for x in play_counts if x < 1000)
                }
            }
        return None

    def generate_user_profile(self):
        """生成用户画像"""
        try:
            self._send_status({"type": "analyze_progress", "data": {"message": "开始生成用户画像...", "progress": 25}})
            content_categories = self.analyze_content_categories()
            popular_topics = self.analyze_popular_topics()
            popularity_stats = self.analyze_video_popularity()
            up_distribution = self.analyze_up_distribution()

            # 将字典转换为Counter对象
            categories_counter = Counter(content_categories)
            
            profile = {
                '内容偏好': dict(content_categories),
                '热门话题': dict(popular_topics[:5]),  # 只展示前5个主要话题
                '视频热度分析': popularity_stats
            }

            # 使用Counter对象的most_common方法
            main_interests = [cat for cat, _ in categories_counter.most_common(3)]
            top_topics = [topic for topic, _ in popular_topics[:3]]  # 获取前三个主要话题

            # 计算主要兴趣的占比
            total_videos = sum(content_categories.values())
            main_interest_percentage = (content_categories[main_interests[0]] / total_videos * 100) if total_videos > 0 else 0

            description = f"""
根据分析，该用户主要关注以下领域：
{', '.join(main_interests)}

用户特点：
内容偏好：{main_interests[0]}类内容最多，占比{main_interest_percentage:.1f}%
热门话题：最常出现的关键词为 {', '.join(top_topics)}

推荐策略：
建议推送更多{main_interests[0]}相关的优质内容
可以关注{[up for up, _ in up_distribution.most_common(10)]}等UP主的更新
"""
            profile['用户画像描述'] = description

            self._send_status({"type": "analyze_progress", "data": {"message": "用户画像生成完成", "progress": 100}})
            return profile
        except Exception as e:
            self._send_status({"type": "analyze_progress", "data": {"message": f"分析出错: {str(e)}", "progress": 0}})
            raise

if __name__ == "__main__":
    analyzer = BilibiliAnalyzer()
    profile = analyzer.generate_user_profile()
    
    # 打印分析结果
    print("\n=== B站用户画像分析 ===")
    print(profile['用户画像描述'])
    
    print("\n=== 详细统计 ===")
    for category, stats in profile.items():
        if category != '用户画像描述':
            print(f"\n{category}:")
            print(json.dumps(stats, ensure_ascii=False, indent=2)) 
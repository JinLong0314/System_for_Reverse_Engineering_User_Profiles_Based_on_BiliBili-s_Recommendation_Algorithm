from flask import Flask, render_template, jsonify, request, send_file
from BilibiliSpider import Bilibili
from bilibili_analyzer import BilibiliAnalyzer
import json
import threading
import queue
import os
from gensim.models import KeyedVectors

app = Flask(__name__, static_url_path='')

# 用于存储爬虫状态和消息的队列
status_queue = queue.Queue()
is_crawling = False

# 用于存储历史消息
message_history = []

# 全局变量存储词向量模型
word_vectors = None
model_loading_error = None

def load_word_vectors():
    """加载词向量模型的函数"""
    global word_vectors, model_loading_error
    try:
        print("开始加载词向量模型...")
        word_vectors = KeyedVectors.load_word2vec_format('wiki.zh.vec')
        print("词向量模型加载完成")
    except Exception as e:
        model_loading_error = str(e)
        print(f"词向量模型加载失败: {e}")

# 在后台线程中加载词向量模型
loading_thread = threading.Thread(target=load_word_vectors)
loading_thread.start()

def save_messages():
    """保存消息到文件"""
    with open('message_history.json', 'w', encoding='utf-8') as f:
        json.dump(message_history, f, ensure_ascii=False, indent=2)

def load_messages():
    """从文件加载消息"""
    global message_history
    try:
        if os.path.exists('message_history.json'):
            with open('message_history.json', 'r', encoding='utf-8') as f:
                message_history = json.load(f)
    except Exception as e:
        print(f"加载历史消息出错: {e}")
        message_history = []

@app.route('/model_status')
def model_status():
    """检查词向量模型加载状态"""
    if model_loading_error:
        return jsonify({
            "status": "error",
            "message": f"词向量模型加载失败: {model_loading_error}"
        })
    elif word_vectors is None:
        return jsonify({
            "status": "loading",
            "message": "词向量模型正在加载中..."
        })
    else:
        return jsonify({
            "status": "ready",
            "message": "词向量模型已加载完成"
        })

@app.route('/clear_data')
def clear_data():
    """清除所有数据"""
    global message_history
    try:
        # 清除消息历史
        message_history = []
        if os.path.exists('message_history.json'):
            os.remove('message_history.json')
            
        # 清除爬取的数据
        if os.path.exists('bilibili_videos.json'):
            os.remove('bilibili_videos.json')
            
        return jsonify({
            "status": "success",
            "message": "数据已清除"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"清除数据时出错: {str(e)}"
        })

def run_spider(num):
    """运行爬虫的函数"""
    global is_crawling
    spider = None
    try:
        status_queue.put("开始运行爬虫...")
        spider = Bilibili(num,status_queue=status_queue)
        spider.bilibili()
        status_queue.put("爬虫运行完成！")
    except Exception as e:
        status_queue.put(f"爬虫出错: {str(e)}")
    finally:
        if spider:
            spider.teardown_method(None)
        is_crawling = False

@app.route('/')
def index():
    """主页路由"""
    load_messages()  # 加载历史消息
    return render_template('index.html', message_history=message_history)

@app.route('/start_crawl')
def start_crawl():
    """启动爬虫的路由"""
    global is_crawling
    if not is_crawling:
        is_crawling = True
        # 获取爬取数量参数，默认为100
        num = request.args.get('num', 100, type=int)
        while not status_queue.empty():
            status_queue.get()
        # 传递爬取数量参数
        thread = threading.Thread(target=run_spider, args=(num,))
        thread.start()
        return jsonify({"status": "started"})
    return jsonify({"status": "already_running"})

@app.route('/get_status')
def get_status():
    """获取爬虫状态的路由"""
    messages = []
    while not status_queue.empty():
        message = status_queue.get()
        messages.append(message)
        message_history.append(message)  # 添加到历史记录
    
    if messages:  # 如果有新消息，保存历史记录
        save_messages()
        
    return jsonify({
        "messages": messages,
        "is_crawling": is_crawling,
        "history": message_history  # 返回完整历史
    })

@app.route('/analyze')
def analyze():
    """分析数据的路由"""
    global word_vectors
    try:
        # 检查数据文件是否存在
        if not os.path.exists('bilibili_videos.json'):
            return jsonify({
                "status": "error",
                "message": "未找到数据文件，请先爬取数据"
            })

        # 检查词向量模型是否已加载
        if word_vectors is None:
            if model_loading_error:
                return jsonify({
                    "status": "error",
                    "message": f"词向量模型加载失败: {model_loading_error}"
                })
            return jsonify({
                "status": "error",
                "message": "词向量模型正在加载中，请稍后再试"
            })

        # 读取数据文件
        with open('bilibili_videos.json', 'r', encoding='utf-8') as f:
            videos = json.load(f)
            
        if not videos:
            return jsonify({
                "status": "error",
                "message": "数据文件为空，请重新爬取数据"
            })

        # 创建分析器实例时传入已加载的词向量模型
        analyzer = BilibiliAnalyzer(status_queue=status_queue, word_vectors=word_vectors)
        profile = analyzer.generate_user_profile()
        return jsonify({
            "status": "success",
            "data": profile
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"分析数据时出错: {str(e)}"
        })

# 添加新的路由来保存分析结果
@app.route('/save_analysis', methods=['POST'])
def save_analysis():
    """保存分析结果"""
    try:
        data = request.json
        # 将分析结果添加到消息历史
        message_history.append({
            "type": "analysis_result",
            "data": data
        })
        save_messages()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })

# 添加新的路由用于实时分析
@app.route('/analyze_current')
def analyze_current():
    """分析当前已爬取的数据"""
    global word_vectors
    try:
        # 检查词向量模型是否已加载
        if word_vectors is None:
            if model_loading_error:
                return jsonify({
                    "status": "error",
                    "message": f"词向量模型加载失败: {model_loading_error}"
                })
            return jsonify({
                "status": "error",
                "message": "词向量模型正在加载中，请稍后再试"
            })

        # 读取当前数据文件
        try:
            with open('bilibili_videos.json', 'r', encoding='utf-8') as f:
                videos = json.load(f)
                
            if videos:
                # 创建分析器实例并分析当前数据
                analyzer = BilibiliAnalyzer(status_queue=status_queue, word_vectors=word_vectors)
                profile = analyzer.generate_user_profile()
                return jsonify({
                    "status": "success",
                    "data": profile,
                    "video_count": len(videos)
                })
            else:
                return jsonify({
                    "status": "waiting",
                    "message": "等待数据收集..."
                })
        except FileNotFoundError:
            # 文件不存在时返回等待状态而不是错误
            return jsonify({
                "status": "waiting",
                "message": "等待数据收集..."
            })
        except json.JSONDecodeError:
            # JSON解析错误时返回等待状态
            return jsonify({
                "status": "waiting",
                "message": "数据文件正在写入中..."
            })
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"分析数据时出错: {str(e)}"
        })

# 添加路由来访问 JSON 文件
@app.route('/bilibili_videos.json')
def get_videos_json():
    """提供视频数据 JSON 文件的访问"""
    try:
        return send_file('bilibili_videos.json', mimetype='application/json')
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"无法读取数据文件: {str(e)}"
        }), 404

if __name__ == '__main__':
    app.run(debug=True) 
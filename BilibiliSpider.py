# Generated by Selenium IDE
import time
import json
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from queue import Queue

class Bilibili():
    def __init__(self, num=100, status_queue=None):
        # 無頭模式
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        self.driver = webdriver.Chrome(options=chrome_options)
        self.vars = {}
        self.status_queue = status_queue
        self.num = num
    
    def teardown_method(self, method):
        self.driver.quit()
    
    def send_status(self, message):
        """发送状态消息"""
        if self.status_queue:
            self.status_queue.put(message)
        print(message if isinstance(message, str) else message.get('data', ''))
    
    def check_login(self):
        """检查是否已登录"""
        try:
            # 减少等待时间到2秒
            wait = WebDriverWait(self.driver, 1)
            # 常见登录检测选择器
            login_selectors = [
                (By.CLASS_NAME, "bili-avatar-icon"),
                (By.CLASS_NAME, "header-avatar-wrap")
            ]
            
            for selector in login_selectors:
                try:
                    element = wait.until(EC.presence_of_element_located(selector))
                    if element.is_displayed():
                        print(f"已检测到登录状态 (通过选择器: {selector})")
                        return True
                except:
                    continue
                    
            print("未检测到登录状态，即将跳转到登录页面...")
            return False
        except Exception as e:
            print(f"登录检测出错: {str(e)}")
            return False
    
    def login(self):
        """执行登录流程"""
        self.send_status("开始登录流程...")
        # 访问登录页面
        self.driver.get("https://passport.bilibili.com/login")
        time.sleep(0.1)

        # 获取二维码图片的base64数据
        html = self.driver.page_source
        pattern = r'data:image/png;base64,([^"]+)'
        match = re.search(pattern, html)

        if match:
            base64_data = match.group(1)
            # 将base64数据存储起来供网页使用
            self.qr_code = f"data:image/png;base64,{base64_data}"
            self.send_status({"type": "qr_code", "data": self.qr_code})
            
            self.send_status({"type": "message", "data": "请使用B站手机APP扫描二维码登录"})

            # 等待扫码登录
            login_wait_time = 0
            max_wait_time = 60  # 最大等待60秒
            
            while login_wait_time < max_wait_time:
                try:
                    # 检查是否登录成功
                    if self.check_login():
                        self.send_status({"type": "message", "data": "登录成功！"})
                        # 额外等待确保登录状态完全加载
                        time.sleep(0.3)
                        # 刷新页面
                        self.driver.refresh()
                        return True
                    time.sleep(2)
                    login_wait_time += 2
                    self.send_status({"type": "message", "data": f"等待登录中... ({login_wait_time}秒)"})
                except:
                    continue
                    
            self.send_status({"type": "message", "data": "登录等待超时"})
            return False
        else:
            self.send_status({"type": "message", "data": "未找到二维码数据"})
            raise Exception("登录失败：未找到二维码")
    
    def scroll_and_collect(self):
        """边滚动边收集数据，使用更快的滚动方式"""
        try:
            window_height = self.driver.execute_script("return window.innerHeight")
            scroll_pause_time = 0.1
            scroll_step = window_height * 2
            
            # 添加最大滚动次数限制，确保能收集足够的视频
            max_scrolls = 200  # 增加最大滚动次数
            scroll_count = 0
            
            scroll_script = """
            window.scrollTo({
                top: arguments[0],
                behavior: 'instant'
            });
            return document.documentElement.scrollHeight;
            """
            
            last_height = 0
            current_position = 0
            no_new_content_count = 0
            
            while scroll_count < max_scrolls:
                current_position += scroll_step
                new_height = self.driver.execute_script(scroll_script, current_position)
                
                video_cards = self.driver.find_elements(By.CSS_SELECTOR, ".bili-video-card.is-rcmd:not([data-processed='true'])")
                
                if video_cards:
                    self.driver.execute_script("""
                        arguments[0].forEach(card => {
                            card.setAttribute('data-processed', 'true');
                        });
                    """, video_cards)
                    
                    yield video_cards
                    no_new_content_count = 0
                else:
                    no_new_content_count += 1
                    if no_new_content_count > 5:  # 如果连续5次没有新内容，多等待一下
                        time.sleep(0.5)
                        no_new_content_count = 0
                
                if new_height == last_height:
                    # 如果页面高度没有变化，尝试多滚动几次
                    current_position += window_height * 3
                
                last_height = new_height
                scroll_count += 1
                time.sleep(scroll_pause_time)
                
        except Exception as e:
            print(f"滚动过程中出错: {str(e)}")
    
    def bilibili(self):
        self.send_status({"type": "message", "data": "开始爬取..."})
        self.driver.get("https://www.bilibili.com/")
        
        if not self.check_login():
            self.send_status({"type": "message", "data": "需要登录，跳转到登录页面..."})
            self.driver.get("https://passport.bilibili.com/login")
            time.sleep(0.3)
            
            if not self.login():
                raise Exception("登录失败，程序退出")
        
        videos_info = []
        processed_titles = set()
        self.send_status({"type": "message", "data": "开始收集视频信息..."})
        
        try:
            for video_cards in self.scroll_and_collect():
                new_videos = []
                for card in video_cards:
                    try:
                        title = card.find_element(By.CSS_SELECTOR, ".bili-video-card__info--tit").get_attribute("title")
                        link = card.find_element(By.CSS_SELECTOR, ".bili-video-card__wrap a").get_attribute("href")
                  
                        if title not in processed_titles:
                            if link is None:
                                print(f"警告: 视频 '{title}' 的链接为None，跳过此视频")
                                continue
                            
                            # 获取UP主信息和主页链接
                            up_element = card.find_element(By.CSS_SELECTOR, ".bili-video-card__info--owner")
                            up_link = up_element.get_attribute("href") if up_element else None
                            up_name = card.find_element(By.CSS_SELECTOR, ".bili-video-card__info--author").text if card.find_elements(By.CSS_SELECTOR, ".bili-video-card__info--author") else "未知"
                            print(f"作者链接：{up_link}")
                            video_info = {
                                "title": title,
                                "thumbnail": card.find_element(By.CSS_SELECTOR, ".bili-video-card__cover img").get_attribute("src"),
                                "link": link,
                                "up_name": up_name,
                                "up_link": up_link,  # 添加UP主主页链接
                                "play_count": card.find_element(By.CSS_SELECTOR, ".bili-video-card__stats--item").text if card.find_elements(By.CSS_SELECTOR, ".bili-video-card__stats--item") else "未知"
                            }
                            new_videos.append(video_info)
                            
                            # 每次添加新视频后，立即保存当前数据
                            valid_videos = [video for video in videos_info if video["link"] is not None and not video["link"].startswith("https://cm.bilibili.com")]
                            with open("bilibili_videos.json", "w", encoding="utf-8") as f:
                                json.dump(valid_videos, f, ensure_ascii=False, indent=2)
                                
                            # 发送进度更新
                            self.send_status({
                                "type": "progress",
                                "data": {
                                    "title": title,
                                    "up_name": up_name,
                                    "current": len(valid_videos),
                                    "total": self.num,
                                    "percentage": round(len(valid_videos) / self.num * 100, 1)
                                }
                            })
                            
                    except Exception as e:
                        self.send_status({"type": "message", "data": f"处理视频卡片出错: {str(e)}"})
                        continue
                
                # 过滤掉广告链接
                filtered_videos = []
                for video in new_videos:
                    if video["link"] is None:
                        print(f"警告: 发现link为None的视频，标题为: {video['title']}")
                        continue
                    if not video["link"].startswith("https://cm.bilibili.com"):
                        filtered_videos.append(video)
                    else:
                        print(f"过滤掉广告视频: {video['title']}")
                
                # 批量更新处理过的标题
                processed_titles.update(video["title"] for video in filtered_videos)
                videos_info.extend(filtered_videos)
                
                # 更新进度信息
                valid_count = len([v for v in videos_info if not v["link"].startswith("https://cm.bilibili.com")])
                self.send_status({
                    "type": "progress",
                    "data": {
                        "current": valid_count,
                        "total": self.num,
                        "percentage": round(valid_count / self.num * 100, 1)
                    }
                })
                
                if valid_count >= self.num:
                    self.send_status({"type": "message", "data": "已达到"+str(self.num)+"个有效视频，停止收集"})
                    break
                    
        except Exception as e:
            self.send_status({"type": "message", "data": f"爬取过程出错: {str(e)}"})
        
        # 最后一次保存（可以删除，因为已经在循环中实时保存了）
        try:
            valid_videos = [video for video in videos_info if video["link"] is not None and not video["link"].startswith("https://cm.bilibili.com")]
            
            with open("bilibili_videos.json", "w", encoding="utf-8") as f:
                json.dump(valid_videos[:self.num], f, ensure_ascii=False, indent=2)
            
            self.send_status({"type": "message", "data": f"爬取完成！成功收集{len(valid_videos)}个有效视频"})
            self.send_status({"type": "message", "data": "数据已保存到 bilibili_videos.json"})
        except Exception as e:
            self.send_status({"type": "message", "data": f"保存数据时出错: {str(e)}"})

# 添加以下代码来运行测试
if __name__ == "__main__":
    try:
        BiliSpider = Bilibili()
        BiliSpider.setup_method(None)
        BiliSpider.bilibili()
    finally:
        BiliSpider.teardown_method(None)
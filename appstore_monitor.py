import requests
import time
import logging
import os
import sys
import json
from datetime import datetime, timezone, timedelta

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 配置参数
COUNTRY_CODE = "cn"  # 中国区
FANGTANG_KEY = os.environ.get("FANGTANG_KEY", "")  # 从环境变量获取方糖 KEY
APP_INFO_FILE = "app_info.json"  # 应用信息 JSON 文件

def load_app_info():
    """从 JSON 文件加载应用信息"""
    try:
        with open(APP_INFO_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"加载应用信息文件失败: {str(e)}")
        return []

def get_app_info(app_id: str, default_name: str) -> dict:
    """通过 App ID 获取应用信息"""
    try:
        params = {"id": app_id, "country": COUNTRY_CODE}
        response = requests.get("https://itunes.apple.com/lookup", params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data["resultCount"] > 0:
            result = data["results"][0]
            return {
                "status": "online",
                "name": result.get("trackName", default_name),
                "version": result.get("version", "未知"),
                "price": result.get("formattedPrice", "未知"),
                "url": result.get("trackViewUrl", "")
            }
        return {"status": "offline", "name": default_name}
    
    except Exception as e:
        logging.error(f"查询 {app_id} 失败: {str(e)}")
        return {"status": "error", "name": default_name}

def send_to_fangtang(title, content, short):
    """发送消息到方糖"""
    if not FANGTANG_KEY:
        logging.warning("未设置方糖 KEY，跳过推送")
        return False
    
    try:
        url = f"https://sctapi.ftqq.com/{FANGTANG_KEY}.send"
        data = {
            "title": title,
            "desp": content,
            "short": short
        }
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if result.get("code") == 0:
            logging.info("方糖推送成功")
            return True
        else:
            logging.error(f"方糖推送失败: {result.get('message', '未知错误')}")
            return False
    
    except Exception as e:
        logging.error(f"方糖推送异常: {str(e)}")
        return False

def get_china_time():
    """获取中国时间"""
    # 获取当前 UTC 时间
    utc_now = datetime.now(timezone.utc)
    # 转换为中国时间 (UTC+8)
    china_now = utc_now + timedelta(hours=8)
    return china_now

def is_within_time_range():
    """检查当前是否在中国时间 8:00-22:00 范围内"""
    # 获取中国时间
    china_now = get_china_time()
    # 提取小时
    hour = china_now.hour
    # 检查是否在 8-22 点之间
    return 8 <= hour < 22

def format_app_detail(info, app_id):
    """格式化应用详细信息"""
    status_icon = "✅" if info["status"] == "online" else "🚫" if info["status"] == "offline" else "❌"
    
    # 简洁格式，只显示状态、ID和名称
    return f"{status_icon} **{info['name']}** (ID: {app_id})"

def monitor(force_send=False):
    """执行监控任务"""
    # 如果不是强制发送且不在时间范围内，则跳过
    if not force_send and not is_within_time_range():
        logging.info("当前不在推送时间范围内 (中国时间 8:00-22:00)")
        return
    
    logging.info("开始检查应用状态")
    
    # 加载应用信息
    app_info = load_app_info()
    if not app_info:
        logging.error("没有找到应用信息，请检查 app_info.json 文件")
        return
    
    # 构建消息内容
    online_apps = []
    offline_apps = []
    error_apps = []
    
    for app in app_info:
        app_id = app["id"]
        default_name = app["name"]
        info = get_app_info(app_id, default_name)
        
        if info["status"] == "online":
            online_apps.append(format_app_detail(info, app_id))
            logging.info(f"✅ [ID: {app_id}] 名称: {info['name']}")
        elif info["status"] == "offline":
            offline_apps.append(format_app_detail(info, app_id))
            logging.warning(f"🚨 [ID: {app_id}] 应用已下架！名称: {info['name']}")
        else:
            error_apps.append(format_app_detail(info, app_id))
            logging.error(f"❌ [ID: {app_id}] 查询异常，名称: {info['name']}")
    
    # 获取中国时间并格式化
    china_time = get_china_time()
    time_str = china_time.strftime('%H:%M')
    
    # 构建推送内容
    title = f"AppStore 监控报告 - {time_str} (中国时间)"
    
    # 构建简洁的消息内容，确保每个应用单独一行
    content = ""
    
    if online_apps:
        content += "## 📱 在线应用\n\n"
        # 每个应用单独一行，并在每个应用后添加两个换行符
        for app in online_apps:
            content += f"{app}\n\n"
    
    if offline_apps:
        content += "## 🚫 已下架应用\n\n"
        # 每个应用单独一行，并在每个应用后添加两个换行符
        for app in offline_apps:
            content += f"{app}\n\n"
    
    if error_apps:
        content += "## ❌ 查询异常\n\n"
        # 每个应用单独一行，并在每个应用后添加两个换行符
        for app in error_apps:
            content += f"{app}\n\n"
    
    # 构建消息卡片内容
    online_count = len(online_apps)
    offline_count = len(offline_apps)
    error_count = len(error_apps)
    
    short = f"在线: {online_count} | 下架: {offline_count}"
    if error_count > 0:
        short += f" | 异常: {error_count}"
    
    # 发送到方糖
    send_to_fangtang(title, content, short)
    logging.info("本轮检查完成")

if __name__ == "__main__":
    # 检查是否有命令行参数
    force_send = len(sys.argv) > 1 and sys.argv[1] == "--force"
    monitor(force_send)
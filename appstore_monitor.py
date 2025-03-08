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
DEFAULT_COUNTRY = "cn"  # Default country if not specified
FANGTANG_KEY = os.environ.get("FANGTANG_KEY", "")  # 从环境变量获取方糖 KEY
APP_INFO_FILE = "app_info.json"  # 应用信息 JSON 文件
STATUS_FILE = "app_status.json"  # 应用状态记录文件

def load_app_info():
    """从 JSON 文件加载应用信息"""
    try:
        with open(APP_INFO_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Handle different format versions
        if isinstance(data, list):
            # New array format - each app has its own countries array
            return data
        elif isinstance(data, dict) and "apps" in data:
            # Old format with default_country - convert to new format
            default_country = data.get("default_country", DEFAULT_COUNTRY)
            new_format = []
            
            for app in data["apps"]:
                # If app has country property, use it, otherwise use default
                countries = [app.get("country", default_country)]
                new_app = {
                    "id": app["id"],
                    "name": app["name"],
                    "countries": countries
                }
                new_format.append(new_app)
            
            return new_format
        else:
            logging.error("未知的应用信息格式")
            return []
    except Exception as e:
        logging.error(f"加载应用信息文件失败: {str(e)}")
        return []

def load_app_status():
    """加载上次的应用状态"""
    try:
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                status_data = json.load(f)
            
            # Check if we need to migrate from old format to new format
            # Old format used app_id as key, new format uses app_id_country
            needs_migration = True
            for key in status_data:
                if '_' in key:  # New format already has compound keys with underscore
                    needs_migration = False
                    break
            
            if needs_migration:
                logging.info("检测到旧格式的状态文件，进行自动迁移...")
                migrated_data = {}
                
                # Get the current app configuration for country info
                app_info = load_app_info()
                app_country_map = {}
                
                # Build a mapping of app_id to countries
                for app in app_info:
                    app_id = app["id"]
                    countries = app.get("countries", [DEFAULT_COUNTRY])
                    app_country_map[app_id] = countries
                
                # Convert each app status to the new format
                for app_id, status in status_data.items():
                    # If app exists in current config, use its countries, otherwise default to "cn"
                    countries = app_country_map.get(app_id, [DEFAULT_COUNTRY])
                    
                    for country in countries:
                        new_key = f"{app_id}_{country}"
                        migrated_data[new_key] = {
                            "status": status.get("status", "unknown"),
                            "name": status.get("name", "Unknown App"),
                            "country": country,
                            "app_id": app_id,
                            "last_check": status.get("last_check", "未检查")
                        }
                
                # Save the migrated data
                with open(STATUS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(migrated_data, f, ensure_ascii=False, indent=2)
                logging.info("状态文件迁移完成")
                
                return migrated_data
            
            return status_data
        # 如果文件不存在，创建一个初始状态文件
        else:
            logging.info(f"状态文件 {STATUS_FILE} 不存在，将创建初始状态文件")
            create_initial_status_file()
            with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"加载应用状态文件失败: {str(e)}")
        return {}

def create_initial_status_file():
    """创建初始状态文件"""
    try:
        app_info = load_app_info()
        initial_status = {}
        
        for app in app_info:
            app_id = app["id"]
            app_name = app["name"]
            countries = app.get("countries", [DEFAULT_COUNTRY])
            
            # 为每个应用的每个国家/地区创建状态
            for country in countries:
                status_key = f"{app_id}_{country}"
                initial_status[status_key] = {
                    "status": "unknown",  # 初始状态为未知
                    "name": app_name,
                    "country": country,
                    "app_id": app_id,
                    "last_check": "未检查"
                }
        
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(initial_status, f, ensure_ascii=False, indent=2)
        logging.info(f"已创建初始状态文件 {STATUS_FILE}")
    except Exception as e:
        logging.error(f"创建初始状态文件失败: {str(e)}")

def save_app_status(status_dict):
    """保存应用状态"""
    try:
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(status_dict, f, ensure_ascii=False, indent=2)
        logging.info("应用状态已保存")
    except Exception as e:
        logging.error(f"保存应用状态失败: {str(e)}")

def get_app_info(app_id: str, default_name: str, country_code: str = DEFAULT_COUNTRY) -> dict:
    """通过 App ID 获取应用信息"""
    try:
        params = {"id": app_id, "country": country_code}
        logging.info(f"查询应用 ID: {app_id}, 国家/地区: {country_code}")
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
                "url": result.get("trackViewUrl", ""),
                "country": country_code,
                "app_id": app_id
            }
        return {"status": "offline", "name": default_name, "country": country_code, "app_id": app_id}
    
    except Exception as e:
        logging.error(f"查询 {app_id} (国家/地区: {country_code}) 失败: {str(e)}")
        return {"status": "error", "name": default_name, "country": country_code, "app_id": app_id}

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

def format_app_detail(info):
    """格式化应用详细信息"""
    status_icon = "✅" if info["status"] == "online" else "🚫" if info["status"] == "offline" else "❌"
    
    country = info["country"].upper()
    app_id = info["app_id"]
    
    # 简洁格式，显示状态、ID、名称和国家/地区
    return f"{status_icon} **{info['name']}** (ID: {app_id}, 区域: {country})"

def send_offline_alert(newly_offline_apps):
    """发送应用下架警告"""
    if not newly_offline_apps:
        return
    
    # 获取中国时间并格式化
    china_time = get_china_time()
    time_str = china_time.strftime('%H:%M')
    
    # 构建警告标题和内容
    title = f"⚠️ 应用下架警告 - {time_str} (中国时间)"
    content = "## 🚨 以下应用刚刚下架\n\n"
    
    for app in newly_offline_apps:
        country = app["country"].upper()
        app_id = app["app_id"]
        content += f"🚫 **{app['name']}** (ID: {app_id}, 区域: {country})\n\n"
    
    # 构建消息卡片内容
    short = f"有 {len(newly_offline_apps)} 个应用刚刚下架！"
    
    # 发送到方糖
    send_to_fangtang(title, content, short)
    logging.warning(f"已发送 {len(newly_offline_apps)} 个应用的下架警告")

def monitor(force_send=False):
    """执行监控任务"""
    # 如果不是强制发送且不在时间范围内，则跳过
    if not force_send and not is_within_time_range():
        logging.info("当前不在推送时间范围内 (中国时间 8:00-22:00)")
        return
    
    logging.info("开始检查应用状态")
    
    # 加载应用信息和上次状态
    app_info = load_app_info()
    if not app_info:
        logging.error("没有找到应用信息，请检查 app_info.json 文件")
        return
    
    previous_status = load_app_status()
    current_status = {}  # 用于保存本次检查的状态
    
    # 构建消息内容
    online_apps = []
    offline_apps = []
    error_apps = []
    newly_offline_apps = []  # 新下架的应用
    
    # 添加区域统计
    region_stats = {
        "cn": {"online": 0, "offline": 0, "error": 0},
        "us": {"online": 0, "offline": 0, "error": 0}
    }
    
    # 遍历每个应用及其指定的国家/地区
    for app in app_info:
        app_id = app["id"]
        default_name = app["name"]
        # 获取应用需要检查的国家/地区列表
        countries = app.get("countries", [DEFAULT_COUNTRY])
        
        for country in countries:
            # 为每个应用+国家组合生成唯一的状态键
            status_key = f"{app_id}_{country}"
            
            # 查询应用状态
            info = get_app_info(app_id, default_name, country)
            
            # 保存当前状态
            current_status[status_key] = {
                "status": info["status"],
                "name": info["name"],
                "country": country,
                "app_id": app_id,
                "last_check": get_china_time().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 检查是否新下架
            if (info["status"] == "offline" and 
                status_key in previous_status and 
                previous_status[status_key].get("status") == "online"):
                newly_offline_apps.append(info)
            
            # 按状态分类
            if info["status"] == "online":
                online_apps.append(format_app_detail(info))
                region_stats[country]["online"] += 1
                logging.info(f"✅ [ID: {app_id}] 名称: {info['name']} 区域: {country.upper()}")
            elif info["status"] == "offline":
                offline_apps.append(format_app_detail(info))
                region_stats[country]["offline"] += 1
                logging.warning(f"🚨 [ID: {app_id}] 应用已下架！名称: {info['name']} 区域: {country.upper()}")
            else:
                error_apps.append(format_app_detail(info))
                region_stats[country]["error"] += 1
                logging.error(f"❌ [ID: {app_id}] 查询异常，名称: {info['name']} 区域: {country.upper()}")
    
    # 保存当前状态
    save_app_status(current_status)
    
    # 如果有新下架的应用，发送警告
    if newly_offline_apps:
        send_offline_alert(newly_offline_apps)
    
    # 获取中国时间并格式化
    china_time = get_china_time()
    time_str = china_time.strftime('%H:%M')
    
    # 构建推送内容
    title = f"AppStore 监控报告 - {time_str} (中国时间)"
    
    # 添加区域统计信息
    content = "## 📊 区域统计\n\n"
    content += f"🇨🇳 中国区：在线 {region_stats['cn']['online']} 款 | 下架 {region_stats['cn']['offline']} 款"
    if region_stats['cn']['error'] > 0:
        content += f" | 异常 {region_stats['cn']['error']} 款"
    content += "\n\n"
    
    content += f"🇺🇸 美国区：在线 {region_stats['us']['online']} 款 | 下架 {region_stats['us']['offline']} 款"
    if region_stats['us']['error'] > 0:
        content += f" | 异常 {region_stats['us']['error']} 款"
    content += "\n\n"
    
    # 添加应用详细信息
    if online_apps:
        content += "## 📱 在线应用\n\n"
        
        # 按区域分组应用
        cn_apps = [app for app in online_apps if "区域: CN" in app]
        us_apps = [app for app in online_apps if "区域: US" in app]
        
        if cn_apps:
            content += "### 🇨🇳 中国区\n\n"
            for i, app in enumerate(cn_apps, 1):
                content += f"{app}\n\n"
                if i % 5 == 0 and i < len(cn_apps):
                    content += "---\n\n"
        
        if us_apps:
            content += "### 🇺🇸 美国区\n\n"
            for i, app in enumerate(us_apps, 1):
                content += f"{app}\n\n"
                if i % 5 == 0 and i < len(us_apps):
                    content += "---\n\n"
    
    if offline_apps:
        content += "## 🚫 已下架应用\n\n"
        
        # 按区域分组下架应用
        cn_offline = [app for app in offline_apps if "区域: CN" in app]
        us_offline = [app for app in offline_apps if "区域: US" in app]
        
        if cn_offline:
            content += "### 🇨🇳 中国区\n\n"
            for i, app in enumerate(cn_offline, 1):
                content += f"{app}\n\n"
                if i % 5 == 0 and i < len(cn_offline):
                    content += "---\n\n"
        
        if us_offline:
            content += "### 🇺🇸 美国区\n\n"
            for i, app in enumerate(us_offline, 1):
                content += f"{app}\n\n"
                if i % 5 == 0 and i < len(us_offline):
                    content += "---\n\n"

    if error_apps:
        content += "## ❌ 查询异常\n\n"
        
        # 按区域分组异常应用
        cn_error = [app for app in error_apps if "区域: CN" in app]
        us_error = [app for app in error_apps if "区域: US" in app]
        
        if cn_error:
            content += "### 🇨🇳 中国区\n\n"
            for i, app in enumerate(cn_error, 1):
                content += f"{app}\n\n"
                if i % 5 == 0 and i < len(cn_error):
                    content += "---\n\n"
        
        if us_error:
            content += "### 🇺🇸 美国区\n\n"
            for i, app in enumerate(us_error, 1):
                content += f"{app}\n\n"
                if i % 5 == 0 and i < len(us_error):
                    content += "---\n\n"

    # 构建消息卡片内容
    online_count = len(online_apps)
    offline_count = len(offline_apps)
    error_count = len(error_apps)
    
    short = f"CN区在线: {region_stats['cn']['online']} | US区在线: {region_stats['us']['online']}"
    if offline_count > 0:
        short += f" | 下架: {offline_count}"
    if error_count > 0:
        short += f" | 异常: {error_count}"
    
    # 发送到方糖
    send_to_fangtang(title, content, short)
    logging.info("本轮检查完成")

if __name__ == "__main__":
    # 检查是否有命令行参数
    force_send = len(sys.argv) > 1 and sys.argv[1] == "--force"
    monitor(force_send)
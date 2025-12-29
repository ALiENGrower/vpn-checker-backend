import signal
import os
import re
import socket
import ssl
import time
import json
import requests
import base64
import websocket
import shutil
from urllib.parse import unquote
from concurrent.futures import ThreadPoolExecutor

# --- БЛОК ТЕЛЕГРАМ-УВЕДОМЛЕНИЙ ---

def send_telegram_report(message, files=None):
    """Отправляет текстовый отчет и прикрепляет файлы нескольким пользователям."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_ids_str = os.getenv('TELEGRAM_CHAT_ID')
    
    if token and chat_ids_str:
        # Разбиваем строку с ID на список
        chat_ids = [chat.strip() for chat in chat_ids_str.split(',')]
        
        for chat_id in chat_ids:
            try:
                # 1. Отправка текста
                url_msg = f"https://api.telegram.org/bot{token}/sendMessage"
                payload = {
                    "chat_id": chat_id, 
                    "text": message, 
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True
                }
                requests.post(url_msg, json=payload, timeout=10)
                
                # 2. Отправка файлов (если они переданы)
                if files:
                    url_doc = f"https://api.telegram.org/bot{token}/sendDocument"
                    for file_path in files:
                        if os.path.exists(file_path):
                            with open(file_path, 'rb') as f:
                                requests.post(url_doc, data={'chat_id': chat_id}, files={'document': f}, timeout=20)
            except Exception as e:
                print(f"Ошибка отправки для {chat_id}: {e}")

# --- СИСТЕМНЫЕ НАСТРОЙКИ ---

def timeout_handler(signum, frame):
    raise TimeoutError("Превышено время выполнения скрипта")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(300 * 60) # Лимит 5 часов

BASE_DIR = "checked"
FOLDER_RU = os.path.join(BASE_DIR, "RU_Best")
FOLDER_EURO = os.path.join(BASE_DIR, "My_Euro")
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")

GITHUB_REPO = os.getenv('GITHUB_REPOSITORY', 'ALiENGrower/vpn-checker-backend')

TIMEOUT = 5
THREADS = 40
CACHE_HOURS = 12
CHUNK_LIMIT = 300
MAX_KEYS = 15000
socket.setdefaulttimeout(TIMEOUT)

URLS_RU = [
    "https://raw.githubusercontent.com/zieng2/wl/main/vless.txt",
    "https://raw.githubusercontent.com/LowiKLive/BypassWhitelistRu/refs/heads/main/WhiteList-Bypass_Ru.txt",
    "https://raw.githubusercontent.com/zieng2/wl/main/vless_universal.txt",
    "https://raw.githubusercontent.com/vsevjik/OBSpiskov/refs/heads/main/wwh",
    "https://jsnegsukavsos.hb.ru-msk.vkcloud-storage.ru/love",
    "https://etoneya.a9fm.site/1",
    "https://s3c3.001.gpucloud.ru/vahe4xkwi/cjdr"
]

URLS_MY = [
    "https://raw.githubusercontent.com/kort0881/vpn-vless-configs-russia/refs/heads/main/githubmirror/new/all_new.txt"
]

EURO_CODES = {"NL", "DE", "FI", "GB", "FR", "SE", "PL", "CZ", "AT", "CH", "IT", "ES", "NO", "DK", "BE", "IE", "LU", "EE", "LV", "LT"}
BAD_MARKERS = ["CN", "IR", "KR", "BR", "IN", "RELAY", "POOL"]

# --- ФУНКЦИИ ОБРАБОТКИ ---

def get_country_fast(host, key_name):
    host, name = host.lower(), key_name.upper()
    if host.endswith(".ru"): return "RU"
    if host.endswith(".de"): return "DE"
    if host.endswith(".nl"): return "NL"
    for code in EURO_CODES:
        if code in name: return code
    return "UN"

def fetch_keys(urls, tag):
    extracted = []
    for url in urls:
        try:
            r = requests.get(url, timeout=15)
            if r.status_code != 200: continue
            content = r.text.strip()
            
            if "://" not in content:
                try:
                    lines = base64.b64decode(content + "==").decode('utf-8', errors='ignore').splitlines()
                except:
                    lines = content.splitlines()
            else:
                lines = content.splitlines()

            for line in lines:
                line = line.strip()
                if 20 < len(line) < 2500 and line.startswith(("vless://", "vmess://", "trojan://", "ss://")):
                    if tag == "MY":
                        upper_l = line.upper()
                        if any(m in upper_l for m in BAD_MARKERS) or ".ir" in line or ".cn" in line:
                            continue
                    extracted.append((line, tag))
        except:
            continue
    return extracted

def check_single_key(data):
    key, tag = data
    try:
        part = key.split("@")[1].split("?")[0].split("#")[0]
        host, port = part.split(":")[0], int(part.split(":")[1])
        
        country = get_country_fast(host, key)
        if tag == "MY" and country == "RU": return None

        is_tls = any(s in key for s in ['security=tls', 'security=reality', 'trojan://', 'vmess://'])
        is_ws = 'type=ws' in key or 'net=ws' in key
        
        start_time = time.time()
        
        if is_ws:
            path = unquote(re.search(r'path=([^&]+)', key).group(1)) if 'path=' in key else "/"
            ws = websocket.create_connection(f"{'wss' if is_tls else 'ws'}://{host}:{port}{path}", timeout=TIMEOUT, sslopt={"cert_reqs": ssl.CERT_NONE})
            ws.close()
        elif is_tls:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            with socket.create_connection((host, port), timeout=TIMEOUT) as sock:
                with context.wrap_socket(sock, server_hostname=host): pass
        else:
            with socket.create_connection((host, port), timeout=TIMEOUT): pass
            
        latency = int((time.time() - start_time) * 1000)
        return (latency, tag, country)
    except:
        return None

def save_chunked(keys, folder, base_name):
    created = []
    if not keys:
        path = os.path.join(folder, f"{base_name}.txt")
        with open(path, "w") as f: f.write("")
        return [f"{base_name}.txt"]
    
    chunks = [keys[i:i + CHUNK_LIMIT] for i in range(0, len(keys), CHUNK_LIMIT)]
    for i, chunk in enumerate(chunks, 1):
        name = f"{base_name}.txt" if len(chunks) == 1 else f"{base_name}_part{i}.txt"
        with open(os.path.join(folder, name), "w", encoding="utf-8") as f:
            f.write("\n".join(chunk))
        created.append(name)
    return created

# --- ОСНОВНОЙ ЦИКЛ ---

if __name__ == "__main__":
    for f in [FOLDER_RU, FOLDER_EURO]:
        if os.path.exists(f): shutil.rmtree(f)
        os.makedirs(f, exist_ok=True)

    history = {}
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f: history = json.load(f)
        except: pass

    raw_tasks = fetch_keys(URLS_RU, "RU") + fetch_keys(URLS_MY, "MY")
    unique_tasks = list({t[0]: t[1] for t in raw_tasks}.items())[:MAX_KEYS]
    
    now = time.time()
    to_check, final_ru, final_euro = [], [], []

    for key, tag in unique_tasks:
        kid = key.split("#")[0]
        cached = history.get(kid)
        if cached and (now - cached['time'] < CACHE_HOURS * 3600) and cached.get('alive'):
            entry = f"{kid}#{cached['latency']}ms_{cached.get('country','UN')}"
            if tag == "RU": final_ru.append(entry)
            else: final_euro.append(entry)
        else:
            to_check.append((key, tag))

    if to_check:
        with ThreadPoolExecutor(max_workers=THREADS) as executor:
            results = list(executor.map(check_single_key, to_check))
            for i, res in enumerate(results):
                if res:
                    latency, tag, country = res
                    kid = to_check[i][0].split("#")[0]
                    history[kid] = {'alive': True, 'latency': latency, 'time': now, 'country': country}
                    entry = f"{kid}#{latency}ms_{country}"
                    if tag == "RU": final_ru.append(entry)
                    else: final_euro.append(entry)

    history = {k: v for k, v in history.items() if now - v['time'] < 259200}
    with open(HISTORY_FILE, "w") as f: json.dump(history, f, indent=2)

    def get_ms(s):
        try: return int(re.search(r'(\d+)ms', s).group(1))
        except: return 9999

    final_ru.sort(key=get_ms)
    final_euro.sort(key=get_ms)

    ru_files = save_chunked(final_ru, FOLDER_RU, "ru_white")
    euro_files = save_chunked(final_euro, FOLDER_EURO, "my_euro")

    # Генерация списка подписок
    sub_list_path = os.path.join(BASE_DIR, "subscriptions_list.txt")
    base_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{BASE_DIR}"
    sub_text = "=== SUBSCRIPTIONS ===\n"
    for f in ru_files: sub_text += f"{base_url}/RU_Best/{f}\n"
    for f in euro_files: sub_text += f"{base_url}/My_Euro/{f}\n"
    
    with open(sub_list_path, "w", encoding="utf-8") as f:
        f.write(sub_text)

    # ПОДГОТОВКА ОТЧЕТА И ФАЙЛОВ ДЛЯ TG
    files_to_send = [sub_list_path]
    for f in ru_files: files_to_send.append(os.path.join(FOLDER_RU, f))
    for f in euro_files: files_to_send.append(os.path.join(FOLDER_EURO, f))

    msg = (
        f"✅ <b>Система когерентности обновлена</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"🇷🇺 Россия (RU): <code>{len(final_ru)}</code>\n"
        f"🇪🇺 Европа (EURO): <code>{len(final_euro)}</code>\n"
        f"🕒 В базе кэша: {len(history)}\n"
        f"━━━━━━━━━━━━━━\n"
        f"📦 Все файлы прикреплены к отчету."
    )
    
    send_telegram_report(msg, files=files_to_send)
    print("Успех. Отчет отправлен.")

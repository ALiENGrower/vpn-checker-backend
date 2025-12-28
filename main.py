import os
import re
import html
import socket
import ssl
import time
import requests
import base64
import websocket
from datetime import datetime
from urllib.parse import quote, unquote

# ------------------ Настройки ------------------
NEW_KEYS_FOLDER = "checked"
os.makedirs(NEW_KEYS_FOLDER, exist_ok=True)

TIMEOUT = 2   # Таймаут проверки (сек) - быстро и жестко
RETRIES = 1   # 1 попытка

timestamp = datetime.now().strftime("%Y%m%d_%H%M")
LIVE_KEYS_FILE = os.path.join(NEW_KEYS_FOLDER, "live_keys.txt")
LOG_FILE = os.path.join(NEW_KEYS_FOLDER, "log.txt")

MY_CHANNEL = "@vlesstrojan" 

# === СПИСОК ИСТОЧНИКОВ ===
URLS = [
    # 1. ВАШ ОСНОВНОЙ АГРЕГАТОР (где уже "все собрано")
    # (Я поправил ссылку на RAW формат, чтобы скрипт мог её прочитать)
    "https://raw.githubusercontent.com/kort0881/vpn-vless-configs-russia/main/githubmirror/new/all_new.txt",

    # 2. НОВЫЕ ДОПОЛНИТЕЛЬНЫЕ (от ryzgames / zieng)
    "https://raw.githubusercontent.com/zieng2/wl/main/vless.txt",
    "https://raw.githubusercontent.com/LowiKLive/BypassWhitelistRu/refs/heads/main/WhiteList-Bypass_Ru.txt",
    "https://raw.githubusercontent.com/zieng2/wl/main/vless_universal.txt",
    "https://raw.githubusercontent.com/vsevjik/OBSpiskov/refs/heads/main/wwh",
    "https://jsnegsukavsos.hb.ru-msk.vkcloud-storage.ru/love",
    "https://etoneya.a9fm.site/1",
    "https://s3c3.001.gpucloud.ru/vahe4xkwi/cjdr"
]

# ------------------ Функции ------------------

def decode_base64_safe(data):
    """Безопасная декодировка Base64"""
    try:
        data = data.replace('-', '+').replace('_', '/')
        padding = len(data) % 4
        if padding:
            data += '=' * (4 - padding)
        return base64.b64decode(data).decode('utf-8', errors='ignore')
    except:
        return None

def fetch_and_load_keys(urls):
    all_keys = []
    print(f"Загрузка с {len(urls)} источников...")
    
    for url in urls:
        try:
            # Маскируемся под браузер, чтобы ВК/сайты не блочили
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code != 200:
                print(f"[ERROR] {url} -> {resp.status_code}")
                continue
                
            content = resp.text.strip()
            
            # Проверка: если это base64 (нет явных ссылок) -> декодируем
            if "vmess://" not in content and "vless://" not in content:
                decoded = decode_base64_safe(content)
                if decoded:
                    lines = decoded.splitlines()
                else:
                    lines = content.splitlines()
            else:
                lines = content.splitlines()

            count = 0
            for line in lines:
                line = line.strip()
                # Берем только нужные протоколы
                if line.startswith(("vless://", "vmess://", "trojan://", "ss://")):
                    all_keys.append(line)
                    count += 1
            print(f"[OK] {url} -> найдено {count}")
            
        except Exception as e:
            print(f"[FAIL] {url} -> {e}")
            
    return list(set(all_keys)) # Убираем дубликаты

def extract_host_port(key):
    try:
        if "@" in key and ":" in key:
            after_at = key.split("@")[1]
            main_part = re.split(r'[?#]', after_at)[0]
            if ":" in main_part:
                host, port = main_part.split(":")
                return host, int(port)
    except: return None, None
    return None, None

def classify_latency(latency_ms: int) -> str:
    if latency_ms < 500: return "fast"
    if latency_ms < 1500: return "normal"
    return "slow"

def measure_latency(key, host, port, timeout=TIMEOUT):
    """Hybrid Check: WebSocket vs TCP"""
    is_tls = 'security=tls' in key or 'security=reality' in key or 'trojan://' in key or 'vmess://' in key
    is_ws = 'type=ws' in key or 'net=ws' in key
    
    path = "/"
    path_match = re.search(r'path=([^&]+)', key)
    if path_match: path = unquote(path_match.group(1))

    protocol = "wss" if is_tls else "ws"
    
    # WebSocket Check (Priority)
    if is_ws:
        try:
            start = time.time()
            ws_url = f"{protocol}://{host}:{port}{path}"
            ws = websocket.create_connection(ws_url, timeout=timeout, sslopt={"cert_reqs": ssl.CERT_NONE})
            ws.close()
            return int((time.time() - start) * 1000)
        except: return None

    # TLS TCP Check
    if not is_ws and is_tls:
        try:
            start = time.time()
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            with socket.create_connection((host, port), timeout=timeout) as sock:
                with context.wrap_socket(sock, server_hostname=host):
                    pass
            return int((time.time() - start) * 1000)
        except: return None

    # Plain TCP Check
    try:
        start = time.time()
        with socket.create_connection((host, port), timeout=timeout):
            pass
        return int((time.time() - start) * 1000)
    except: return None

def add_comment(key, latency, quality):
    if "#" in key: base, _ = key.split("#", 1)
    else: base = key
    tag = f"{quality}_{latency}ms_{MY_CHANNEL}".replace(" ", "_")
    return f"{base}#{tag}"

# ------------------ Main ------------------
if __name__ == "__main__":
    print("=== START CHECKER ===")
    
    all_keys = fetch_and_load_keys(URLS)
    print(f"Всего уникальных ключей для проверки: {len(all_keys)}")

    valid_count = 0
    
    with open(LIVE_KEYS_FILE, "w", encoding="utf-8") as f_out:
        for i, key in enumerate(all_keys):
            key = html.unescape(key).strip()
            host, port = extract_host_port(key)
            
            if not host: continue
            
            # Лог каждые 50 штук, чтобы в Actions было видно движение
            if i % 50 == 0: print(f"Progress: {i}/{len(all_keys)} checked...")

            latency = measure_latency(key, host, port)
            
            if latency is not None:
                qual = classify_latency(latency)
                final_key = add_comment(key, latency, qual)
                f_out.write(final_key + "\n")
                valid_count += 1

    print(f"=== DONE. Valid keys: {valid_count} ===")
    print(f"Saved to: {LIVE_KEYS_FILE}")





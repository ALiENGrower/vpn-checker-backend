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
from urllib.parse import unquote, quote
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
CHUNK_LIMIT = 6660
MAX_KEYS = 30000
socket.setdefaulttimeout(TIMEOUT)

# Новые константы из main(vpn).py
MAX_PING_MS = 3000
FAST_LIMIT = 3000
MAX_HISTORY_AGE = 2 * 24 * 3600
MY_CHANNEL = "∞"

# Фиксированные имена файлов для FAST слоя
RU_FILES = ["ru_white_part1.txt", "ru_white_part2.txt", "ru_white_part3.txt", "ru_white_part4.txt"]
EURO_FILES = ["my_euro_part1.txt", "my_euro_part2.txt", "my_euro_part3.txt"]

URLS_RU = [
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/Base64/BLACK_SS+All_RUS_base64.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/Base64/BLACK_VLESS_RUS_base64.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/Base64/BLACK_VLESS_RUS_mobile_base64.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/Base64/Vless-Reality-White-Lists-Rus-Mobile-2-base64.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/Base64/Vless-Reality-White-Lists-Rus-Mobile-base64.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/Base64/WHITE-CIDR-RU-all-base64.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/Base64/WHITE-CIDR-RU-checked-base64.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/Base64/WHITE-SNI-RU-all-base64.txt",
    "https://raw.githubusercontent.com/zieng2/wl/main/vless.txt",
    "https://raw.githubusercontent.com/LowiKLive/BypassWhitelistRu/refs/heads/main/WhiteList-Bypass_Ru.txt",
    "https://raw.githubusercontent.com/zieng2/wl/main/vless_universal.txt",
    "https://raw.githubusercontent.com/vsevjik/OBSpiskov/refs/heads/main/wwh",
    "https://jsnegsukavsos.hb.ru-msk.vkcloud-storage.ru/love",
    "https://etoneya.a9fm.site/1",
    "https://s3c3.001.gpucloud.ru/vahe4xkwi/cjdr",
    "https://raw.githubusercontent.com/zieng2/wl/refs/heads/main/vless_universal.txt",
    "https://raw.githubusercontent.com/zieng2/wl/refs/heads/main/vless_lite.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/WHITE-SNI-RU-all.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/WHITE-CIDR-RU-all.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/Vless-Reality-White-Lists-Rus-Mobile-2.txt",
    "https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/refs/heads/main/WHITE-CIDR-RU-checked.txt",
    "https://key.zarazaex.xyz/sub",
    "https://rostunnel.vercel.app/mega.txt",
    "https://subrostunnel.vercel.app/wl.txt",
    "https://subrostunnel.vercel.app/gen.txt",
    "https://etoneya.su/whitelist",
    "https://raw.githubusercontent.com/Kirillo4ka/eavevpn-configs/refs/heads/main/WHITE-CIDR-RU-all.txt",
    "https://raw.githubusercontent.com/Kirillo4ka/eavevpn-configs/refs/heads/main/WHITE-CIDR-RU-checked.txt",
    "https://raw.githubusercontent.com/Kirillo4ka/eavevpn-configs/refs/heads/main/Vless-Reality-White-Lists-Rus-Mobile.txt",
    "https://raw.githubusercontent.com/Kirillo4ka/eavevpn-configs/refs/heads/main/WHITE-SNI-RU-all.txt",
    "https://gist.githubusercontent.com/DestroyST6767/50af50221ca1858ba2084efc0f524fbc/raw/1dc2f8edf8b2d7ab2a85ffd970208aa6fbb65a8e/Destroy_ST%2520%25D0%2591%25D0%25A1",
    "https://gitverse.ru/api/repos/bywarm/rser/raw/branch/master/selected.txt",
    "https://gitverse.ru/api/repos/bywarm/rser/raw/branch/master/wl.txt",
    "https://gitverse.ru/api/repos/bywarm/rser/raw/branch/master/merged.txt",
    "https://raw.githubusercontent.com/Alex999ooo/VPN-for-Russia-/refs/heads/main/VPN%20by%20Alex999ooo%20%F0%9F%8F%B3%EF%B8%8F",
    "https://raw.githubusercontent.com/prominbro/sub/refs/heads/main/212.txt",
    "https://raw.githubusercontent.com/dmitriistekolnikov/Free_vpns_for_Russ/refs/heads/main/Vrema.txt",
    "https://raw.githubusercontent.com/dmitriistekolnikov/Free_vpns_for_Russ/refs/heads/main/Vip.txt",
    "https://raw.githubusercontent.com/Temnuk/naabuzil/refs/heads/main/whitelist_full",
    "https://raw.githubusercontent.com/Temnuk/naabuzil/refs/heads/main/whitelist",
    "https://raw.githubusercontent.com/ksenkovsolo/HardVPN-bypass-WhiteLists-/refs/heads/main/vpn-lte/WHITELIST-ALL.txt",
    "https://raw.githubusercontent.com/ksenkovsolo/HardVPN-bypass-WhiteLists-/refs/heads/main/vpn-lte/subscriptions/1sub.txt",
    "https://raw.githubusercontent.com/ksenkovsolo/HardVPN-bypass-WhiteLists-/refs/heads/main/vpn-lte/subscriptions/2sub.txt",
    "https://raw.githubusercontent.com/ksenkovsolo/HardVPN-bypass-WhiteLists-/refs/heads/main/vpn-lte/subscriptions/3sub.txt",
    "https://raw.githubusercontent.com/ksenkovsolo/HardVPN-bypass-WhiteLists-/refs/heads/main/vpn-lte/subscriptions/4sub.txt",
    "https://raw.githubusercontent.com/ksenkovsolo/HardVPN-bypass-WhiteLists-/refs/heads/main/vpn-lte/subscriptions/5sub.txt",
    "https://raw.githubusercontent.com/ksenkovsolo/HardVPN-bypass-WhiteLists-/refs/heads/main/vpn-lte/best_keys.txt",
    "https://raw.githubusercontent.com/ksenkovsolo/HardVPN-bypass-WhiteLists-/refs/heads/main/vpn-lte/good_keys.txt",
    "https://raw.githubusercontent.com/AirLinkVPN1/AirLinkVPN/refs/heads/main/rkn_white_list",
    "https://raw.githubusercontent.com/Maskkost93/kizyak-vpn-4.0/refs/heads/main/kizyakbeta7.txt",
    "https://raw.githubusercontent.com/Maskkost93/kizyak-vpn-4.0/refs/heads/main/kizyakbeta6.txt",
    "https://raw.githubusercontent.com/Maskkost93/kizyak-vpn-4.0/refs/heads/main/kizyaktestru.txt",
    "https://obwl.vercel.app/configs/configs.txt",
    "https://obwl.vercel.app/configs/selected.txt",
    "https://tinyurl.com/AeryxVPNyandexua",
    "https://raw.githubusercontent.com/VOID-Anonymity/V.O.I.D-VPN_Bypass/refs/heads/main/url_work.txt",
    "https://raw.githubusercontent.com/dequar/deqwl/refs/heads/main/deray.txt",
    "https://tinyurl.com/scalavpnbot",
    "https://raw.githubusercontent.com/kama55726/KomaryServers/refs/heads/main/KomaryServ",
    "https://raw.githubusercontent.com/LimeHi/Old-Context-Menu/refs/heads/main/afg.txt",
    "https://raw.githubusercontent.com/nzea243/ikoV31tud_vpn/refs/heads/main/tri_228.txt",
    "https://raw.githubusercontent.com/mbelspb-gif/gdffgd/refs/heads/main/Swordware.net",
    "https://gist.githubusercontent.com/flaafix/c79a81037d15163360571c7a7331b153/raw/AetrisVPN.txt",
    "https://raw.githubusercontent.com/HalyavusVPNUS/halyava-vpn-lte/refs/heads/main/lte.txt",
]

URLS_MY = [
    "https://raw.githubusercontent.com/kort0881/vpn-vless-configs-russia/refs/heads/main/githubmirror/new/all_new.txt",
    "https://raw.githubusercontent.com/kort0881/vpn-vless-configs-russia/refs/heads/main/githubmirror/clean/vless.txt",
    "https://raw.githubusercontent.com/kort0881/vpn-vless-configs-russia/refs/heads/main/githubmirror/clean/vmess.txt",
    "https://raw.githubusercontent.com/kort0881/vpn-vless-configs-russia/refs/heads/main/githubmirror/clean/trojan.txt",
    "https://raw.githubusercontent.com/kort0881/vpn-vless-configs-russia/refs/heads/main/githubmirror/clean/ss.txt",
    "https://raw.githubusercontent.com/kort0881/vpn-vless-configs-russia/refs/heads/main/githubmirror/clean/hysteria.txt",
    "https://raw.githubusercontent.com/kort0881/vpn-vless-configs-russia/refs/heads/main/githubmirror/clean/hysteria2.txt",
    "https://raw.githubusercontent.com/kort0881/vpn-vless-configs-russia/refs/heads/main/githubmirror/clean/hy2.txt",
    "https://raw.githubusercontent.com/kort0881/vpn-vless-configs-russia/refs/heads/main/githubmirror/clean/tuic.txt",
    "https://tinyurl.com/freesub-scalavpnrobot",
    "https://raw.githubusercontent.com/Ilyacom4ik/free-v2ray-2026/refs/heads/main/subscriptions/FreeCFGHub1.txt",
    "https://raw.githubusercontent.com/uretkavpn/Uretkavpn/refs/heads/main/UretkaVpn.txt",
    "https://gist.githubusercontent.com/FrizanGAME/dfd1f7ac36511593dc6d0faff14cc8bb/raw/frizanVPN.txt",
    "https://raw.githubusercontent.com/Ilyacom4ik/vpn-keys/refs/heads/main/allkeysFreeCFGHub.txt",
    "https://raw.githubusercontent.com/likzil/vless1/refs/heads/main/Treetcpvpn",
    "https://raw.githubusercontent.com/Ilyacom4ik/vpn-keys/refs/heads/main/FreeCFGHubSUB",
    "https://raw.githubusercontent.com/RKPchannel/RKP_bypass_configs/refs/heads/main/whitelist.txt",
    "https://tinyurl.com/AeryxWiFiLTE",
    "https://tinyurl.com/5cnvrkmy",
    "https://tinyurl.com/3mzxa6k6",
    "https://tinyurl.com/Sub1EggAeryx",
    "https://raw.githubusercontent.com/Ghost-LInk-star/GhostL/refs/heads/main/dizzga.txt",
    "https://raw.githubusercontent.com/mbelspb-gif/bright/refs/heads/main/Kdlddl.sw",
    "https://raw.githubusercontent.com/Ghost-LInk-star/bambuk/refs/heads/main/vpn.txt",
    "https://gist.githubusercontent.com/nikitavalentinov90021-ai/b5f135a9547a559f8042cfc7c7cde32d/raw/3d454f959d5f4a2c37c47a5d4d9bd4c798506cea/LTE8464552823",
    "https://gist.githubusercontent.com/pidarasuebisov-afk/e220b44264242d1a97c0908aba091edd/raw/PKN%20cocnyL",
    "https://raw.githubusercontent.com/dmitriistekolnikov/Free_vpns_for_Russ/refs/heads/main/Vpn.txt",
    "https://gist.githubusercontent.com/nikitavalentinov90021-ai/a4de8e24121096a7714be35465849a0c/raw/995e0ee28983e89e3dab94d9e80834514bd212c1/ID6592823693.txt",
    "https://gist.githubusercontent.com/nikitavalentinov90021-ai/41901f30db6c78a6a4d0da27429f4fab/raw/6efae398be2ad0ab70ba257bab20a82053c36383/LTE.txt",
    "https://gist.githubusercontent.com/VSPBOOST/d84dcf89bf31012a96ee60a9eb73b852/raw/4f6af123b4a0251806b89958c845666268283c5a/gistfile1.txt",
    "https://gitverse.ru/api/repos/cid-uskoritel/cid-white/raw/branch/master/whitelist(beta).txt",
    "https://raw.githubusercontent.com/ByeWhiteLists/ByeWhiteLists2/refs/heads/main/ByeWhiteLists2.txt",
    "https://raw.githubusercontent.com/RYZgames31/UWB/refs/heads/main/wcfg",
    "https://raw.githubusercontent.com/twinkalex1470-crypto/CatWhiteVPN/refs/heads/main/CaTWhiteVPN.txt",
    "https://raw.githubusercontent.com/DarkFirexs/Whitelist-bypass_VPN/refs/heads/main/Whitelist%20%7C%20VPN",
    "https://raw.githubusercontent.com/stanislavPLS/AuraChannel/refs/heads/main/ID%3D1%2Cdata%3D280427",
    "https://raw.githubusercontent.com/stanislavPLS/GMVPN-users/refs/heads/main/id%3D1%2Cdata%3D120527",
    "https://gitverse.ru/api/repos/cid-uskoritel/cid-white/raw/branch/master/whitelist.txt",
    "https://sub.obbhod.online/premium",
    "http://194.33.61.236:8080/premium",
    "https://raw.githubusercontent.com/Ilyacom4ik/free-v2ray-2026/refs/heads/main/subscriptions/whitelist-keys.txt",
    "http://144.31.165.198:8080/premium",
    "https://raw.githubusercontent.com/kama55726/KomaryServers/main/White-List-2"
]

EURO_CODES = {"NL", "DE", "FI", "GB", "FR", "SE", "PL", "CZ", "AT", "CH", "IT", "ES", "NO", "DK", "BE", "IE", "LU", "EE", "LV", "LT"}
BAD_MARKERS = ["CN", "IR", "KR", "BR", "IN", "RELAY", "POOL", "🇨🇳", "🇮🇷", "🇰🇷"]

# --- Жёсткий фильтр русских выходных серверов ---

RU_MARKERS_STRICT = [
    ".ru", "moscow", "msk", "spb", "saint-peter", "russia",
    "россия", "москва", "питер", "ru-", "-ru.",
    "178.154.", "77.88.", "5.255.", "87.250.",
    "95.108.", "213.180.", "195.208.",
    "91.108.", "149.154.",
]

# --- ФУНКЦИИ ОБРАБОТКИ ---

def load_json(path):
    """Загружает JSON файл."""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_json(path, data):
    """Сохраняет данные в JSON файл."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

def is_russian_exit(key_str, host, country):
    """Проверяет, является ли сервер русским."""
    if country == "RU":
        return True
    host_lower = host.lower()
    key_upper = key_str.upper()
    if host_lower.endswith(".ru"):
        return True
    for marker in RU_MARKERS_STRICT:
        if marker.lower() in host_lower:
            return True
        if marker.upper() in key_upper:
            return True
    return False

def is_garbage_text(key_str):
    """Проверяет ключ на наличие мусорных маркеров."""
    upper = key_str.upper()
    for m in BAD_MARKERS:
        if m in upper:
            return True
    if ".ir" in key_str or ".cn" in key_str or "127.0.0.1" in key_str:
        return True
    return False

def get_country_fast(host, key_name):
    """Быстрое определение страны по хосту и имени ключа."""
    try:
        host = host.lower()
        name = key_name.upper()
        if host.endswith(".ru"):
            return "RU"
        if host.endswith(".de"):
            return "DE"
        if host.endswith(".nl"):
            return "NL"
        if host.endswith(".uk") or host.endswith(".co.uk"):
            return "GB"
        if host.endswith(".fr"):
            return "FR"
        for code in EURO_CODES:
            if code in name:
                return code
    except:
        pass
    return "UN"

def fetch_keys(urls, tag):
    """Извлекает ключи из списка URL."""
    extracted = []
    for url in urls:
        try:
            # Конвертация github blob в raw
            if "github.com" in url and "/blob/" in url:
                url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")

            r = requests.get(url, timeout=15)
            if r.status_code != 200:
                continue
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
                if len(line) > 2000:
                    continue
                if 20 < len(line) < 2500 and line.startswith(("vless://", "vmess://", "trojan://", "ss://")):
                    if tag == "MY":
                        if is_garbage_text(line):
                            continue
                        upper_l = line.upper()
                        if any(m in upper_l for m in BAD_MARKERS) or ".ir" in line or ".cn" in line:
                            continue
                    extracted.append((line, tag))
        except:
            continue
    return extracted

def check_single_key(data):
    """Проверяет один ключ на работоспособность."""
    key, tag = data
    try:
        if "@" in key and ":" in key:
            part = key.split("@")[1].split("?")[0].split("#")[0]
            host, port = part.split(":")[0], int(part.split(":")[1])
        else:
            return None, None, None, None

        country = get_country_fast(host, key)

        if tag == "MY" and country == "RU":
            return None, None, None, None

        is_tls = any(s in key for s in ['security=tls', 'security=reality', 'trojan://', 'vmess://'])
        is_ws = 'type=ws' in key or 'net=ws' in key

        path = "/"
        match = re.search(r'path=([^&]+)', key)
        if match:
            path = unquote(match.group(1))

        start_time = time.time()

        if is_ws:
            protocol = "wss" if is_tls else "ws"
            ws_url = f"{protocol}://{host}:{port}{path}"
            ws = websocket.create_connection(
                ws_url,
                timeout=TIMEOUT,
                sslopt={"cert_reqs": ssl.CERT_NONE},
                sockopt=((socket.SOL_SOCKET, socket.SO_RCVTIMEO, TIMEOUT),)
            )
            ws.close()
        elif is_tls:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            with socket.create_connection((host, port), timeout=TIMEOUT) as sock:
                with context.wrap_socket(sock, server_hostname=host):
                    pass
        else:
            with socket.create_connection((host, port), timeout=TIMEOUT):
                pass

        latency = int((time.time() - start_time) * 1000)
        return latency, tag, country, host
    except:
        return None, None, None, None

def make_final_key(k_id, latency, country):
    """Создаёт финальный ключ с меткой."""
    info_str = f"[{latency}ms {country} {MY_CHANNEL}]"
    label_encoded = quote(info_str, safe='')
    return f"{k_id}#{label_encoded}"

def extract_ping(key_str):
    """Извлекает значение пинга из ключа."""
    try:
        decoded = unquote(key_str)
        label = decoded.split("#")[-1]
        match = re.search(r'(\d+)ms', label)
        if match:
            return int(match.group(1))
        return None
    except:
        return None

def save_exact(keys, folder, filename):
    """Сохраняет ключи в файл точно."""
    path = os.path.join(folder, filename)
    valid_keys = [k.strip() for k in keys if k and k.strip()]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(valid_keys) if valid_keys else "")
    return path

def save_fixed_chunks_ru(keys_list, folder):
    """Сохраняет RU ключи в фиксированные файлы."""
    valid_keys = [k.strip() for k in keys_list if k and k.strip()]
    chunks = [valid_keys[i:i + CHUNK_LIMIT] for i in range(0, min(len(valid_keys), CHUNK_LIMIT * 4), CHUNK_LIMIT)]
    while len(chunks) < 4:
        chunks.append([])
    for i, filename in enumerate(RU_FILES):
        save_exact(chunks[i] if i < len(chunks) else [], folder, filename)
        count = len(chunks[i]) if i < len(chunks) else 0
        print(f"  {filename}: {count} ключей")
    return RU_FILES

def save_fixed_chunks_euro(keys_list, folder):
    """Сохраняет EURO ключи в фиксированные файлы."""
    valid_keys = [k.strip() for k in keys_list if k and k.strip()]
    chunks = [valid_keys[i:i + CHUNK_LIMIT] for i in range(0, min(len(valid_keys), CHUNK_LIMIT * 3), CHUNK_LIMIT)]
    while len(chunks) < 3:
        chunks.append([])
    for i, filename in enumerate(EURO_FILES):
        save_exact(chunks[i] if i < len(chunks) else [], folder, filename)
        count = len(chunks[i]) if i < len(chunks) else 0
        print(f"  {filename}: {count} ключей")
    return EURO_FILES

def save_chunked(keys, folder, base_name, chunk_size=None):
    """Сохраняет ключи в чанки."""
    if chunk_size is None:
        chunk_size = CHUNK_LIMIT

    valid_keys = [k.strip() for k in keys if k and k.strip()]
    if not valid_keys:
        path = os.path.join(folder, f"{base_name}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("")
        return [f"{base_name}.txt"]

    chunks = [valid_keys[i:i + chunk_size] for i in range(0, len(valid_keys), chunk_size)]
    created = []
    for idx, chunk in enumerate(chunks, 1):
        name = f"{base_name}.txt" if len(chunks) == 1 else f"{base_name}_part{idx}.txt"
        with open(os.path.join(folder, name), "w", encoding="utf-8") as f:
            f.write("\n".join(chunk))
        created.append(name)
        print(f"  {name}: {len(chunk)} ключей")
    return created

def generate_subscriptions_list():
    """Генерирует список подписок с разделением FAST/ALL."""
    base_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{BASE_DIR}"

    subs_lines = []

    subs_lines.append("=== 🇷🇺 RUSSIA (FAST) ===")
    for filename in RU_FILES:
        subs_lines.append(f"{base_url}/RU_Best/{filename}")
    subs_lines.append("")

    subs_lines.append("=== 🇷🇺 RUSSIA (ALL) ===")
    ru_all_candidates = sorted(
        f for f in os.listdir(FOLDER_RU)
        if f.startswith("ru_white_all_part") and f.endswith(".txt")
    )
    for fname in ru_all_candidates[:2]:
        subs_lines.append(f"{base_url}/RU_Best/{fname}")
    subs_lines.append("")

    subs_lines.append("=== 🇪🇺 EUROPE (FAST) ===")
    for filename in EURO_FILES:
        subs_lines.append(f"{base_url}/My_Euro/{filename}")
    subs_lines.append("")

    subs_lines.append("=== 🇪🇺 EUROPE (ALL) ===")
    euro_all_candidates = sorted(
        f for f in os.listdir(FOLDER_EURO)
        if f.startswith("my_euro_all_part") and f.endswith(".txt")
    )
    for fname in euro_all_candidates[:2]:
        subs_lines.append(f"{base_url}/My_Euro/{fname}")

    sub_list_path = os.path.join(BASE_DIR, "subscriptions_list.txt")
    with open(sub_list_path, "w", encoding="utf-8") as f:
        f.write("\n".join(subs_lines))

    print(f"\n📋 subscriptions_list.txt создан ({len([l for l in subs_lines if l.startswith('http')])} ссылок)")

    return sub_list_path

# --- ОСНОВНОЙ ЦИКЛ ---

if __name__ == "__main__":
    print("=== CHECKER v5 (FAST/ALL LAYERS) ===")
    print(f"Параметры: CACHE={CACHE_HOURS}h, MAX_PING={MAX_PING_MS}ms, FAST={FAST_LIMIT}, HISTORY={MAX_HISTORY_AGE//3600}h")

    # Очистка и создание папок
    for f in [FOLDER_RU, FOLDER_EURO]:
        if os.path.exists(f):
            shutil.rmtree(f)
        os.makedirs(f, exist_ok=True)

    # Загрузка истории
    history = load_json(HISTORY_FILE)

    # Получение ключей
    raw_tasks = fetch_keys(URLS_RU, "RU") + fetch_keys(URLS_MY, "MY")
    unique_tasks = list({t[0]: t[1] for t in raw_tasks}.items())[:MAX_KEYS]

    now = time.time()
    to_check, final_ru, final_euro = [], [], []

    print(f"\n📊 Всего уникальных ключей: {len(unique_tasks)}")

    # Обработка кэша
    for key, tag in unique_tasks:
        kid = key.split("#")[0]
        cached = history.get(kid)

        if cached and (now - cached['time'] < CACHE_HOURS * 3600) and cached.get('alive'):
            latency = cached['latency']
            country = cached.get('country', 'UN')
            host = cached.get('host', '')
            entry = make_final_key(kid, latency, country)

            if tag == "RU":
                final_ru.append(entry)
            elif tag == "MY" and not is_russian_exit(key, host, country):
                final_euro.append(entry)
        else:
            to_check.append((key, tag))

    print(f"✅ Из кэша: RU={len(final_ru)}, EURO={len(final_euro)}")
    print(f"🔍 На проверку: {len(to_check)}")

    # Проверка новых ключей
    if to_check:
        checked_count = 0
        with ThreadPoolExecutor(max_workers=THREADS) as executor:
            results = list(executor.map(check_single_key, to_check))

            for i, res in enumerate(results):
                if not res or res[0] is None:
                    continue

                latency, tag, country, host = res
                key, _ = to_check[i]
                kid = key.split("#")[0]

                history[kid] = {
                    'alive': True,
                    'latency': latency,
                    'time': now,
                    'country': country,
                    'host': host
                }

                entry = make_final_key(kid, latency, country)

                if tag == "RU":
                    final_ru.append(entry)
                elif tag == "MY" and not is_russian_exit(key, host, country):
                    final_euro.append(entry)

                checked_count += 1

        print(f"✅ Проверено успешно: {checked_count}")

    # Чистка истории
    history = {k: v for k, v in history.items() if now - v['time'] < MAX_HISTORY_AGE}
    save_json(HISTORY_FILE, history)

    # Фильтрация по пингу и сортировка
    def get_ms(s):
        ping = extract_ping(s)
        return ping if ping is not None else 9999

    final_ru_clean = [k for k in final_ru if extract_ping(k) is not None and extract_ping(k) <= MAX_PING_MS]
    final_euro_clean = [k for k in final_euro if extract_ping(k) is not None and extract_ping(k) <= MAX_PING_MS]

    final_ru_clean.sort(key=get_ms)
    final_euro_clean.sort(key=get_ms)

    print(f"\n📈 После фильтрации (≤ {MAX_PING_MS} ms) и сортировки:")
    print(f"  RU: {len(final_ru_clean)} ключей")
    print(f"  EURO: {len(final_euro_clean)} ключей")

    # Разделение на FAST и ALL
    res_ru_fast = final_ru_clean[:FAST_LIMIT]
    res_euro_fast = final_euro_clean[:FAST_LIMIT]
    res_ru_all = final_ru_clean
    res_euro_all = final_euro_clean

    print(f"\n🚀 FAST слои (топ {FAST_LIMIT}):")
    print(f"  RU FAST: {len(res_ru_fast)}")
    print(f"  EURO FAST: {len(res_euro_fast)}")

    # Сохранение FAST
    print(f"\n💾 Сохранение RU FAST → {FOLDER_RU}:")
    save_fixed_chunks_ru(res_ru_fast, FOLDER_RU)

    print(f"\n💾 Сохранение EURO FAST → {FOLDER_EURO}:")
    save_fixed_chunks_euro(res_euro_fast, FOLDER_EURO)

    # Сохранение ALL
    print(f"\n💾 Сохранение RU ALL → {FOLDER_RU}:")
    save_chunked(res_ru_all, FOLDER_RU, "ru_white_all")

    print(f"\n💾 Сохранение EURO ALL → {FOLDER_EURO}:")
    save_chunked(res_euro_all, FOLDER_EURO, "my_euro_all")

    # Генерация списка подписок
    sub_list_path = generate_subscriptions_list()

    # ПОДГОТОВКА ОТЧЕТА И ФАЙЛОВ ДЛЯ TG
    files_to_send = [sub_list_path]

    # Добавляем RU файлы
    for f in os.listdir(FOLDER_RU):
        if f.endswith('.txt'):
            files_to_send.append(os.path.join(FOLDER_RU, f))

    # Добавляем EURO файлы
    for f in os.listdir(FOLDER_EURO):
        if f.endswith('.txt'):
            files_to_send.append(os.path.join(FOLDER_EURO, f))

    msg = (
        f"✅ <b>Система когерентности обновлена</b>\n"
        f"━━━━━━━━━━━━━━\n"
        f"🇷🇺 Россия FAST: <code>{len(res_ru_fast)}</code>\n"
        f"🇷🇺 Россия ALL: <code>{len(res_ru_all)}</code>\n"
        f"🇪🇺 Европа FAST: <code>{len(res_euro_fast)}</code>\n"
        f"🇪🇺 Европа ALL: <code>{len(res_euro_all)}</code>\n"
        f"🕒 В базе кэша: {len(history)}\n"
        f"━━━━━━━━━━━━━━\n"
        f"📦 Все файлы прикреплены к отчету."
    )

    send_telegram_report(msg, files=files_to_send)
    print("\n✅ SUCCESS: FAST/ALL LAYERS GENERATED")
    print("Успех. Отчет отправлен.")





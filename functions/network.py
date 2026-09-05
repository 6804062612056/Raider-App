import ipaddress
import json
import re
import socket
import subprocess
import time
from typing import Any, Dict, List, Optional
from kivy.utils import platform
from kivy.app import App
from functions import database, file

PORT: int = 5000
BUFFER_SIZE: int = 4096

request_callback = None
server_running: bool = False
server_socket: Optional[socket.socket] = None


def acquire_android_multicast_lock() -> None:
    """เปิดท่อรับ-ส่ง Broadcast บน Android OS (จำเป็นมากเมื่อใช้บนมือถือ)"""
    if platform == "android":
        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Context = autoclass("android.content.Context")

            activity = PythonActivity.mActivity
            wifi_manager = activity.getSystemService(Context.WIFI_SERVICE)

            multicast_lock = wifi_manager.createMulticastLock("kivy_udp_lock")
            multicast_lock.acquire()
            print("ANDROID MULTICAST LOCK ACQUIRED")
        except Exception as e:
            print(f"MULTICAST LOCK ERROR: {e}")


def set_request_callback(callback) -> None:
    """กำหนด Callback Function สำหรับรับ Request"""
    global request_callback
    request_callback = callback


# ==========================================
# Network Discovery Section
# ==========================================

def get_windows_networks() -> List[Dict[str, str]]:
    if platform == "android":
        return []

    result: List[Dict[str, str]] = []
    found_nets: set[tuple] = set()

    try:
        output = subprocess.check_output(["ipconfig"], encoding="utf-8", errors="ignore")
        adapters = output.split("\n\n")

        for adapter in adapters:
            ip_match = re.search(r"IPv4 Address[^\r\n:]*:\s*([\d\.]+)", adapter)
            mask_match = re.search(r"Subnet Mask[^\r\n:]*:\s*([\d\.]+)", adapter)

            if ip_match and mask_match:
                ip = ip_match.group(1).strip()
                mask = mask_match.group(1).strip()

                if not ip.startswith(("127.", "169.254.")):
                    try:
                        net = ipaddress.IPv4Network(f"{ip}/{mask}", strict=False)
                        found_nets.add((ip, mask, str(net.broadcast_address)))
                    except Exception:
                        pass
    except Exception as e:
        print(f"IPCONFIG PARSE ERROR: {e}")

    if not found_nets:
        try:
            hostname = socket.gethostname()
            for ip in socket.gethostbyname_ex(hostname)[2]:
                if not ip.startswith(("127.", "169.254.")):
                    net24 = ipaddress.IPv4Network(f"{ip}/255.255.255.0", strict=False)
                    net16 = ipaddress.IPv4Network(f"{ip}/255.255.0.0", strict=False)
                    found_nets.add((ip, "255.255.255.0", str(net24.broadcast_address)))
                    found_nets.add((ip, "255.255.0.0", str(net16.broadcast_address)))
        except Exception as e:
            print(f"HOSTNAME ERROR: {e}")

    for ip, mask, b_ip in found_nets:
        info = {
            "ip": ip,
            "mask": mask,
            "broadcast": b_ip,
            "type": "active",
        }
        result.append(info)
    return result


def get_android_networks() -> List[Dict[str, str]]:
    if platform != "android":
        return []

    result: List[Dict[str, str]] = []
    zt_results: List[Dict[str, str]] = []  # 📌 แยกเก็บวง ZeroTier ไว้ต่างหากเพื่อให้ได้ความสำคัญสูงสุด

    try:
        from jnius import autoclass

        NetworkInterface = autoclass("java.net.NetworkInterface")
        interfaces = NetworkInterface.getNetworkInterfaces()

        while interfaces.hasMoreElements():
            interface = interfaces.nextElement()
            if_name = interface.getName().lower()
            
            is_zerotier = "zt" in if_name or "zerotier" in if_name or "tun" in if_name
            is_general_vpn = "ppp" in if_name or "p2p" in if_name

            if is_general_vpn and not is_zerotier:
                continue

            addresses = interface.getInterfaceAddresses()

            for i in range(addresses.size()):
                info = addresses.get(i)
                address = info.getAddress()

                if address is None or address.isLoopbackAddress():
                    continue

                ip = str(address.getHostAddress())
                if "." not in ip:
                    continue

                if ip.startswith(("127.", "169.254.")):
                    continue

                prefix = int(info.getNetworkPrefixLength())
                if not (0 < prefix <= 32):
                    prefix = 24

                try:
                    net = ipaddress.IPv4Network(f"{ip}/{prefix}", strict=False)
                    network_info = {
                        "ip": ip,
                        "mask": str(net.netmask),
                        "broadcast": str(net.broadcast_address),
                        "network": str(net),
                        "type": "active",
                    }
                    
                    # 📌 จัดลำดับให้ ZeroTier หรือ IP วงเสมือนขึ้นมาก่อน
                    if is_zerotier or ip.startswith("10."):
                        zt_results.append(network_info)
                    else:
                        result.append(network_info)
                except Exception:
                    continue
    except Exception as e:
        print(f"ANDROID NETWORK ERROR: {e}")

    # 📌 เอา ZeroTier ขึ้นมาไว้บนสุดเสมอ เพื่อให้ระบบหยิบ IP นี้ไปใช้ก่อนเน็ตซิม
    return zt_results + result


def get_networks() -> List[Dict[str, str]]:
    return get_android_networks() if platform == "android" else get_windows_networks()


def get_broadcast_subnets() -> set[str]:
    networks = get_networks()
    subnets = {
        "255.255.255.255", 
        "192.168.1.255", 
        "192.168.0.255", 
        "10.243.255.255", 
        "127.0.0.1"
    }
    
    for net in networks:
        b_ip = net.get("broadcast")
        if b_ip:
            subnets.add(b_ip)
            
    return subnets


def get_network_info() -> Optional[Dict[str, str]]:
    networks = get_networks()
    return networks[0] if networks else None


def get_network_ip() -> Optional[str]:
    info = get_network_info()
    return info["ip"] if info else "127.0.0.1"


# ==========================================
# Server Listener Section (ฝั่ง Customer รอดักฟังสัญญาณ Scan และ Book Request)
# ==========================================

def start_server() -> None:
    """เริ่มต้นรัน UDP Server Listener Loop (สำหรับฝั่ง Customer)"""
    global server_running, server_socket

    if server_running:
        return

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        sock.bind(("0.0.0.0", PORT))
        sock.settimeout(1.0)

        server_socket = sock
        server_running = True
        print(f"CUSTOMER SERVER STARTED ON PORT {PORT}")

        while server_running:
            try:
                data, address = sock.recvfrom(BUFFER_SIZE)
                request = json.loads(data.decode("utf-8"))
                request_type = request.get("type")

                if request_type == "scan_customer":
                    email = file.read_email()
                    if not email:
                        continue

                    user = database.search(email)
                    if not user:
                        continue

                    start_lat, start_lon, dest_lat, dest_lon = None, None, None, None
                    try:
                        app = App.get_running_app()
                        if app and hasattr(app, "root") and app.root:
                            sm = app.root
                            if hasattr(sm, "get_screen"):
                                try:
                                    select_screen = sm.get_screen("select_location")
                                    if select_screen:
                                        if select_screen.start_coords:
                                            start_lat, start_lon = select_screen.start_coords
                                        if select_screen.dest_coords:
                                            dest_lat, dest_lon = select_screen.dest_coords
                                except Exception:
                                    pass

                            if start_lat is None:
                                start_lat = getattr(sm, "my_start_lat", None)
                                start_lon = getattr(sm, "my_start_lon", None)
                                dest_lat = getattr(sm, "my_dest_lat", None)
                                dest_lon = getattr(sm, "my_dest_lon", None)
                    except Exception as e:
                        print(f"Error fetching coordinates: {e}")

                    # 📌 แนบ IP ที่แท้จริง (ZeroTier IP) ไปกับ Response
                    response = {
                        "type": "customer_info",
                        "email": email,
                        "firstname": user.get("firstname", ""),
                        "lastname": user.get("lastname", ""),
                        "role": user.get("role", "customer"),
                        "start_lat": start_lat,
                        "start_lon": start_lon,
                        "dest_lat": dest_lat,
                        "dest_lon": dest_lon,
                        "ip": get_network_ip(), 
                    }
                    sock.sendto(json.dumps(response).encode("utf-8"), address)
                    print(f"CUSTOMER INFO SENT TO RIDER: {address[0]} with coords: ({start_lat}, {start_lon}) -> ({dest_lat}, {dest_lon})")

                elif request_type == "BOOK_REQUEST":
                    if request_callback:
                        request_data = request
                        request_data["ip"] = address[0]
                        request_callback(request_data)
                    print(f"BOOK REQUEST RECEIVED FROM RIDER: {address[0]}")

            except socket.timeout:
                continue
            except Exception:
                pass
    except Exception as e:
        print(f"SERVER START ERROR: {e}")
    finally:
        server_running = False
        if server_socket:
            try:
                server_socket.close()
            except Exception:
                pass
            server_socket = None


def stop_server() -> None:
    global server_running
    server_running = False


# ==========================================
# Broadcast Scan Section (ฝั่ง Rider ใช้ปุ่ม SCAN ค้นหา Customer)
# ==========================================

def scan_network_for_customers() -> List[Dict[str, Any]]:
    """ให้ Rider ยิง Broadcast Scan หา Customer ที่กำลังรออยู่"""
    acquire_android_multicast_lock()

    customers: List[Dict[str, Any]] = []
    used_emails: set[str] = set()
    used_ips: set[str] = set()

    broadcast_targets = get_broadcast_subnets()
    req_data = json.dumps({"type": "scan_customer"}).encode("utf-8")

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        sock.settimeout(0.01)
        try:
            while True:
                sock.recvfrom(BUFFER_SIZE)
        except Exception:
            pass

        print("RIDER SENDING SCAN TO TARGETS:", broadcast_targets)

        for _ in range(3):
            for b_ip in broadcast_targets:
                try:
                    sock.sendto(req_data, (b_ip, PORT))
                except Exception as e:
                    print(f"BROADCAST SEND ERROR ({b_ip}): {e}")
            time.sleep(0.05)

        sock.settimeout(0.3)
        start_time = time.time()
        listen_duration = 2.0

        while time.time() - start_time < listen_duration:
            try:
                data, address = sock.recvfrom(BUFFER_SIZE)
                found_ip = address[0]

                response = json.loads(data.decode("utf-8"))
                if response.get("type") != "customer_info":
                    continue

                email = response.get("email")
                if not email or email in used_emails:
                    continue

                customer = response
                # 📌 บังคับใช้ IP ที่มือถือระบุมาใน JSON เพื่อป้องกันไอพีสลับวง
                customer["ip"] = response.get("ip", found_ip)

                if customer["ip"] in used_ips:
                    continue

                customers.append(customer)
                used_emails.add(email)
                used_ips.add(customer["ip"])
                print("FOUND CUSTOMER:", customer)

            except socket.timeout:
                continue
            except Exception:
                pass

    print("TOTAL CUSTOMERS FOUND:", len(customers))
    return customers

import socket,json,re,subprocess
from kivy.utils import platform
from functions import file,database

PORT=5000
request_callback=None
server_running=False
server_socket=None

def set_request_callback(callback):
    global request_callback
    request_callback=callback

def ip_int(ip):
    return sum(int(x)<<(24-i*8) for i,x in enumerate(ip.split(".")))

def int_ip(n):
    return ".".join(str((n>>x)&255) for x in (24,16,8,0))

def get_broadcast(ip,mask):
    try:
        return int_ip(ip_int(ip)|(0xffffffff^ip_int(mask)))
    except:
        return None

def get_windows_networks():
    if platform=="android":
        return []
    try:
        text=subprocess.check_output(["ipconfig"],encoding="utf-8",errors="ignore")
    except Exception as e:
        print("IPCONFIG ERROR:",e)
        return []
    result=[]
    blocks=re.split(r"\r?\n\r?\n",text)
    for block in blocks:
        ips=re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b",block)
        if not ips:
            continue
        low=block.lower()
        ip=None
        mask=None
        for x in ips:
            if x.startswith(("127.","169.254.")):
                continue
            if not ip:
                ip=x
            elif x.startswith(("255.","254.")):
                mask=x
                break
        if not ip:
            continue
        if not mask:
            mask="255.255.255.0"
        if "hamachi" in low:
            kind="hamachi"
        elif "radmin" in low:
            kind="radmin"
        elif "zerotier" in low or "zero tier" in low:
            kind="zerotier"
        elif ip.startswith("26."):
            kind="radmin"
        elif ip.startswith("25."):
            kind="hamachi"
        else:
            kind="lan"
        network={"ip":ip,"mask":mask,"broadcast":get_broadcast(ip,mask),"type":kind}
        result.append(network)
        print("NETWORK FOUND:",network)
    print("TOTAL NETWORKS:",len(result))
    return result

def get_android_networks():
    if platform!="android":
        return []
    result=[]
    try:
        from jnius import autoclass
        NetworkInterface=autoclass("java.net.NetworkInterface")
        interfaces=NetworkInterface.getNetworkInterfaces()
        while interfaces.hasMoreElements():
            interface=interfaces.nextElement()
            name=str(interface.getName()).lower()
            addresses=interface.getInterfaceAddresses()
            for i in range(addresses.size()):
                info=addresses.get(i)
                address=info.getAddress()
                if address is None or address.isLoopbackAddress():
                    continue
                ip=str(address.getHostAddress())
                if "." not in ip:
                    continue
                prefix=int(info.getNetworkPrefixLength())
                if prefix<=0 or prefix>32:
                    prefix=24
                mask=int_ip((0xffffffff<<(32-prefix))&0xffffffff)
                if name.startswith("zt"):
                    kind="zerotier"
                elif name.startswith("tun"):
                    kind="vpn"
                else:
                    kind="lan"
                network={"ip":ip,"mask":mask,"broadcast":get_broadcast(ip,mask),"type":kind}
                result.append(network)
                print("NETWORK FOUND:",network)
    except Exception as e:
        print("ANDROID NETWORK ERROR:",e)
    print("TOTAL NETWORKS:",len(result))
    return result

def get_networks():
    return get_android_networks() if platform=="android" else get_windows_networks()

def get_network_info():
    networks=get_networks()
    priority=["hamachi","radmin","zerotier","vpn","lan"]
    for kind in priority:
        for network in networks:
            if network["type"]==kind:
                print("SELECTED NETWORK:",network)
                return network
    print("NO NETWORK FOUND")
    return None

def get_network_ip():
    info=get_network_info()
    return info["ip"] if info else None

def start_server():
    global server_running,server_socket
    if server_running:
        print("SERVER: Already running")
        return
    info=get_network_info()
    if not info:
        print("SERVER: Network not found")
        return
    ip=info["ip"]
    sock=None
    try:
        sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        server_socket=sock
        sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        sock.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
        sock.bind(("0.0.0.0",PORT))
        sock.settimeout(1)
        server_running=True
        print(f"SERVER STARTED: {info['type']} {ip}:{PORT}")
        while server_running:
            try:
                data,address=sock.recvfrom(4096)
                request=json.loads(data.decode("utf-8"))
                request_type=request.get("type")
                print("REQUEST:",request_type,"FROM:",address[0])
                if request_type=="scan":
                    email=file.read_email()
                    if not email:
                        continue
                    user=database.search(email)
                    if not user:
                        continue
                    response={"type":"user","email":email}
                    sock.sendto(json.dumps(response).encode("utf-8"),address)
                    print("SCAN RESPONSE:",address[0])
                elif request_type=="customer_request":
                    customer=request.get("customer",{})
                    print("CUSTOMER REQUEST:",customer)
                    if request_callback:
                        request_callback(customer)
            except socket.timeout:
                continue
            except Exception as e:
                if server_running:
                    print("SERVER ERROR:",e)
    except Exception as e:
        print("SERVER START ERROR:",e)
    finally:
        server_running=False
        if sock:
            try:
                sock.close()
            except:
                pass
        server_socket=None
        print("SERVER STOPPED")

def stop_server():
    global server_running,server_socket
    server_running=False
    if server_socket:
        try:
            server_socket.close()
        except:
            pass
    server_socket=None
    print("SERVER STOP REQUESTED")

def scan_network():
    networks=get_networks()
    if not networks:
        print("SCAN: Network not found")
        return []
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)
    sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    sock.settimeout(2)
    targets=set()
    for network in networks:
        broadcast=network.get("broadcast")
        if broadcast:
            targets.add(broadcast)
    print("SCAN TARGETS:",targets)
    request=json.dumps({"type":"scan"}).encode("utf-8")
    for target in targets:
        try:
            sock.sendto(request,(target,PORT))
            print("SCAN SENT TO:",target)
        except Exception as e:
            print("SCAN SEND ERROR:",target,e)
    users=[]
    used_emails=set()
    used_ips=set()
    while True:
        try:
            data,address=sock.recvfrom(4096)
            response=json.loads(data.decode("utf-8"))
            if response.get("type")!="user":
                continue
            email=response.get("email")
            ip=address[0]
            if not email or email in used_emails or ip in used_ips:
                continue
            user=database.search(email)
            if not user:
                continue
            user["ip"]=ip
            users.append(user)
            used_emails.add(email)
            used_ips.add(ip)
            print("USER FOUND:",user)
        except socket.timeout:
            break
        except Exception as e:
            print("SCAN ERROR:",e)
    sock.close()
    print("TOTAL USERS:",len(users))
    return users

def send_customer_request(rider_ip):
    email=file.read_email()
    if not email:
        print("REQUEST: Customer email not found")
        return False
    customer=database.search(email)
    if not customer:
        print("REQUEST: Customer not found")
        return False
    customer["ip"]=get_network_ip()
    request={"type":"customer_request","customer":customer}
    try:
        sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        sock.settimeout(5)
        sock.sendto(json.dumps(request).encode("utf-8"),(rider_ip,PORT))
        sock.close()
        print("REQUEST SENT TO:",rider_ip)
        return True
    except Exception as e:
        print("REQUEST ERROR:",e)
        return False

import socket,json,re,subprocess,ipaddress
from kivy.utils import platform
from functions import file,database

PORT=5000
request_callback=None
server_running=False
server_socket=None

def set_request_callback(callback):
    global request_callback
    request_callback=callback

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
            if x.startswith(("255.","254.")):
                if ip and not mask:
                    mask=x
                continue
            if not ip:
                ip=x
        if not ip:
            continue
        if not mask:
            mask="255.255.255.0"
        if "hamachi" in low or ip.startswith("25."):
            kind="hamachi"
        elif "radmin" in low or ip.startswith("26."):
            kind="radmin"
        elif "zerotier" in low or "zero tier" in low:
            kind="zerotier"
        else:
            kind="lan"
        try:
            network=ipaddress.IPv4Network(f"{ip}/{mask}",strict=False)
            broadcast=str(network.broadcast_address)
        except:
            continue
        info={"ip":ip,"mask":mask,"broadcast":broadcast,"network":str(network),"type":kind}
        result.append(info)
        print("NETWORK FOUND:",info)
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
                try:
                    network=ipaddress.IPv4Network(f"{ip}/{prefix}",strict=False)
                    mask=str(network.netmask)
                    broadcast=str(network.broadcast_address)
                except:
                    continue
                if name.startswith("zt"):
                    kind="zerotier"
                elif name.startswith("tun"):
                    kind="vpn"
                elif name.startswith(("wlan","eth")):
                    kind="lan"
                else:
                    kind="other"
                network_info={"ip":ip,"mask":mask,"broadcast":broadcast,"network":str(network),"type":kind}
                result.append(network_info)
                print("NETWORK FOUND:",network_info)
    except Exception as e:
        print("ANDROID NETWORK ERROR:",e)
    print("TOTAL NETWORKS:",len(result))
    return result

def get_networks():
    return get_android_networks() if platform=="android" else get_windows_networks()

def get_network_info():
    networks=get_networks()
    priority=["hamachi","radmin","zerotier","vpn","lan","other"]
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

def scan_ip(sock,ip,local_ip,users,used_emails,used_ips):
    try:
        request=json.dumps({"type":"scan"}).encode("utf-8")
        sock.sendto(request,(ip,PORT))
        print("SCAN SENT TO:",ip)
        sock.settimeout(0.15)
        while True:
            try:
                data,address=sock.recvfrom(4096)
            except socket.timeout:
                break
            response=json.loads(data.decode("utf-8"))
            if response.get("type")!="user":
                continue
            email=response.get("email")
            found_ip=address[0]
            if not email or found_ip==local_ip:
                continue
            if email in used_emails or found_ip in used_ips:
                continue
            user=database.search(email)
            if not user:
                continue
            user["ip"]=found_ip
            users.append(user)
            used_emails.add(email)
            used_ips.add(found_ip)
            print("USER FOUND:",user)
    except Exception as e:
        print("SCAN ERROR:",ip,e)

def scan_network():
    networks=get_networks()
    if not networks:
        print("SCAN: Network not found")
        return []
    local_ip=get_network_ip()
    targets=[]
    for network in networks:
        try:
            net=ipaddress.IPv4Network(network["network"],strict=False)
            for ip in net.hosts():
                ip=str(ip)
                if ip!=local_ip:
                    targets.append(ip)
        except Exception as e:
            print("NETWORK SCAN ERROR:",e)
    targets=list(dict.fromkeys(targets))
    print("TOTAL SCAN IP:",len(targets))
    users=[]
    used_emails=set()
    used_ips=set()
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
    for ip in targets:
        scan_ip(sock,ip,local_ip,users,used_emails,used_ips)
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

import json
import socket
import threading
import time
from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen

from functions import network
from functions import file


class Connect1(Screen):
    result_text = StringProperty("Waiting for Rider...")
    subnets_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.server_sock = None
        self.is_running = False

    def on_enter(self):
        network.acquire_android_multicast_lock()
        self.result_text = "Waiting for Rider..."
        
        broadcasts = network.get_broadcast_subnets()
        formatted_subnets = "\n".join(f"• {b_ip}" for b_ip in sorted(broadcasts))
        self.subnets_text = f"Active Subnets:\n{formatted_subnets}"

        # เปิด Server ฝั่ง Customer รอรับข้อมูลที่พอร์ต 5001
        self.start_customer_listener()

        # ส่งข้อมูลพิกัดและคำขอไปยังไรเดอร์แบบ Real-time (วนลูปต่อเนื่อง)
        threading.Thread(
            target=self.broadcast_booking_request, name="BroadcastBookingThread", daemon=True
        ).start()

    def on_leave(self):
        self.stop_customer_listener()

    def start_customer_listener(self):
        self.is_running = True
        threading.Thread(
            target=self.customer_listen_thread, name="CustomerListenerThread", daemon=True
        ).start()

    def stop_customer_listener(self):
        self.is_running = False
        if self.server_sock:
            try:
                self.server_sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                self.server_sock.close()
            except Exception:
                pass
            self.server_sock = None

    def customer_listen_thread(self):
        """ลูกค้าฟังพอร์ต 5001 เพื่อรอรับสัญญาณ ACCEPT_JOB หรือ LOCATION_UPDATE จากไรเดอร์"""
        try:
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_sock.bind(("", 5001))
            self.server_sock.settimeout(1.0)
        except Exception as e:
            print("Socket bind error (Customer):", e)
            return

        while self.is_running:
            try:
                if not self.server_sock:
                    break
                data, addr = self.server_sock.recvfrom(1024)
                if not data:
                    continue

                raw_msg = data.decode("utf-8").strip()
                message = json.loads(raw_msg)
                msg_type = str(message.get("type", "")).strip().upper()
                
                # หากได้รับ ACCEPT_JOB หรือมีการส่งพิกัด LOCATION_UPDATE มาจากไรเดอร์ ให้ถือว่ารับงานแล้ว
                if msg_type in ["ACCEPT_JOB", "LOCATION_UPDATE"]:
                    print(f"Received {msg_type}! Switching customer to tracking_map...")
                    self.is_running = False
                    
                    # สั่งเปลี่ยนหน้าจอฝั่งลูกค้าไปที่ tracking_map ทันที
                    Clock.schedule_once(lambda dt: setattr(self.manager, "current", "tracking_map"))
                    break

            except socket.timeout:
                continue
            except Exception as e:
                if not self.is_running:
                    break
                print("Customer listener error:", e)
                break

        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass
            self.server_sock = None

    def broadcast_booking_request(self):
        """ส่งข้อมูลพิกัดไปยังพอร์ต 5000 ของไรเดอร์แบบวนลูปต่อเนื่องจนกว่าจะมีการตอบรับหรือออกจากหน้าจอ"""
        try:
            start = getattr(self.manager, "rider_start_coords", None)
            destination = getattr(self.manager, "rider_dest_coords", None)
            
            customer_email = file.read_email() if hasattr(file, "read_email") else ""
            user_db = network.database.search(customer_email) if hasattr(network, "database") and customer_email else {}
            
            # ดึง Rating ของลูกค้าเองโดยใช้ฟังก์ชัน get_rating() แบบไม่มี parameter
            customer_rating = file.get_rating() if hasattr(file, "get_rating") else 0

            payload = json.dumps({
                "type": "BOOK_REQUEST",
                "email": customer_email,
                "firstname": user_db.get("firstname", "Customer"),
                "lastname": user_db.get("lastname", ""),
                "rating": customer_rating,  # <--- แนบ Rating ส่งไปให้ไรเดอร์ด้วย
                "start_lat": start[0] if start else 13.738288,
                "start_lon": start[1] if start else 100.532340,
                "dest_lat": destination[0] if destination else 13.819220,
                "dest_lon": destination[1] if destination else 100.514600,
            }).encode("utf-8")

            broadcasts = network.get_broadcast_subnets()
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

            target_ips = set(broadcasts)
            target_ips.add("127.0.0.1")

            while self.is_running:
                for ip in target_ips:
                    try:
                        sock.sendto(payload, (ip, 5000))
                    except Exception:
                        pass
                time.sleep(2.0)
                
            sock.close()
        except Exception as e:
            print("Error broadcasting booking request:", e)

    def go_to(self, screen):
        self.manager.current = screen
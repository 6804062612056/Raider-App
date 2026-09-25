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

    def on_enter(self, *args):
        super().on_enter(*args) if hasattr(super(), "on_enter") else None
        self.start_dots_animation()
        network.acquire_android_multicast_lock()
        self.result_text = "Waiting for Rider..."
        
        broadcasts = network.get_broadcast_subnets()
        formatted_subnets = "\n".join(f"• {b_ip}" for b_ip in sorted(broadcasts))
        self.subnets_text = f"Active Subnets:\n{formatted_subnets}"

        self.start_customer_listener()

        threading.Thread(
            target=self.broadcast_booking_request, name="BroadcastBookingThread", daemon=True
        ).start()

    def on_leave(self, *args):
        self.stop_customer_listener()
        self.stop_dots_animation()
        super().on_leave(*args) if hasattr(super(), "on_leave") else None

    def start_customer_listener(self):
        self.stop_customer_listener()
        self.is_running = True
        threading.Thread(
            target=self.customer_listen_thread, name="CustomerListenerThread", daemon=True
        ).start()

    def stop_customer_listener(self):
        self.is_running = False
        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass
            self.server_sock = None

    def customer_listen_thread(self):
        """ลูกค้าฟังพอร์ต 5001 รอรับสัญญาณ ACCEPT_JOB หรือ CHECK_AVAILABILITY"""
        try:
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            if hasattr(socket, "SO_REUSEPORT"):
                try:
                    self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except Exception:
                    pass

            # ป้องกัน WinError 10054 บน Windows
            try:
                SIO_UDP_CONNRESET = -1744830452
                self.server_sock.ioctl(SIO_UDP_CONNRESET, False)
            except Exception:
                pass

            self.server_sock.bind(("", 5001))
            self.server_sock.settimeout(0.5)
        except Exception as e:
            print("Socket bind error (Customer 5001):", e)
            return

        print("Customer UDP Listener is running on port 5001...")

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

                print(f"Customer received UDP message: {msg_type} from {addr}")

                if msg_type == "CHECK_AVAILABILITY":
                    pong_msg = json.dumps({"type": "PONG_AVAILABLE"}).encode("utf-8")
                    try:
                        self.server_sock.sendto(pong_msg, addr)
                    except Exception:
                        pass

                elif msg_type == "ACCEPT_JOB":
                    print("ACCEPT_JOB received! Transitioning to tracking_map...")
                    
                    ack_msg = json.dumps({"type": "ACCEPT_ACK"}).encode("utf-8")
                    try:
                        self.server_sock.sendto(ack_msg, addr)
                    except Exception:
                        pass

                    rider_email = message.get("email", "")
                    if rider_email:
                        self.manager.current_rider_email = rider_email

                    self.is_running = False
                    Clock.schedule_once(lambda dt: self.switch_to_tracking())
                    break

            except socket.timeout:
                continue
            except ConnectionResetError:
                # ข้าม error 10054 บน Windows แล้ววนรับต่อ
                continue
            except (OSError, Exception) as e:
                if not self.is_running:
                    break
                print("Customer listener socket error/closed:", e)
                if self.is_running:
                    time.sleep(0.1)
                    continue
                break

        self.stop_customer_listener()

    def switch_to_tracking(self):
        if self.manager:
            self.manager.current = "tracking_map"

    def broadcast_booking_request(self):
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            try:
                SIO_UDP_CONNRESET = -1744830452
                sock.ioctl(SIO_UDP_CONNRESET, False)
            except Exception:
                pass

            start = getattr(self.manager, "rider_start_coords", None)
            destination = getattr(self.manager, "rider_dest_coords", None)
            
            customer_email = file.read_email() if hasattr(file, "read_email") else ""
            user_db = network.database.search(customer_email) if hasattr(network, "database") and customer_email else {}
            customer_rating = file.get_rating() if hasattr(file, "get_rating") else 0

            payload = json.dumps({
                "type": "BOOK_REQUEST",
                "email": customer_email,
                "firstname": user_db.get("firstname", "Customer"),
                "lastname": user_db.get("lastname", ""),
                "rating": customer_rating,
                "start_lat": start[0] if start else 13.738288,
                "start_lon": start[1] if start else 100.532340,
                "dest_lat": destination[0] if destination else 13.819220,
                "dest_lon": destination[1] if destination else 100.514600,
            }).encode("utf-8")

            while self.is_running:
                target_ips = set(network.get_broadcast_subnets())
                target_ips.add("255.255.255.255")
                target_ips.add("127.0.0.1")

                for ip in target_ips:
                    try:
                        sock.sendto(payload, (ip, 5000))
                    except Exception:
                        pass
                time.sleep(1.0)
                
        except Exception as e:
            print("Error broadcasting booking request:", e)
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

    def cancel_booking_and_back(self):
        self.is_running = False
        self.stop_customer_listener()

        def _send_cancel():
            try:
                customer_email = file.read_email() if hasattr(file, "read_email") else ""
                payload = json.dumps({
                    "type": "CANCEL_BOOKING",
                    "email": customer_email
                }).encode("utf-8")

                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

                target_ips = set(network.get_broadcast_subnets())
                target_ips.add("255.255.255.255")
                target_ips.add("127.0.0.1")

                for ip in target_ips:
                    try:
                        sock.sendto(payload, (ip, 5000))
                    except Exception:
                        pass
                sock.close()
            except Exception as e:
                print("Error sending cancel booking:", e)

        threading.Thread(target=_send_cancel, daemon=True).start()
        
        if hasattr(self.manager, "rider_start_coords"):
            self.manager.rider_start_coords = None
        if hasattr(self.manager, "rider_dest_coords"):
            self.manager.rider_dest_coords = None

        self.go_to("home_customer")

    def go_to(self, screen):
        self.manager.current = screen

    def start_dots_animation(self):
        from kivy.animation import Animation

        dot1 = self.ids.get("dot1")
        dot2 = self.ids.get("dot2")
        dot3 = self.ids.get("dot3")

        if not (dot1 and dot2 and dot3):
            return

        def bounce_node(widget):
            anim = Animation(y=widget.y + 12, duration=0.2, transition='out_quad') + \
                   Animation(y=widget.y, duration=0.2, transition='in_quad')
            anim.start(widget)

        def play_sequence(dt):
            bounce_node(dot1)
            Clock.schedule_once(lambda dt: bounce_node(dot2), 0.15)
            Clock.schedule_once(lambda dt: bounce_node(dot3), 0.30)

        play_sequence(0)
        self._dots_event = Clock.schedule_interval(play_sequence, 1.2)

    def stop_dots_animation(self):
        if hasattr(self, '_dots_event') and self._dots_event:
            Clock.unschedule(self._dots_event)
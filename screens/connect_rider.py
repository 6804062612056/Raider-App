import json
import socket
import threading
import time
from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.uix.button import Button
from kivy.uix.screenmanager import Screen
from kivy.graphics import Color, RoundedRectangle

from functions import network
from functions import file
from functions.cal_money import calculate_delivery


class Connect2(Screen):
    status_text = StringProperty("Searching for customers...")
    result_text = StringProperty("Searching for customers...")

    REQUEST_TIMEOUT = 2.0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.server_sock = None
        self.is_running = False
        self.active_requests = {}
        self.cleanup_event = None

    def on_enter(self, *args):
        super().on_enter(*args) if hasattr(super(), "on_enter") else None
        network.acquire_android_multicast_lock()
        
        self.clear_all_requests()
        self.stop_rider_listener()
        
        self.update_status("Searching for customers...")
        self.start_rider_listener()

        if not self.cleanup_event:
            self.cleanup_event = Clock.schedule_interval(self.check_expired_requests, 0.5)

    def on_leave(self, *args):
        self.stop_rider_listener()
        if self.cleanup_event:
            self.cleanup_event.cancel()
            self.cleanup_event = None
        self.clear_all_requests()
        super().on_leave(*args) if hasattr(super(), "on_leave") else None

    def update_status(self, text):
        self.status_text = text
        self.result_text = text

    def start_rider_listener(self):
        self.is_running = True
        threading.Thread(
            target=self.rider_listen_thread, name="RiderListenerThread", daemon=True
        ).start()

    def stop_rider_listener(self):
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

    def rider_listen_thread(self):
        try:
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.server_sock.bind(("", 5000))
            self.server_sock.settimeout(1.0)
        except Exception as e:
            print("Socket bind error (Rider 5000):", e)
            return

        while self.is_running:
            try:
                if not self.server_sock:
                    break
                data, addr = self.server_sock.recvfrom(2048)
                if not data:
                    continue

                raw_msg = data.decode("utf-8").strip()
                message = json.loads(raw_msg)
                msg_type = str(message.get("type", "")).strip().upper()
                customer_email = message.get("email", "")

                if not customer_email:
                    continue

                if msg_type == "BOOK_REQUEST":
                    Clock.schedule_once(
                        lambda dt, email=customer_email, msg=message, sender_addr=addr: self.add_or_update_request_button(
                            email, msg, sender_addr
                        )
                    )

                elif msg_type == "CANCEL_BOOKING":
                    Clock.schedule_once(
                        lambda dt, email=customer_email: self.remove_request_button(email)
                    )

            except socket.timeout:
                continue
            except (OSError, Exception) as e:
                if not self.is_running:
                    break
                print("Rider listener socket error/closed:", e)
                break

        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass
            self.server_sock = None

    def add_or_update_request_button(self, email, data, addr):
        now = time.time()
        container = self.ids.get("request_container")

        if email in self.active_requests:
            self.active_requests[email]["last_seen"] = now
            self.active_requests[email]["addr"] = addr
            self.active_requests[email]["data"] = data
        else:
            firstname = data.get("firstname", "Customer")
            lastname = data.get("lastname", "")
            rating = data.get("rating", 0)
            
            # คำนวณราคาค่าโดยสารจากพิกัดจริงด้วย calculate_delivery เช่นเดียวกับหน้า ride_info
            fare = 0
            try:
                start_lat = data.get("start_lat")
                start_lon = data.get("start_lon")
                dest_lat = data.get("dest_lat")
                dest_lon = data.get("dest_lon")
                if start_lat and start_lon and dest_lat and dest_lon:
                    calc_result = calculate_delivery((start_lat, start_lon), (dest_lat, dest_lon))
                    if calc_result and "price" in calc_result:
                        fare = calc_result["price"]
            except Exception as e:
                print("Error calculating fare for button:", e)

            btn_text = f"{firstname} {lastname} : {fare} THB (Rating {float(rating):.1f})"
            
            btn = Button(
                text=btn_text,
                size_hint_y=None,
                height='56dp',
                font_size='18sp',
                bold=True,
                color=(0.2, 0.2, 0.2, 1),
                background_color=(0, 0, 0, 0),
                background_normal='',
                background_down=''
            )

            with btn.canvas.before:
                btn_color = Color(1, 0.8, 0, 1)
                btn_rect = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[20,])

            def update_btn_graphics(instance, *args):
                btn_rect.pos = instance.pos
                btn_rect.size = instance.size

            def on_btn_state(instance, value):
                if value == 'down':
                    btn_color.rgba = (0.9, 0.7, 0, 1)
                else:
                    btn_color.rgba = (1, 0.8, 0, 1)

            btn.bind(pos=update_btn_graphics, size=update_btn_graphics, state=on_btn_state)
            btn.bind(on_release=lambda instance, e=email: self.inspect_job(e))

            if container:
                container.add_widget(btn)

            self.active_requests[email] = {
                "data": data,
                "button": btn,
                "last_seen": now,
                "addr": addr,
            }

            self.update_status(f"Found {len(self.active_requests)} request(s)!")

    def remove_request_button(self, email):
        if email in self.active_requests:
            btn_info = self.active_requests.pop(email)
            btn = btn_info.get("button")
            container = self.ids.get("request_container")

            if container and btn:
                container.remove_widget(btn)

            if not self.active_requests:
                self.update_status("Searching for passengers...")
            else:
                self.update_status(f"Found {len(self.active_requests)} request(s)!")

    def check_expired_requests(self, dt):
        try:
            now = time.time()
            expired_emails = [
                email
                for email, req in list(self.active_requests.items())
                if now - req.get("last_seen", 0) > self.REQUEST_TIMEOUT
            ]

            for email in expired_emails:
                self.remove_request_button(email)
        except Exception as e:
            print("Error checking expired requests:", e)

    def clear_all_requests(self):
        container = self.ids.get("request_container")
        if container:
            container.clear_widgets()
        self.active_requests.clear()

    def inspect_job(self, customer_email):
        if customer_email not in self.active_requests:
            self.update_status("This request has been cancelled!")
            return

        req_info = self.active_requests[customer_email]
        data = req_info.get("data", {})
        addr = req_info.get("addr")

        self.update_status("Verifying customer status...")

        def _verify_and_proceed():
            is_valid = False
            try:
                verify_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                verify_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                verify_sock.settimeout(0.8)

                ping_msg = json.dumps({"type": "CHECK_AVAILABILITY"}).encode("utf-8")

                target_ips = set(network.get_broadcast_subnets()) if hasattr(network, "get_broadcast_subnets") else set()
                target_ips.add("255.255.255.255")
                target_ips.add("127.0.0.1")
                if addr:
                    target_ips.add(addr[0])

                for ip in target_ips:
                    try:
                        verify_sock.sendto(ping_msg, (ip, 5001))
                    except Exception:
                        pass

                try:
                    while True:
                        resp, _ = verify_sock.recvfrom(512)
                        if resp:
                            resp_json = json.loads(resp.decode("utf-8"))
                            if resp_json.get("type") in ["PONG_AVAILABLE", "PONG"]:
                                is_valid = True
                                break
                except socket.timeout:
                    is_valid = False

                verify_sock.close()
            except Exception as e:
                print("Error verifying customer availability:", e)
                is_valid = False

            if is_valid:
                Clock.schedule_once(lambda dt: self._go_to_ride_info(customer_email, data, addr))
            else:
                Clock.schedule_once(lambda dt: self._reject_expired_job(customer_email))

        threading.Thread(target=_verify_and_proceed, daemon=True).start()

    def _reject_expired_job(self, customer_email):
        self.remove_request_button(customer_email)
        self.update_status("Customer is no longer available!")

    def _go_to_ride_info(self, customer_email, data, addr):
        self.manager.current_customer_email = customer_email
        if addr:
            self.manager.selected_customer_ip = addr[0]

        self.manager.rider_start_coords = (data.get("start_lat"), data.get("start_lon"))
        self.manager.rider_dest_coords = (data.get("dest_lat"), data.get("dest_lon"))

        self.stop_rider_listener()
        self.go_to("ride_info")

    def go_to(self, screen):
        self.manager.current = screen

    def back(self):
        self.go_to("home_rider")
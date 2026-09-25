import json
import socket
import time
import threading
from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen
from kivy_garden.mapview import MapMarker, MapView

from functions import network
from functions import file
from functions.cal_money import calculate_delivery
from functions.dialogs import show_error_popup


class StaticMapView(MapView):
    """Special MapView that disables dragging, zooming, and map touch interactions."""

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos):
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos):
            return True
        return super().on_touch_up(touch)


class RideInfoScreen(Screen):
    distance_text = StringProperty("Calculating...")
    earnings_text = StringProperty("Calculating...")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_start_marker = None
        self.current_dest_marker = None
        self.udp_sock = None
        self.is_listening = False
        self.is_cancelled = False

    def on_enter(self):
        try:
            self.distance_text = "Calculating..."
            self.earnings_text = "Calculating..."
            self.is_cancelled = False

            start = getattr(self.manager, "rider_start_coords", None)
            destination = getattr(self.manager, "rider_dest_coords", None)

            if not start or not destination:
                print("Warning: Missing customer coordinates, using defaults.")
                start = start or (13.738288, 100.532340)
                destination = destination or (13.819220, 100.514600)

            self.setup_map(start, destination)
            self.start_listening_udp()

            threading.Thread(
                target=self._calculate_ride_async,
                args=(start, destination),
                daemon=True
            ).start()

        except Exception as e:
            print("RideInfoScreen error:", e)
            self.distance_text = "Error"
            self.earnings_text = "Error"

    def on_leave(self):
        self.is_listening = False
        if self.udp_sock:
            try:
                self.udp_sock.close()
            except Exception:
                pass
            self.udp_sock = None

    def start_listening_udp(self):
        if self.is_listening:
            return

        self.is_listening = True

        def _listen():
            try:
                self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.udp_sock.bind(("", 5001))
                self.udp_sock.settimeout(0.5)

                while self.is_listening:
                    try:
                        sock = self.udp_sock
                        if not sock or not self.is_listening:
                            break

                        data, addr = sock.recvfrom(1024)
                        if not data or not self.is_listening:
                            continue

                        msg = json.loads(data.decode("utf-8"))
                        msg_type = msg.get("type")

                        if msg_type in ["CANCEL_JOB", "CUSTOMER_CANCEL"]:
                            if not self.is_cancelled:
                                self.is_cancelled = True
                                Clock.schedule_once(lambda dt: self._show_cancel_error())

                    except socket.timeout:
                        continue
                    except (ConnectionResetError, OSError):
                        break
                    except Exception:
                        pass
            except Exception:
                pass
            finally:
                if self.udp_sock:
                    try:
                        self.udp_sock.close()
                    except Exception:
                        pass
                    self.udp_sock = None

        threading.Thread(target=_listen, daemon=True).start()

    def _calculate_ride_async(self, start, destination):
        try:
            result = calculate_delivery(start, destination)
            if result:
                dist_str = f"{result['distance']} km"
                earnings_str = f"{result['price']} THB"
            else:
                dist_str = "N/A"
                earnings_str = "N/A"
        except Exception as e:
            print("Calculate delivery error:", e)
            dist_str = "Error"
            earnings_str = "Error"

        Clock.schedule_once(
            lambda dt: self._update_ui_text(dist_str, earnings_str)
        )

    def _update_ui_text(self, dist_str, earnings_str):
        self.distance_text = dist_str
        self.earnings_text = earnings_str

    def setup_map(self, start, destination):
        mapview = self.ids.map_view

        if self.current_start_marker:
            mapview.remove_marker(self.current_start_marker)
            self.current_start_marker = None

        if self.current_dest_marker:
            mapview.remove_marker(self.current_dest_marker)
            self.current_dest_marker = None

        if not start or not destination:
            mapview.center_on(13.7563, 100.5018)
            mapview.zoom = 13
            return

        self.current_start_marker = MapMarker(lat=start[0], lon=start[1], color=[1, 0, 0, 1])
        self.current_start_marker.anchor_x = 0.5
        self.current_start_marker.anchor_y = 0.0
        mapview.add_marker(self.current_start_marker)

        self.current_dest_marker = MapMarker(lat=destination[0], lon=destination[1], color=[0, 1, 0, 1])
        self.current_dest_marker.anchor_x = 0.5
        self.current_dest_marker.anchor_y = 0.0
        mapview.add_marker(self.current_dest_marker)

        center_lat = (start[0] + destination[0]) / 2
        center_lon = (start[1] + destination[1]) / 2
        mapview.center_on(center_lat, center_lon)

        lat_diff = abs(start[0] - destination[0])
        lon_diff = abs(start[1] - destination[1])
        max_diff = max(lat_diff, lon_diff)

        if max_diff > 5.0:
            mapview.zoom = 4
        elif max_diff > 2.0:
            mapview.zoom = 5
        elif max_diff > 1.0:
            mapview.zoom = 6
        elif max_diff > 0.5:
            mapview.zoom = 7
        elif max_diff > 0.2:
            mapview.zoom = 8
        elif max_diff > 0.1:
            mapview.zoom = 9
        elif max_diff > 0.05:
            mapview.zoom = 10
        elif max_diff > 0.02:
            mapview.zoom = 11
        elif max_diff > 0.01:
            mapview.zoom = 12
        else:
            mapview.zoom = 13

        mapview.trigger_update(False)

    def accept_ride(self):
        if self.is_cancelled:
            self._show_cancel_error()
            return

        customer_ip = getattr(self.manager, "selected_customer_ip", None)

        def _verify_and_accept():
            is_customer_alive = False
            verify_sock = None
            try:
                verify_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                verify_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                verify_sock.settimeout(0.8)

                ping_msg = json.dumps({"type": "CHECK_AVAILABILITY"}).encode("utf-8")

                target_ips = set(network.get_broadcast_subnets()) if hasattr(network, "get_broadcast_subnets") else set()
                target_ips.add("255.255.255.255")
                target_ips.add("127.0.0.1")
                if customer_ip:
                    target_ips.add(customer_ip)

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
                                is_customer_alive = True
                                break
                except socket.timeout:
                    is_customer_alive = False

            except Exception as e:
                print("Error verifying customer before accept:", e)
                is_customer_alive = False
            finally:
                if verify_sock:
                    try:
                        verify_sock.close()
                    except Exception:
                        pass

            if not is_customer_alive:
                Clock.schedule_once(lambda dt: self._show_cancel_error())
                return

            sock = None
            try:
                rider_email = file.read_email() if hasattr(file, "read_email") else ""
                user_db = network.database.search(rider_email) if hasattr(network, "database") and rider_email else {}

                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

                try:
                    SIO_UDP_CONNRESET = -1744830452
                    sock.ioctl(socket.SIO_UDP_CONNRESET, False)
                except Exception:
                    pass

                accept_msg = json.dumps({
                    "type": "ACCEPT_JOB",
                    "rider_ip": network.get_network_ip() if hasattr(network, "get_network_ip") else "",
                    "email": rider_email,
                    "firstname": user_db.get("firstname", "Rider"),
                    "lastname": user_db.get("lastname", ""),
                }).encode("utf-8")

                print("Rider sending ACCEPT_JOB...")
                for _ in range(3):
                    for ip in target_ips:
                        try:
                            sock.sendto(accept_msg, (ip, 5001))
                        except Exception:
                            pass
                    time.sleep(0.05)

            except Exception as e:
                print("Error during accept send:", e)
            finally:
                if sock:
                    try:
                        sock.close()
                    except Exception:
                        pass

            Clock.schedule_once(lambda dt: setattr(self.manager, "current", "tracking_map"))

        threading.Thread(target=_verify_and_accept, daemon=True).start()

    def _show_cancel_error(self):
        show_error_popup(
            message="The customer has cancelled the request or logged out.",
            screen_manager=self.manager,
            target_screen="connect_rider"
        )

    def reject_ride(self):
        customer_ip = getattr(self.manager, "selected_customer_ip", None)

        def _send():
            try:
                msg = json.dumps({"type": "REJECT_JOB"}).encode("utf-8")
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

                target_ips = set(network.get_broadcast_subnets()) if hasattr(network, "get_broadcast_subnets") else set()
                target_ips.add("255.255.255.255")
                target_ips.add("127.0.0.1")
                if customer_ip:
                    target_ips.add(customer_ip)

                for ip in target_ips:
                    try:
                        sock.sendto(msg, (ip, 5001))
                    except Exception:
                        pass
                sock.close()
            except Exception as e:
                print("Error sending reject job:", e)

            Clock.schedule_once(lambda dt: setattr(self.manager, "current", "connect_rider"))

        threading.Thread(target=_send, daemon=True).start()

    def go_back(self):
        self.manager.current = "connect_rider"
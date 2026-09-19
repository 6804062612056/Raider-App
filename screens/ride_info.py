import json
import socket
import threading
from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen
from kivy_garden.mapview import MapMarker, MapView

from functions import network
from functions.cal_money import calculate_delivery


class StaticMapView(MapView):
    """MapView แบบพิเศษที่บล็อกการเลื่อน การซูม และการสัมผัสแผนที่ทั้งหมด"""

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
    distance_text = StringProperty("xxx")
    earnings_text = StringProperty("xxx")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # ประกาศตัวแปรเก็บอ้างอิงหมุดปัจจุบันเพื่อใช้ในการลบของเก่าทิ้ง
        self.current_start_marker = None
        self.current_dest_marker = None

    def on_enter(self):
        try:
            start = getattr(self.manager, "rider_start_coords", None)
            destination = getattr(self.manager, "rider_dest_coords", None)

            if not start or not destination:
                print("Warning: Missing customer coordinates, using defaults.")
                start = start or (13.738288, 100.532340)
                destination = destination or (13.819220, 100.514600)

            result = calculate_delivery(start, destination)
            if result:
                self.distance_text = f"{result['distance']} km"
                self.earnings_text = f"{result['price']} THB"
            else:
                self.distance_text = "N/A"
                self.earnings_text = "N/A"

            self.setup_map(start, destination)

        except Exception as e:
            print("RideInfoScreen error:", e)
            self.distance_text = "Error"
            self.earnings_text = "Error"

    def setup_map(self, start, destination):
        mapview = self.ids.map_view

        # 1. ลบหมุดเก่ารอบที่แล้วทิ้งอย่างถูกต้องผ่านตัวแปรอ้างอิงโดยตรง
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

        # 2. สร้างหมุดใหม่และเก็บลงในตัวแปรประจำคลาส
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

        # ปรับระดับการซูมแบบครอบคลุมระยะทางที่กว้างขึ้น
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

        # 3. บังคับอัปเดตแผนที่ให้เรนเดอร์หมุดใหม่ทันที
        mapview.trigger_update(False)

    def accept_ride(self):
        """เมื่อไรเดอร์กดปุ่มรับงาน ให้ส่งสัญญาณ ACCEPT_JOB ไปบอกลูกค้าที่พอร์ต 5001"""
        customer_ip = getattr(self.manager, "selected_customer_ip", None)

        def _send():
            if customer_ip:
                try:
                    rider_email = network.file.read_email()
                    user_db = network.database.search(rider_email) if rider_email else {}

                    msg = json.dumps({
                        "type": "ACCEPT_JOB",
                        "rider_ip": network.get_network_ip(),
                        "email": rider_email,
                        "firstname": user_db.get("firstname", "Rider"),
                        "lastname": user_db.get("lastname", ""),
                    }).encode("utf-8")

                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.sendto(msg, (customer_ip, 5001))
                    sock.close()
                except Exception as e:
                    print("Error sending accept job from ride_info:", e)

            Clock.schedule_once(lambda dt: setattr(self.manager, "current", "tracking_map"))

        threading.Thread(target=_send, daemon=True).start()

    def reject_ride(self):
        """เมื่อไรเดอร์กดปุ่มปฏิเสธงาน ส่งสัญญาณ REJECT_JOB ไปบอกลูกค้า แล้วพากลับหน้าเลือกงาน"""
        customer_ip = getattr(self.manager, "selected_customer_ip", None)

        def _send():
            if customer_ip:
                try:
                    msg = json.dumps({
                        "type": "REJECT_JOB"
                    }).encode("utf-8")

                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.sendto(msg, (customer_ip, 5001))
                    sock.close()
                except Exception as e:
                    print("Error sending reject job from ride_info:", e)

            Clock.schedule_once(lambda dt: setattr(self.manager, "current", "connect_rider"))

        threading.Thread(target=_send, daemon=True).start()

    def go_back(self):
        self.manager.current = "connect_rider"
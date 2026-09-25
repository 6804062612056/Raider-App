import threading
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty
from kivy.uix.screenmanager import Screen
from kivy.utils import platform
from kivy.clock import Clock
from kivy.metrics import dp
from kivy_garden.mapview import MapMarker
from functions import file, cal_money


class SelectLocation(Screen):
    mode = StringProperty("start")
    current_money_text = StringProperty("0.00")
    trip_price_text = StringProperty("0.00")
    message = StringProperty("")

    start_coords = ObjectProperty(None, allownone=True)
    dest_coords = ObjectProperty(None, allownone=True)

    start_marker = None
    dest_marker = None

    # ตัวแปรจัดการ Animation แผงด้านล่าง (เปลี่ยนเป็น BooleanProperty เพื่อให้ KV ดักจับได้)
    is_collapsed = BooleanProperty(False)
    EXPANDED_HEIGHT = dp(260)
    COLLAPSED_HEIGHT = dp(45)

    # ตัวแปรจัดการ Thread และการหน่วงเวลาคำนวณ (Debounce)
    calc_event = None

    def on_enter(self):
        print("ENTER MAP")
        self.message = ""
        self.trip_price_text = "0.00"

        try:
            money = file.get_money()
            self.current_money_text = f"{float(money):,.2f}"
        except Exception:
            self.current_money_text = "0.00"

        mapview = self.ids.map_view

        if self.start_marker:
            mapview.remove_marker(self.start_marker)
            self.start_marker = None

        if self.dest_marker:
            mapview.remove_marker(self.dest_marker)
            self.dest_marker = None

        self.start_coords = None
        self.dest_coords = None
        self.mode = "start"

        self.gps_centered = False
        self.prev_lat = None
        self.prev_lon = None

        self.update_map(13.7563, 100.5018)

        if platform == "android":
            self.start_gps()

    def update_map(self, lat, lon):
        mapview = self.ids.map_view
        mapview.center_on(lat, lon)

    def start_gps(self):
        pass

    def set_mode(self, selected_mode: str):
        self.mode = selected_mode
        print(f"Selection mode set to: {self.mode}")

    def on_map_touch(self, mapview, touch):
        """จัดการการแตะแผนที่ ป้องกันการกดทะลุแผงปุ่ม และสร้างหมุด"""
        if not mapview.collide_point(*touch.pos):
            return False

        # ป้องกันไม่ให้กดโดนแผงปุ่มด้านล่างแล้วทะลุไปสร้างหมุดบนแผนที่
        bottom_panel = self.ids.get('bottom_panel')
        if bottom_panel and touch.y <= bottom_panel.height:
            return True  # คืนค่า True บล็อก Touch ไม่ให้ลงไปที่ MapView

        if (
            touch.is_mouse_scrolling
            or abs(touch.x - touch.ox) > 5
            or abs(touch.y - touch.oy) > 5
        ):
            return False

        rel_x = touch.x - mapview.x
        rel_y = touch.y - mapview.y

        lat, lon = mapview.get_latlon_at(rel_x, rel_y)

        if self.mode == "start":
            self.start_coords = (lat, lon)
            if self.start_marker:
                mapview.remove_marker(self.start_marker)
                self.start_marker = None

            self.start_marker = MapMarker(lat=lat, lon=lon, color=[1, 0, 0, 1])
            self.start_marker.anchor_x = 0.5
            self.start_marker.anchor_y = 0.0
            mapview.add_marker(self.start_marker)

        elif self.mode == "destination":
            self.dest_coords = (lat, lon)
            if self.dest_marker:
                mapview.remove_marker(self.dest_marker)
                self.dest_marker = None

            self.dest_marker = MapMarker(lat=lat, lon=lon, color=[0, 1, 0, 1])
            self.dest_marker.anchor_x = 0.5
            self.dest_marker.anchor_y = 0.0
            mapview.add_marker(self.dest_marker)

        # เมื่อมีทั้งจุดเริ่มต้นและปลายทาง -> คำนวณราคาแบบ Async โดยใช้ Debounce (0.3 วินาที)
        if self.start_coords and self.dest_coords:
            self.trigger_async_calculation()

        return True

    def trigger_async_calculation(self):
        """เลื่อนการยิง API คำนวณราคาออกไป 0.3 วินาที เพื่อรอให้ผู้ใช้นิ่งก่อน (ป้องกันการกดรัว)"""
        if self.calc_event:
            self.calc_event.cancel()
        
        self.trip_price_text = ""
        # รอ 0.3 วินาทีหลังการแตะครั้งสุดท้าย หากมีการแตะใหม่จะถูก Cancel แล้วนับใหม่
        self.calc_event = Clock.schedule_once(lambda dt: self._start_calc_thread(), 0.3)

    def _start_calc_thread(self):
        """ส่งงานไปรันบน Background Thread"""
        threading.Thread(target=self._calculate_delivery_worker, daemon=True).start()

    def _calculate_delivery_worker(self):
        """รันบน Background Thread สื่อสารกลับ Kivy Main Thread ด้วย Clock.schedule_once"""
        result = cal_money.calculate_delivery(self.start_coords, self.dest_coords)
        Clock.schedule_once(lambda dt: self._update_price_ui(result))

    def _update_price_ui(self, result):
        """อัปเดตราคาบน UI หลังคำนวณเสร็จ"""
        if result and "price" in result:
            self.trip_price_text = f"{float(result['price']):,.2f}"
        else:
            self.trip_price_text = "0.00"

    def confirm_route(self):
        if not self.start_coords or not self.dest_coords:
            self.message = "Please select both start and destination points."
            return

        try:
            current_money = float(file.get_money())
            trip_price = float(self.trip_price_text.replace(",", ""))

            if current_money < trip_price:
                self.message = "Insufficient balance."
                return
        except Exception:
            pass

        self.manager.rider_start_coords = self.start_coords
        self.manager.rider_dest_coords = self.dest_coords
        
        self.manager.my_start_lat = self.start_coords[0]
        self.manager.my_start_lon = self.start_coords[1]
        self.manager.my_dest_lat = self.dest_coords[0]
        self.manager.my_dest_lon = self.dest_coords[1]

        self.manager.current = "connect_customer"

    def toggle_sheet(self):
        """กดปุ่มเพื่อสลับระหว่าง พับเก็บ / กางออก"""
        from kivy.animation import Animation

        panel = self.ids.get('bottom_panel')
        if not panel:
            return

        target_height = self.COLLAPSED_HEIGHT if not self.is_collapsed else self.EXPANDED_HEIGHT
        
        anim = Animation(height=target_height, duration=0.25, transition='out_cubic')
        anim.start(panel)
        self.is_collapsed = not self.is_collapsed
import json
import socket
import threading
from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen
from kivy_garden.mapview import MapMarker, MapView

from functions import file, database
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


class RideFeeScreen(Screen):
    distance_text = StringProperty("Calculating...")
    ride_fee_text = StringProperty("Calculating...")
    balance_text = StringProperty("Loading...")
    price_value = 0.0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_start_marker = None
        self.current_dest_marker = None

    def on_enter(self):
        # ตั้งค่าแสดงผลเริ่มต้นเพื่อไม่ให้หน้าจอว่างเปล่า
        self.distance_text = "Calculating..."
        self.ride_fee_text = "Calculating..."
        
        start = getattr(self.manager, "rider_start_coords", None)
        destination = getattr(self.manager, "rider_dest_coords", None)

        # 1. วาดแผนที่ก่อนทันที (ไม่รอ Network Request)
        self.setup_map(start, destination)

        # 2. ย้ายการดึงข้อมูลเงินและการคำนวณค่าส่งไปทำใน Background Thread
        threading.Thread(
            target=self._load_screen_data_async, 
            args=(start, destination), 
            daemon=True
        ).start()

    def _load_screen_data_async(self, start, destination):
        """คำนวณราคาและดึงยอดเงินคงเหลือใน Background Thread"""
        # ดึงยอดเงิน
        try:
            money = file.get_money()
            balance_str = f"{float(money):,.2f} THB"
        except Exception as e:
            print("Load balance error:", e)
            balance_str = "0.00 THB"

        # คำนวณเส้นทางและค่าบริการ
        dist_str = "0.0 km"
        fee_str = "0.00 THB"
        price_val = 0.0

        if start and destination:
            result = calculate_delivery(start, destination)
            if result:
                dist_str = f"{result['distance']} km"
                price_val = float(result['price'])
                fee_str = f"{price_val:,.2f} THB"
            else:
                dist_str = "N/A"
                fee_str = "N/A"

        # อัปเดต UI บน Main Thread
        Clock.schedule_once(
            lambda dt: self._update_ui_data(balance_str, dist_str, fee_str, price_val)
        )

    def _update_ui_data(self, balance_str, dist_str, fee_str, price_val):
        self.balance_text = balance_str
        self.distance_text = dist_str
        self.ride_fee_text = fee_str
        self.price_value = price_val

    def setup_map(self, start, destination):
        mapview = self.ids.map_view
        
        # ลบหมุดเก่า
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

        # สร้างหมุดใหม่
        self.current_start_marker = MapMarker(lat=start[0], lon=start[1], color=[1, 0, 0, 1])
        self.current_start_marker.anchor_x = 0.5
        self.current_start_marker.anchor_y = 0.0
        mapview.add_marker(self.current_start_marker)

        self.current_dest_marker = MapMarker(lat=destination[0], lon=destination[1], color=[0, 1, 0, 1])
        self.current_dest_marker.anchor_x = 0.5
        self.current_dest_marker.anchor_y = 0.0
        mapview.add_marker(self.current_dest_marker)

        # จัดตำแหน่งกึ่งกลาง
        center_lat = (start[0] + destination[0]) / 2
        center_lon = (start[1] + destination[1]) / 2
        mapview.center_on(center_lat, center_lon)
        mapview.zoom = 13
        mapview.trigger_update(False)

    def on_continue(self):
        """เมื่อกดปุ่มดำเนินการต่อ เปลี่ยนหน้าทันที แล้วไปตัดเงินใน Background Thread"""
        role = file.get_role()
        price = self.price_value
        rider_email = getattr(self.manager, "current_rider_email", None)

        if role == "customer" and price > 0:
            # ย้ายกระบวนการชำระเงินไปทำเบื้องหลัง
            threading.Thread(
                target=self._process_payment_async,
                args=(price, rider_email),
                daemon=True
            ).start()

        # สลับไปยังหน้าถัดไปทันที ไม่ต้องรอเขียน Database เสร็จ
        self.manager.current = "rating"

    def _process_payment_async(self, price, rider_email):
        """ประมวลผลการโอนเงิน/หักเงินเบื้องหลัง"""
        try:
            current_cust_money = float(file.get_money())
            if current_cust_money >= price:
                # 1. หักเงินลูกค้า
                file.change_money(-price)
                
                # 2. เพิ่มเงินให้ไรเดอร์
                if rider_email:
                    rider_data = database.search(rider_email)
                    if rider_data:
                        current_rider_money = float(rider_data.get("money", 0))
                        new_rider_money = current_rider_money + price
                        database.update_column(rider_email, "money", new_rider_money)
                        print(f"Successfully transferred {price} THB to rider: {rider_email}")
                    else:
                        print(f"Rider email {rider_email} not found in database.")
                else:
                    print("Warning: current_rider_email not found in manager!")
            else:
                print("Warning: Customer money is not enough!")
        except Exception as e:
            print("Error processing payment:", e)
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
    distance_text = StringProperty("xxx")
    ride_fee_text = StringProperty("xxx")
    balance_text = StringProperty("xxx")
    price_value = 0.0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # ประกาศตัวแปรเก็บสถานะหมุดปัจจุบันเพื่อเอาไว้สั่งลบทีหลัง
        self.current_start_marker = None
        self.current_dest_marker = None

    def on_enter(self):
        try:
            start = getattr(self.manager, "rider_start_coords", None)
            destination = getattr(self.manager, "rider_dest_coords", None)

            if not start or not destination:
                print("Warning: Start or Destination coords not found in RideFeeScreen!")
                self.distance_text = "0.0 km"
                self.price_value = 0.0
                self.ride_fee_text = "0.00 THB"
                self.setup_map(None, None)
                self.load_balance()
                return

            result = calculate_delivery(start, destination)
            if result:
                self.distance_text = f"{result['distance']} km"
                self.price_value = float(result['price'])
                self.ride_fee_text = f"{self.price_value:.2f} THB"
            else:
                self.distance_text = "N/A"
                self.price_value = 0.0
                self.ride_fee_text = "N/A"

            self.load_balance()
            self.setup_map(start, destination)

        except Exception as e:
            print("RideFeeScreen error:", e)

    def load_balance(self):
        try:
            money = file.get_money()
            self.balance_text = f"{float(money):.2f} THB"
        except Exception as e:
            print("Load balance error:", e)
            self.balance_text = "0.00 THB"

    def setup_map(self, start, destination):
        mapview = self.ids.map_view
        
        # 1. ลบหมุดเก่ารอบที่แล้วทิ้งอย่างถูกต้องผ่านตัวแปรอ้างอิงโดยตรง
        if self.current_start_marker:
            mapview.remove_marker(self.current_start_marker)
            self.current_start_marker = None
            
        if self.current_dest_marker:
            mapview.remove_marker(self.current_dest_marker)
            self.current_dest_marker = None

        # ถ้าไม่มีพิกัด ให้รีเซ็ตแผนที่กลับค่ากลาง
        if not start or not destination:
            mapview.center_on(13.7563, 100.5018)
            mapview.zoom = 13
            return

        # 2. สร้างหมุดใหม่และเก็บใส่ตัวแปรประจำคลาสไว้
        self.current_start_marker = MapMarker(lat=start[0], lon=start[1], color=[1, 0, 0, 1])
        self.current_start_marker.anchor_x = 0.5
        self.current_start_marker.anchor_y = 0.0
        mapview.add_marker(self.current_start_marker)

        self.current_dest_marker = MapMarker(lat=destination[0], lon=destination[1], color=[0, 1, 0, 1])
        self.current_dest_marker.anchor_x = 0.5
        self.current_dest_marker.anchor_y = 0.0
        mapview.add_marker(self.current_dest_marker)

        # 3. จัดกึ่งกลางแผนที่ให้พอดีกับพิกัดใหม่
        center_lat = (start[0] + destination[0]) / 2
        center_lon = (start[1] + destination[1]) / 2
        mapview.center_on(center_lat, center_lon)
        mapview.zoom = 13
        mapview.trigger_update(False)

    def on_continue(self):
        role = file.get_role()
        
        if role == "customer" and self.price_value > 0:
            try:
                current_cust_money = float(file.get_money())
                if current_cust_money >= self.price_value:
                    # 1. หักเงินลูกค้า
                    file.change_money(-self.price_value)
                    
                    # 2. เพิ่มเงินให้ไรเดอร์
                    rider_email = getattr(self.manager, "current_rider_email", None)
                    if rider_email:
                        rider_data = database.search(rider_email)
                        if rider_data:
                            current_rider_money = float(rider_data.get("money", 0))
                            new_rider_money = current_rider_money + self.price_value
                            database.update_column(rider_email, "money", new_rider_money)
                            print(f"Successfully transferred {self.price_value} THB to rider: {rider_email}")
                        else:
                            print(f"Rider email {rider_email} not found in database.")
                    else:
                        print("Warning: current_rider_email not found in manager!")
                    
                    print("Payment processed successfully!")
                else:
                    print("Warning: Customer money is not enough!")
            except Exception as e:
                print("Error processing payment:", e)

        self.manager.current = "rating"
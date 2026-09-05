import json
import socket
import threading
from math import atan2, cos, degrees, radians, sin

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import PopMatrix, PushMatrix, Rotate
from kivy.properties import NumericProperty, StringProperty
from kivy.uix.button import Button
from kivy.uix.label import Label  # นำเข้า Label สำหรับแสดงข้อความเรตติ้ง
from kivy.uix.screenmanager import Screen
from kivy.utils import platform
from kivy_garden.mapview import MapMarker

from functions import file, database  # นำเข้า database มาใช้งานด้วย

if platform == "android":
    from android.runnable import run_on_ui_thread
else:
    def run_on_ui_thread(func):
        return func


class RotatableMarker(MapMarker):
    angle = NumericProperty(0)

    def __init__(self, **kwargs):
        kwargs.setdefault("source", "images/arrow.png")
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.width = 50
        self.height = 50

        with self.canvas.before:
            self.push = PushMatrix()
            self.rotate = Rotate(angle=0, origin=self.center)

        with self.canvas.after:
            self.pop = PopMatrix()

        self.bind(
            pos=self.update_rotation,
            size=self.update_rotation,
            angle=self.update_rotation,
        )

    def update_rotation(self, *args):
        self.rotate.origin = self.center
        self.rotate.angle = self.angle


class TrackingMap(Screen):
    email = StringProperty("")
    role = StringProperty("")
    location_text = StringProperty("Waiting for location...")
    rider_rating_text = StringProperty("Rider Rating: -")  # ตัวแปรสำหรับแสดงเรตติ้งไรเดอร์
    bearing = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.marker = None
        self.start_marker = None
        self.dest_marker = None
        self.finish_btn = None
        self.rating_label = None  # ตัวแปรเก็บ Widget แสดงเรตติ้ง

        self.location_manager = None
        self.listener = None
        self.prev_lat = None
        self.prev_lon = None
        self.gps_centered = False

        self.current_lat = 13.7563
        self.current_lon = 100.5018

        self.udp_sock = None
        self.is_listening = False
        self.periodic_event = None

    def on_enter(self):
        print("ENTER TRACKING MAP")
        self.role = file.get_role()
        self.gps_centered = False

        # เคลียร์หมุดเก่าทิ้งก่อนทุกครั้งที่เข้าหน้าจอ
        mapview = self.ids.mapview
        if self.start_marker:
            mapview.remove_marker(self.start_marker)
            self.start_marker = None
        if self.dest_marker:
            mapview.remove_marker(self.dest_marker)
            self.dest_marker = None

        self.setup_route_markers()
        self.start_listening_udp()

        if self.role == "rider":
            self.update_location(13.7563, 100.5018)
            self.add_finish_button()
            self.remove_rider_rating_display()  # ไรเดอร์ไม่ต้องเห็นเรตติ้งตัวเองตรงนี้

            if platform == "android" and not self.listener:
                self.start_gps()

            if not self.periodic_event:
                self.periodic_event = Clock.schedule_interval(
                    self.send_periodic_location, 1.0
                )
        else:
            self.send_route_to_rider()
            self.add_rider_rating_display()  # แสดงเรตติ้งให้ลูกค้าเห็น
            
            # เผื่อกรณีมีอีเมลไรเดอร์ค้างอยู่แล้ว ให้โหลดเรตติ้งมารอเลย
            rider_email = getattr(self.manager, "current_rider_email", "")
            if rider_email:
                self.update_rider_rating_ui(rider_email)

    def on_leave(self):
        print("LEAVING TRACKING MAP")
        self.is_listening = False
        if self.periodic_event:
            self.periodic_event.cancel()
            self.periodic_event = None
        
        self.remove_finish_button()
        self.remove_rider_rating_display()

    def add_rider_rating_display(self):
        if self.rating_label:
            return
        
        # สร้าง Label แสดงเรตติ้งไว้ที่ด้านล่างจอ เปลี่ยนสีเป็นสีดำ (0, 0, 0, 1)
        self.rating_label = Label(
            text=self.rider_rating_text,
            size_hint=(None, None),
            size=(250, 40),
            pos_hint={"center_x": 0.5, "y": 0.05},
            color=(0, 0, 0, 1),  # เปลี่ยนสีตัวอักษรเป็นสีดำที่นี่ครับ
            font_size=18
        )
        # ผูก bind กับตัวแปร rider_rating_text เพื่อให้ข้อความอัปเดตตามอัตโนมัติ
        self.bind(rider_rating_text=self.rating_label.setter('text'))
        self.add_widget(self.rating_label)

    def remove_rider_rating_display(self):
        if self.rating_label:
            self.remove_widget(self.rating_label)
            self.rating_label = None

    def update_rider_rating_ui(self, rider_email):
        """ดึงข้อมูลจาก database มาคำนวณเรตติ้งเฉลี่ยของไรเดอร์"""
        try:
            user_data = database.search(rider_email)
            if user_data:
                sum_rating = user_data.get("sum_rating", 0)
                rating_time = user_data.get("rating_time", 0)
                
                if rating_time > 0:
                    avg_rating = sum_rating / rating_time
                    self.rider_rating_text = f"Rider Rating: {avg_rating:.1f} / 5.0 ({rating_time} reviews)"
                else:
                    self.rider_rating_text = "Rider Rating: No reviews yet"
            else:
                self.rider_rating_text = "Rider Rating: - "
        except Exception as e:
            print("Error fetching rider rating:", e)
            self.rider_rating_text = "Rider Rating: Error"

    def add_finish_button(self):
        if self.finish_btn:
            return
        
        self.finish_btn = Button(
            text="Finish",
            size_hint=(None, None),
            size=(180, 50),
            pos_hint={"center_x": 0.5, "y": 0.05},
            background_color=(0.1, 0.8, 0.1, 1),
            color=(1, 1, 1, 1)
        )
        self.finish_btn.bind(on_release=self.on_empty_click)
        self.add_widget(self.finish_btn)

    def remove_finish_button(self):
        if self.finish_btn:
            self.remove_widget(self.finish_btn)
            self.finish_btn = None

    def on_empty_click(self, instance):
        print("Finish button clicked by rider!")
        
        def _send_finish():
            try:
                payload = json.dumps({
                    "type": "FINISH_RIDE",
                    "rider_email": file.read_email()
                }).encode("utf-8")

                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.sendto(payload, ("255.255.255.255", 5001))
                sock.close()
            except Exception as e:
                print("Error sending finish ride:", e)

        threading.Thread(target=_send_finish, daemon=True).start()
        Clock.schedule_once(lambda dt: setattr(self.manager, "current", "rating"))

    def setup_route_markers(self):
        mapview = self.ids.mapview

        if self.start_marker:
            mapview.remove_marker(self.start_marker)
            self.start_marker = None
        if self.dest_marker:
            mapview.remove_marker(self.dest_marker)
            self.dest_marker = None

        start_coords = getattr(self.manager, "rider_start_coords", None)
        dest_coords = getattr(self.manager, "rider_dest_coords", None)

        if start_coords:
            lat, lon = start_coords
            self.start_marker = MapMarker(lat=lat, lon=lon, color=[1, 0, 0, 1])
            self.start_marker.anchor_x = 0.5
            self.start_marker.anchor_y = 0.0
            mapview.add_marker(self.start_marker)

        if dest_coords:
            lat, lon = dest_coords
            self.dest_marker = MapMarker(lat=lat, lon=lon, color=[0, 1, 0, 1])
            self.dest_marker.anchor_x = 0.5
            self.dest_marker.anchor_y = 0.0
            mapview.add_marker(self.dest_marker)

    def send_periodic_location(self, dt):
        if self.role == "rider" and self.current_lat and self.current_lon:
            self.broadcast_location_to_customer(
                self.current_lat, self.current_lon, self.bearing
            )

    def send_route_to_rider(self):
        start_coords = getattr(self.manager, "rider_start_coords", None)
        dest_coords = getattr(self.manager, "rider_dest_coords", None)

        if not start_coords or not dest_coords:
            return

        def _send():
            try:
                payload = json.dumps({
                    "type": "ROUTE_INFO",
                    "start_coords": start_coords,
                    "dest_coords": dest_coords,
                    "rider_email": file.read_email()
                }).encode("utf-8")

                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.sendto(payload, ("255.255.255.255", 5001))
                sock.close()
            except Exception:
                pass

        threading.Thread(target=_send, daemon=True).start()

    def start_listening_udp(self):
        if self.is_listening:
            return

        self.is_listening = True

        def _listen():
            try:
                self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.udp_sock.bind(("", 5001))
                self.udp_sock.settimeout(1.0)

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

                        if msg_type == "LOCATION_UPDATE" and self.role == "customer":
                            lat = msg.get("lat")
                            lon = msg.get("lon")
                            bearing = msg.get("bearing", 0)
                            
                            rider_email = msg.get("rider_email")
                            if rider_email:
                                self.manager.current_rider_email = rider_email
                                Clock.schedule_once(lambda dt: self.update_rider_rating_ui(rider_email))

                            Clock.schedule_once(
                                lambda dt: self.apply_rider_location(lat, lon, bearing)
                            )

                        elif msg_type == "ROUTE_INFO" and self.role == "rider":
                            start_coords = msg.get("start_coords")
                            dest_coords = msg.get("dest_coords")
                            
                            if "rider_email" in msg:
                                self.manager.current_customer_email = msg.get("rider_email")

                            Clock.schedule_once(
                                lambda dt: self.apply_route_info(start_coords, dest_coords)
                            )

                        elif msg_type == "FINISH_RIDE" and self.role == "customer":
                            if "rider_email" in msg:
                                self.manager.current_rider_email = msg.get("rider_email")

                            Clock.schedule_once(
                                lambda dt: setattr(self.manager, "current", "ride_fee")
                            )

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

    def apply_route_info(self, start_coords, dest_coords):
        if start_coords and dest_coords:
            current_start = getattr(self.manager, "rider_start_coords", None)
            current_dest = getattr(self.manager, "rider_dest_coords", None)

            if current_start != start_coords or current_dest != dest_coords:
                self.manager.rider_start_coords = start_coords
                self.manager.rider_dest_coords = dest_coords
                self.setup_route_markers()

    @run_on_ui_thread
    def start_gps(self):
        from jnius import PythonJavaClass, autoclass, java_method

        LocationManager = autoclass("android.location.LocationManager")
        Context = autoclass("android.content.Context")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Looper = autoclass("android.os.Looper")

        class LocationListener(PythonJavaClass):
            __javainterfaces__ = ["android/location/LocationListener"]
            __javacontext__ = "app"

            @java_method("(Ljava/util/List;)V")
            def onLocationChanged(self, locations):
                if locations.size() == 0:
                    return
                location = locations.get(0)
                lat = float(location.getLatitude())
                lon = float(location.getLongitude())

                Clock.schedule_once(
                    lambda dt: self.owner.update_location(lat, lon)
                )

            @java_method("(Ljava/lang/String;)V")
            def onProviderEnabled(self, provider):
                pass

            @java_method("(Ljava/lang/String;)V")
            def onProviderDisabled(self, provider):
                pass

            @java_method("(Ljava/lang/String;ILandroid/os/Bundle;)V")
            def onStatusChanged(self, provider, status, extras):
                pass

        activity = PythonActivity.mActivity
        self.location_manager = activity.getSystemService(Context.LOCATION_SERVICE)
        self.listener = LocationListener()
        self.listener.owner = self

        self.location_manager.requestLocationUpdates(
            LocationManager.GPS_PROVIDER,
            1000,
            1,
            self.listener,
            Looper.getMainLooper(),
        )

    def broadcast_location_to_customer(self, lat, lon, bearing):
        def _send():
            try:
                payload = json.dumps({
                    "type": "LOCATION_UPDATE",
                    "lat": lat,
                    "lon": lon,
                    "bearing": bearing,
                    "rider_email": file.read_email()
                }).encode("utf-8")

                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.sendto(payload, ("255.255.255.255", 5001))
                sock.close()
            except Exception:
                pass

        threading.Thread(target=_send, daemon=True).start()

    def apply_rider_location(self, lat, lon, bearing):
        self.bearing = bearing
        self.update_map(lat, lon)

        if not self.gps_centered:
            self.ids.mapview.center_on(lat, lon)
            self.gps_centered = True

    def update_location(self, lat, lon):
        self.current_lat = lat
        self.current_lon = lon

        if lat == self.prev_lat and lon == self.prev_lon:
            return

        if self.prev_lat is not None:
            self.bearing = self.calculate_bearing(
                self.prev_lat, self.prev_lon, lat, lon
            )

        self.prev_lat = lat
        self.prev_lon = lon

        self.update_map(lat, lon)

        if not self.gps_centered:
            self.ids.mapview.center_on(lat, lon)
            self.gps_centered = True

        if self.role == "rider":
            self.broadcast_location_to_customer(lat, lon, self.bearing)

    def update_map(self, lat, lon):
        mapview = self.ids.mapview

        self.location_text = f"Rider Position:\nLat: {lat:.6f}, Lon: {lon:.6f}"

        if self.marker is None:
            self.marker = RotatableMarker(lat=lat, lon=lon)
            mapview.add_marker(self.marker)
            mapview.center_on(lat, lon)
            mapview.zoom = 16
        else:
            self.marker.lat = lat
            self.marker.lon = lon
            mapview.trigger_update(False)

        kivy_angle = (360 - self.bearing) % 360
        Animation.cancel_all(self.marker, "angle")
        Animation(angle=kivy_angle, duration=0.15).start(self.marker)

    def calculate_bearing(self, lat1, lon1, lat2, lon2):
        lat1, lat2 = radians(lat1), radians(lat2)
        dlon = radians(lon2 - lon1)
        x = sin(dlon) * cos(lat2)
        y = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dlon)
        return (degrees(atan2(x, y)) + 360) % 360

    def go_to(self, destination):
        self.manager.current = destination

    def back(self):
        if file.get_role() == "customer":
            self.go_to("home_customer")
        elif file.get_role() == "rider":
            self.go_to("home_rider")
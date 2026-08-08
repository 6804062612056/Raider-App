from kivy.uix.screenmanager import Screen
from kivy_garden.mapview import MapMarker
from kivy.graphics import PushMatrix, PopMatrix, Rotate
from kivy.properties import NumericProperty, StringProperty
from kivy.utils import platform
from kivy.clock import Clock
from kivy.animation import Animation
from math import radians, degrees, atan2, sin, cos

if platform == "android":
    from android.runnable import run_on_ui_thread
else:
    def run_on_ui_thread(func):
        return func


class RotatableMarker(MapMarker):
    angle = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.source = "images/arrow.png"
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
            angle=self.update_rotation
        )

    def update_rotation(self, *args):
        self.rotate.origin = self.center
        self.rotate.angle = self.angle


class Map(Screen):
    location_text = StringProperty(
        "Latitude: 13.756300\nLongitude: 100.501800"
    )
    bearing = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.marker = None
        self.location_manager = None
        self.listener = None
        self.prev_lat = None
        self.prev_lon = None

        # ใช้เช็กว่าแผนที่เคยแพนไป GPS จริงแล้วหรือยัง
        self.gps_centered = False

    def on_enter(self):
        print("ENTER MAP")

        # เริ่มต้นที่ตำแหน่งเริ่มต้น
        self.gps_centered = False
        self.prev_lat = None
        self.prev_lon = None

        self.update_location(13.7563, 100.5018)

        if platform == "android":
            self.start_gps()

    @run_on_ui_thread
    def start_gps(self):
        from jnius import autoclass, PythonJavaClass, java_method

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

                print("LOCATION:", lat, lon)

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

        self.location_manager = activity.getSystemService(
            Context.LOCATION_SERVICE
        )

        self.listener = LocationListener()
        self.listener.owner = self

        self.location_manager.requestLocationUpdates(
            LocationManager.GPS_PROVIDER,
            1000,
            1,
            self.listener,
            Looper.getMainLooper()
        )

        print("GPS START")

    def update_location(self, lat, lon):

        if lat == self.prev_lat and lon == self.prev_lon:
            return

        if self.prev_lat is not None:
            self.bearing = self.calculate_bearing(
                self.prev_lat,
                self.prev_lon,
                lat,
                lon
            )

        self.prev_lat = lat
        self.prev_lon = lon

        self.update_map(lat, lon)

        # แพนไปตำแหน่ง GPS จริงแค่ครั้งแรก
        if not self.gps_centered:
            self.ids.mapview.center_on(lat, lon)
            self.gps_centered = True

    def update_map(self, lat, lon):
        mapview = self.ids.mapview

        self.location_text = (
            f"Latitude: {lat:.6f}\n"
            f"Longitude: {lon:.6f}"
        )

        if self.marker is None:
            self.marker = RotatableMarker(lat=lat, lon=lon)
            mapview.add_marker(self.marker)
            mapview.center_on(lat, lon)
            mapview.zoom = 15
        else:
            self.marker.lat = lat
            self.marker.lon = lon

        # แปลง GPS bearing ให้ตรงกับ Kivy angle
        kivy_angle = (360 - self.bearing) % 360

        Animation.cancel_all(self.marker, "angle")
        Animation(
            angle=kivy_angle,
            duration=0.15
        ).start(self.marker)

    def calculate_bearing(self, lat1, lon1, lat2, lon2):
        lat1 = radians(lat1)
        lat2 = radians(lat2)
        dlon = radians(lon2 - lon1)

        x = sin(dlon) * cos(lat2)
        y = (
            cos(lat1) * sin(lat2)
            - sin(lat1) * cos(lat2) * cos(dlon)
        )

        return (degrees(atan2(x, y)) + 360) % 360

    def on_leave(self):
        if self.location_manager and self.listener:
            self.location_manager.removeUpdates(self.listener)
            print("GPS STOP")

    def go_to(self, destination):
        self.manager.current = destination
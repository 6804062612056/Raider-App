import threading
import requests

# ใช้ Session เพื่อ Reuse Connection ลดเวลาสถาปนา TCP ตอนยิงเรียก OSRM
session = requests.Session()


def calculate_delivery(start, destination):
    """
    คำนวณระยะทาง เวลา และค่าบริการ จากพิกัด (lat, lon)
    ด้วยเรตราคาค่าส่งพัสดุ/เดลิเวอรีมาตรฐานในประเทศไทย
    """
    try:
        start_lat, start_lon = start
        end_lat, end_lon = destination

        url = (
            "https://router.project-osrm.org/route/v1/driving/"
            f"{start_lon},{start_lat};{end_lon},{end_lat}?overview=false"
        )

        # ตั้ง timeout เหลือ 5 วินาที เพื่อไม่ให้แอปรอนานเกินไปหาก Server ตอบสนองช้า
        response = session.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != "Ok":
            raise Exception("หาเส้นทางไม่สำเร็จ")

        route = data["routes"][0]
        distance_km = route["distance"] / 1000
        duration_min = route["duration"] / 60

        # --- อัตราค่าบริการขนส่งพัสดุ/เดลิเวอรีมาตรฐานในไทย ---
        if distance_km <= 3:
            price = 40
        elif distance_km <= 15:
            price = 40 + (distance_km - 3) * 9
        elif distance_km <= 30:
            price = 40 + (12 * 9) + (distance_km - 15) * 8
        else:
            price = 40 + (12 * 9) + (15 * 8) + (distance_km - 30) * 7

        return {
            "distance": round(distance_km, 2),
            "duration": round(duration_min, 1),
            "price": round(price),
        }
    except Exception as e:
        print("Calculation delivery error:", e)
        return None


def calculate_delivery_async(start, destination, on_success=None, on_failure=None):
    """
    ฟังก์ชันช่วยเรียก calculate_delivery ใน Background Thread
    เพื่อไม่ให้หน้าจอ Kivy หน่วงหรือค้างขณะรอคำนวณระยะทาง
    """
    def _worker():
        result = calculate_delivery(start, destination)
        if result is not None:
            if on_success:
                on_success(result)
        else:
            if on_failure:
                on_failure()

    threading.Thread(target=_worker, daemon=True).start()
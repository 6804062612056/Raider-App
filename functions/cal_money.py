import requests

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

        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != "Ok":
            raise Exception("หาเส้นทางไม่สำเร็จ")

        route = data["routes"][0]
        distance_km = route["distance"] / 1000
        duration_min = route["duration"] / 60

        # --- อัตราค่าบริการขนส่งพัสดุ/เดลิเวอรีมาตรฐานในไทย ---
        # 3 กม. แรก: ค่าบริการเริ่มต้น 40 บาท
        # กม.ที่ 3 - 15: กม.ละ 9 บาท
        # กม.ที่ 15 - 30: กม.ละ 8 บาท
        # มากกว่า 30 กม. ขึ้นไป: กม.ละ 7 บาท (บวกค่าบริการระยะไกลเพิ่มความคุ้มค่าให้ไรเดอร์)
        
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
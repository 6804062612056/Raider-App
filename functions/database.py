import threading
import requests

URL = "https://bdjpukljrkxhdzvrxrvh.supabase.co/rest/v1/Userdata"
API_KEY = "sb_publishable_N0tPIPFIozXQe-v8wAFskw_ukG67uvK"

HEADERS = {
    "apikey": API_KEY,
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ใช้ Session เพื่อ Reuse TCP Connection ช่วยให้การส่ง HTTP Request ครั้งถัดๆ ไปเร็วขึ้นมาก
session = requests.Session()
session.headers.update(HEADERS)


def _async_worker(func, callback, *args, **kwargs):
    """Worker สำหรับรัน Network Request ใน Background Thread"""
    result = func(*args, **kwargs)
    if callback:
        callback(result)


def run_async(func, *args, callback=None, **kwargs):
    """เรียกใช้ฟังก์ชันใน database.py แบบ Async ไม่บล็อก UI"""
    threading.Thread(
        target=_async_worker,
        args=(func, callback, *args),
        kwargs=kwargs,
        daemon=True
    ).start()


def insert(email, firstname, lastname, password, role, money, rating_time, sum_rating):
    data = {
        "email": email,
        "firstname": firstname,
        "lastname": lastname,
        "password": password,
        "role": role,
        "money": money,
        "rating_time": rating_time,
        "sum_rating": sum_rating
    }
    try:
        response = session.post(URL, json=data)
        if response.status_code in (200, 201):
            print("INSERT: Success")
            return True
        else:
            print(f"INSERT: Failed ({response.status_code}) - {response.text}")
            return False
    except Exception as e:
        print("INSERT Exception:", e)
        return False


def delete(email):
    try:
        # ลบโดยตรงด้วย Filter query parameter โดยไม่ต้อง SELECT มาเช็คก่อนเพื่อลด Round-trip Time
        headers = HEADERS.copy()
        headers["Prefer"] = "return=representation"
        response = session.delete(URL, headers=headers, params={"email": f"eq.{email}"})
        
        if response.status_code in (200, 204):
            deleted_data = response.json()
            if not deleted_data:
                print("DELETE: Not Found")
                return False
            print("DELETE: Success")
            return True
        else:
            print(f"DELETE: Failed ({response.status_code}) - {response.text}")
            return False
    except Exception as e:
        print("DELETE Exception:", e)
        return False


def search(email):
    try:
        response = session.get(URL, params={"email": f"eq.{email}"})
        if response.status_code != 200:
            print(f"SEARCH: Failed ({response.status_code}) - {response.text}")
            return None

        data = response.json()
        return data[0] if data else None
    except Exception as e:
        print("SEARCH Exception:", e)
        return None


def select_all():
    try:
        response = session.get(URL)
        if response.status_code != 200:
            print(f"SELECT: Failed ({response.status_code}) - {response.text}")
            return None

        data = response.json()
        if not data:
            print("SELECT: No Data")
            return []

        print("SELECT: Success")
        return data
    except Exception as e:
        print("SELECT Exception:", e)
        return None


def update_column(email, column_name, value):
    headers = {"Prefer": "return=representation"}
    params = {"email": f"eq.{email}"}
    data = {column_name: value}

    try:
        response = session.patch(URL, headers=headers, params=params, json=data)
        if response.status_code in (200, 204):
            print(f"UPDATE {column_name}: Success")
            return True
        else:
            print(f"UPDATE {column_name}: Failed ({response.status_code}) - {response.text}")
            return False
    except Exception as e:
        print(f"UPDATE {column_name} Exception:", e)
        return False
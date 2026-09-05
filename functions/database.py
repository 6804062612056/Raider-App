import requests

URL = "https://bdjpukljrkxhdzvrxrvh.supabase.co/rest/v1/Userdata"
API_KEY = "sb_publishable_N0tPIPFIozXQe-v8wAFskw_ukG67uvK"

HEADERS = {
    "apikey": API_KEY,
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

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
    response = requests.post(URL, headers=HEADERS, json=data)
    if response.status_code in (200, 201):
        print("INSERT: Success")
        print("Email:", email)
        print("Firstname:", firstname)
        print("Lastname:", lastname)
        print("Role:", role)
        print("Money:", money)
        print("rating time", rating_time)
        print("sum rating", sum_rating)
    else:
        print("INSERT: Failed")
        print("Status:", response.status_code)
        print("Error:", response.text)

def delete(email):
    check = requests.get(
        URL,
        headers=HEADERS,
        params={"email": f"eq.{email}"}
    )
    if check.status_code != 200:
        print("DELETE: Failed to search")
        print("Status:", check.status_code)
        print("Error:", check.text)
        return
    data = check.json()
    if len(data) == 0:
        print("DELETE: Not Found")
        return
    response = requests.delete(
        URL,
        headers=HEADERS,
        params={"email": f"eq.{email}"}
    )
    if response.status_code in (200, 204):
        print("DELETE: Success")
    else:
        print("DELETE: Failed")
        print("Status:", response.status_code)
        print("Error:", response.text)

def search(email):
    params = {
        "email": f"eq.{email}"
    }

    response = requests.get(
        URL,
        headers=HEADERS,
        params=params
    )

    if response.status_code != 200:
        print("SEARCH: Failed")
        print("Status:", response.status_code)
        print("Error:", response.text)
        return None

    data = response.json()

    if len(data) == 0:
        return None

    return data[0]

def select_all():
    response = requests.get(
        URL,
        headers=HEADERS
    )

    if response.status_code != 200:
        print("SELECT: Failed")
        print("Status:", response.status_code)
        print("Error:", response.text)
        return None

    data = response.json()

    if len(data) == 0:
        print("SELECT: No Data")
        return []

    print("SELECT: Success")
    return data

def update_column(email, column_name, value):
    """
    อัปเดตค่าเฉพาะคอลัมน์ที่ต้องการของผู้ใช้ผ่านทาง Email
    เช่น update_column("user@email.com", "money", 500.0)
    """
    headers = HEADERS.copy()
    # กำหนดให้ Supabase คืนค่าข้อมูลที่ถูกอัปเดตกลับมาด้วย (เพื่อเช็คความถูกต้อง)
    headers["Prefer"] = "return=representation"

    params = {
        "email": f"eq.{email}"
    }
    
    data = {
        column_name: value
    }

    response = requests.patch(
        URL,
        headers=headers,
        params=params,
        json=data
    )

    if response.status_code in (200, 204):
        print(f"UPDATE {column_name}: Success")
        return True
    else:
        print(f"UPDATE {column_name}: Failed")
        print("Status:", response.status_code)
        print("Error:", response.text)
        return False
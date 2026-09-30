import threading
from kivy.clock import Clock
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import BooleanProperty

from functions import database


class ClickableLabel(ButtonBehavior, Label):
    pass


class UserList(Screen):
    is_loading = BooleanProperty(False)
    refresh_event = None

    def on_enter(self, *args):
        self.load_users()
        if not self.refresh_event:
            self.refresh_event = Clock.schedule_interval(lambda dt: self.load_users(), 5)

    def on_leave(self, *args):
        if self.refresh_event:
            self.refresh_event.cancel()
            self.refresh_event = None

    def go_to(self, destination):
        self.manager.current = destination

    def load_users(self):
        if self.is_loading:
            return
        self.is_loading = True
        threading.Thread(target=self._fetch_users_async, daemon=True).start()

    def _fetch_users_async(self):
        data = database.select_all()
        Clock.schedule_once(lambda dt: self._update_ui(data))

    def _update_ui(self, data):
        container = self.ids.user_container
        container.clear_widgets()

        if data:
            for user in data:
                email = user.get('email', '')
                rating_time = user.get('rating_time', 0)
                sum_rating = user.get('sum_rating', 0)
                rating = sum_rating / rating_time if rating_time > 0 else 0

                text_content = (
                    f"Name : {user.get('firstname', '')} {user.get('lastname', '')}\n"
                    f"Role : {user.get('role', '')}\n"
                    f"Email : {email}\n"
                    f"Password : {user.get('password', '')}\n"
                    f"Money : {user.get('money', 0)}\n"
                    f"rating time : {rating_time}\n"
                    f"sum rating : {sum_rating}\n"
                    f"rating : {rating:.1f}"
                )

                # สร้าง Box สำหรับแต่ละ User พร้อมระยะห่างและเส้นขอบใต้
                user_box = BoxLayout(
                    orientation='horizontal',
                    size_hint_y=None,
                    height="190dp",
                    padding=["10dp", "10dp", "10dp", "15dp"],
                    spacing="10dp"
                )

                # ข้อความรายละเอียด User (กดคลิกเพื่อแก้ไขได้)
                user_label = ClickableLabel(
                    text=text_content,
                    color=(0, 0, 0, 1),
                    halign="left",
                    valign="top",
                    font_size="14sp"
                )
                user_label.bind(size=lambda instance, value: setattr(instance, 'text_size', (value[0], None)))
                user_label.bind(on_press=lambda instance, u=user: self.open_edit_popup(u))

                # ปุ่ม Delete สีดำ ทางด้านขวา
                delete_btn = Button(
                    text="Delete",
                    size_hint=(None, None),
                    size=("75dp", "40dp"),
                    pos_hint={"center_y": 0.5},
                    background_normal='',
                    background_color=(0, 0, 0, 1),
                    color=(1, 1, 1, 1),
                    font_size="14sp"
                )

                delete_btn.bind(on_press=lambda instance, e=email: self.delete_user(e))

                user_box.add_widget(user_label)
                user_box.add_widget(delete_btn)

                container.add_widget(user_box)

        self.is_loading = False

    def delete_user(self, email):
        def _delete_async():
            success = database.delete(email)
            if success:
                Clock.schedule_once(lambda dt: self.load_users())

        threading.Thread(target=_delete_async, daemon=True).start()

    def open_edit_popup(self, user):
        """Popup แก้ไขข้อมูลสำหรับหน้าจอโทรศัพท์ (มี ScrollView และปุ่มขนาดกดง่าย)"""
        email = user.get('email', '')

        # Layout หลักของ Popup
        main_layout = BoxLayout(orientation='vertical', spacing="10dp", padding="10dp")

        # ScrollView ป้องกันกรณีหน้าจอโทรศัพท์เล็กลงแล้วมองไม่เห็นฟิลด์ล่างๆ
        scroll = ScrollView(size_hint=(1, 1))
        
        # ใช้ 1 Column เหมาะกับหน้าจอแนวตั้งของมือถือ
        form_layout = GridLayout(cols=1, spacing="8dp", size_hint_y=None)
        form_layout.bind(minimum_height=form_layout.setter('height'))

        inputs = {}
        fields = [
            ('firstname', 'First Name'),
            ('lastname', 'Last Name'),
            ('password', 'Password'),
            ('role', 'Role'),
            ('money', 'Money')
        ]

        for key, title in fields:
            # หัวข้อฟิลด์
            lbl = Label(
                text=title,
                size_hint_y=None,
                height="25dp",
                color=(1, 1, 1, 1),
                halign="left",
                font_size="14sp"
            )
            lbl.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0], None)))
            form_layout.add_widget(lbl)

            # ช่องกรอกข้อมูล ปรับความสูงให้พิมพ์บนมือถือง่ายขึ้น
            txt_input = TextInput(
                text=str(user.get(key, '')),
                multiline=False,
                size_hint_y=None,
                height="42dp",
                font_size="15sp",
                padding=["10dp", "10dp"]
            )
            inputs[key] = txt_input
            form_layout.add_widget(txt_input)

        scroll.add_widget(form_layout)
        main_layout.add_widget(scroll)

        # ปุ่มกด Save / Cancel สำหรับมือถือ
        btn_box = BoxLayout(size_hint_y=None, height="45dp", spacing="10dp")
        save_btn = Button(
            text="Save",
            background_normal='',
            background_color=(0.1, 0.7, 0.3, 1),
            font_size="16sp",
            bold=True
        )
        cancel_btn = Button(
            text="Cancel",
            background_normal='',
            background_color=(0.8, 0.2, 0.2, 1),
            font_size="16sp"
        )

        btn_box.add_widget(cancel_btn)
        btn_box.add_widget(save_btn)
        main_layout.add_widget(btn_box)

        # ปรับขนาด Popup ให้เต็มพื้นที่หน้าจอมือถือ (92% width, 85% height)
        popup = Popup(
            title=f"Edit: {email}",
            content=main_layout,
            size_hint=(0.92, 0.85),
            title_size="18sp"
        )

        def save_changes(instance):
            popup.dismiss()
            def _update_async():
                for field_key, input_widget in inputs.items():
                    new_val = input_widget.text.strip()
                    original_val = str(user.get(field_key, ''))
                    if new_val != original_val:
                        if field_key == 'money':
                            try:
                                new_val = float(new_val) if '.' in new_val else int(new_val)
                            except ValueError:
                                pass
                        database.update_column(email, field_key, new_val)
                Clock.schedule_once(lambda dt: self.load_users())

            threading.Thread(target=_update_async, daemon=True).start()

        save_btn.bind(on_press=save_changes)
        cancel_btn.bind(on_press=popup.dismiss)

        popup.open()
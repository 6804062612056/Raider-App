from kivy.uix.modalview import ModalView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, RoundedRectangle

class ModernDialog(ModalView):
    def __init__(self, message="เกิดข้อผิดพลาด", title="แจ้งเตือน", screen_manager=None, target_screen=None, on_dismiss_callback=None, **kwargs):
        super().__init__(**kwargs)
        # ให้ ModalView คลุมเต็มหน้าจอเพื่อทำฉากหลังโปร่งแสง
        self.size_hint = (1, 1)
        
        # ลบภาพพื้นหลังเริ่มต้นของระบบ Kivy ออกทั้งหมดเพื่อตัดขอบดำ
        self.background = ''
        self.background_color = (0, 0, 0, 0.6)  # ฉากหลังมืดโปร่งแสง
        self.auto_dismiss = False

        self.screen_manager = screen_manager
        self.target_screen = target_screen
        self.on_dismiss_callback = on_dismiss_callback

        # กล่องการ์ดหลัก (Modern Card Container) จัดให้อยู่ตรงกลางจอ
        card = BoxLayout(
            orientation='vertical',
            padding=[24, 24, 24, 24],
            spacing=20,
            size_hint=(0.85, None),
            height='220dp',
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )

        with card.canvas.before:
            # พื้นหลังการ์ดสีขาวสะอาดตา ขอบโค้งมนเนียนๆ
            Color(1, 1, 1, 1)
            self.card_rect = RoundedRectangle(pos=card.pos, size=card.size, radius=[24,])

        card.bind(pos=lambda inst, val: setattr(self.card_rect, 'pos', val))
        card.bind(size=lambda inst, val: setattr(self.card_rect, 'size', val))

        # หัวข้อ Dialog
        title_label = Label(
            text=title,
            font_size='20sp',
            bold=True,
            color=(0.1, 0.1, 0.1, 1),
            size_hint_y=None,
            height='30sp',
            halign='center',
            valign='middle'
        )
        title_label.bind(size=title_label.setter('text_size'))
        card.add_widget(title_label)

        # ข้อความรายละเอียด
        msg_label = Label(
            text=message,
            font_size='15sp',
            color=(0.4, 0.4, 0.4, 1),
            halign='center',
            valign='middle'
        )
        msg_label.bind(size=msg_label.setter('text_size'))
        card.add_widget(msg_label)

        # ปุ่มปิดดีไซน์พรีเมียม
        close_btn = Button(
            text="ตกลง",
            size_hint=(1, None),
            height='48dp',
            font_size='16sp',
            bold=True,
            color=(0.1, 0.1, 0.1, 1),
            background_normal='',
            background_down='',
            background_color=(0, 0, 0, 0)
        )

        with close_btn.canvas.before:
            self.btn_color = Color(1, 0.85, 0.2, 1)  # โทนสีเหลืองพรีเมียม
            self.btn_rect = RoundedRectangle(pos=close_btn.pos, size=close_btn.size, radius=[16,])

        close_btn.bind(pos=lambda inst, val: setattr(self.btn_rect, 'pos', val))
        close_btn.bind(size=lambda inst, val: setattr(self.btn_rect, 'size', val))
        
        def on_btn_state(instance, value):
            if value == 'down':
                self.btn_color.rgba = (0.9, 0.72, 0.1, 1)
            else:
                self.btn_color.rgba = (1, 0.85, 0.2, 1)

        close_btn.bind(state=on_btn_state)
        close_btn.bind(on_release=self.dismiss_dialog)
        
        card.add_widget(close_btn)
        self.add_widget(card)

    def dismiss_dialog(self, *args):
        self.dismiss()
        if self.screen_manager and self.target_screen:
            self.screen_manager.current = self.target_screen
        if self.on_dismiss_callback:
            self.on_dismiss_callback()


def show_error_popup(message="เกิดข้อผิดพลาดในการเชื่อมต่อ", screen_manager=None, target_screen=None, on_dismiss_callback=None):
    """
    ฟังก์ชันเรียกใช้งาน Dialog แบบ Custom UI
    """
    dialog = ModernDialog(
        message=message,
        title="Notification",
        screen_manager=screen_manager,
        target_screen=target_screen,
        on_dismiss_callback=on_dismiss_callback
    )
    dialog.open()
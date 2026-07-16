import sys
import os

# Если программа запущена из EXE (PyInstaller), меняем рабочую директорию
if getattr(sys, 'frozen', False):
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(base_dir)

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.progressbar import ProgressBar
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from datetime import datetime
from kivy.core.audio import SoundLoader
import random
import json

Window.size = (400, 600)
Window.clearcolor = (1, 1, 1, 1)

SAVE_FILE = 'save.json'

NEEDS = {
    'banana':     {'icon': 'banana_need.png', 'price': 5, 'text': 'банан',   'sound': 'banana_need_sound.wav'},
    'plum':       {'icon': 'plum_need.png',   'price': 7, 'text': 'слива',   'sound': 'plum_need_sound.wav'},
    'apple':      {'icon': 'apple_need.png',  'price': 6, 'text': 'яблоко',  'sound': 'apple_need_sound.wav'},
    'watermelon': {'icon': 'watermelon_need.png', 'price': 10, 'text': 'арбуз', 'sound': 'watermelon_need_sound.wav'},
    'grape':      {'icon': 'grape_need.png',  'price': 4, 'text': 'виноград','sound': 'grape_need_sound.wav'},
    'shower':     {'icon': 'shower_need.png', 'text': None, 'sound': None}
}

CAT_NEED = {
    'cat': {'icon': 'cat_icon.png', 'text': 'поиграть', 'sound': 'cat_need_sound.wav'}
}


class BurmaldochiApp(App):
    def build(self):
        # Загрузка сохранения
        self.player_name = ""
        self.load_save()

        self.coin_amount_per_click = 10
        self.current_location = 'start'

        self.fruits_inventory = []
        self.active_need = None
        self.need_reminder = None

        # Инициализация всех переменных
        self.thought_bubble = None
        self.need_text_label = None
        self.inventory_bar = None
        self.progress_bar = None
        self.progress_timer = None
        self.progress_value = 0

        self.cat_sprite = None
        self.cat_jump_timer = None

        # Загрузка звуков
        self.bg_sound = SoundLoader.load('background.wav')
        self.click_sound = SoundLoader.load('click_sound.wav')
        self.close_sound = SoundLoader.load('close_sound.wav')
        self.respect_sound = SoundLoader.load('respect_sound.wav')
        self.eat_sound = SoundLoader.load('eat_sound.wav')
        self.wrong_sound = SoundLoader.load('wrong_sound.wav')
        self.shower_done_sound = SoundLoader.load('shower_done_sound.wav')
        self.cat_need_sound = SoundLoader.load('cat_need_sound.wav')
        self.purr_sound = SoundLoader.load('purr_sound.wav')

        if self.bg_sound:
            self.bg_sound.volume = 0.5
            self.bg_sound.loop = True
            self.bg_sound.play()
        if self.click_sound:
            self.click_sound.volume = 1.0

        root = FloatLayout()

        self.full_bg = Image(
            source='background.png', size_hint=(1, 1), pos_hint={'x':0, 'y':0},
            fit_mode='fill'
        )
        root.add_widget(self.full_bg)

        main_layout = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(10),
                                size_hint=(1,1), pos_hint={'x':0, 'y':0})

        # Верхняя белая панель
        top_bar = BoxLayout(size_hint=(1, 0.1), spacing=dp(16))
        with top_bar.canvas.before:
            Color(1,1,1,1)
            self.top_bar_rect = Rectangle(size=top_bar.size, pos=top_bar.pos)
            top_bar.bind(size=self._update_top_bar_rect, pos=self._update_top_bar_rect)

        self.lbl_date = Label(text="", font_size=dp(18), bold=True, color=(0.2,0.2,0.2,1),
                              halign='left', valign='middle', size_hint=(0.6,1))
        self.lbl_date.bind(size=self.lbl_date.setter('text_size'))
        top_bar.add_widget(self.lbl_date)

        self.lbl_coins = Label(text=self._format_coins(self.coins), font_size=dp(20), bold=True,
                               color=(0.1,0.4,0.1,1), halign='right', valign='middle', size_hint=(0.4,1))
        self.lbl_coins.bind(size=self.lbl_coins.setter('text_size'))
        top_bar.add_widget(self.lbl_coins)
        main_layout.add_widget(top_bar)

        # Игровая область
        self.game_area = GameArea(size_hint=(1, 0.7), app=self)
        self.game_area.setup()
        main_layout.add_widget(self.game_area)

        # Нижняя панель
        bottom_bar = FloatLayout(size_hint=(1, 0.15))
        self.btn_dev = Image(
            source='dev_btn.png', size_hint=(None,None), size=(dp(80),dp(80)),
            fit_mode='fill', pos_hint={'x':0.05, 'center_y':0.5}
        )
        self.btn_dev.bind(on_touch_down=self.on_dev_click)
        bottom_bar.add_widget(self.btn_dev)

        self.btn_shop = Image(
            source='shop_btn.png', size_hint=(None,None), size=(dp(80),dp(80)),
            fit_mode='fill', pos_hint={'right':0.95, 'center_y':0.5}
        )
        self.btn_shop.bind(on_touch_down=self.on_shop_click)
        bottom_bar.add_widget(self.btn_shop)
        main_layout.add_widget(bottom_bar)

        root.add_widget(main_layout)
        self.update_date()
        Clock.schedule_once(self.generate_need, 5)

        if self.player_name:
            Clock.schedule_once(lambda dt: self.show_welcome(), 0.5)
        else:
            Clock.schedule_once(lambda dt: self.ask_name(), 1)

        return root

    # ---------- Сохранение и загрузка ----------
    def load_save(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.coins = data.get('coins', 0)
                self.player_name = data.get('name', '')
                self.has_cat = data.get('has_cat', False)
            except Exception as e:
                print(f"Ошибка загрузки: {e}")
                self.coins = 0
                self.player_name = ''
                self.has_cat = False
        else:
            self.coins = 0
            self.player_name = ''
            self.has_cat = False

    def save_save(self):
        data = {
            'name': self.player_name,
            'coins': self.coins,
            'has_cat': self.has_cat
        }
        try:
            with open(SAVE_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            print(f"Сохранение записано: {data}")
        except Exception as e:
            print(f"Ошибка сохранения: {e}")

    def on_stop(self):
        super().on_stop()
        self.save_save()

    # ---------- Запрос имени ----------
    def ask_name(self):
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        content.add_widget(Label(text="Введите ваше имя:", font_size=dp(18)))
        self.name_input = TextInput(text='', multiline=False, font_size=dp(18))
        content.add_widget(self.name_input)
        btn_ok = Button(text='OK', size_hint=(1, 0.3))
        content.add_widget(btn_ok)

        self.name_popup = Popup(title="Добро пожаловать!", content=content,
                                size_hint=(0.8, 0.4), auto_dismiss=False)
        btn_ok.bind(on_release=self.save_name)
        self.name_popup.open()

    def save_name(self, instance):
        name = self.name_input.text.strip()
        if name:
            self.player_name = name
            self.save_save()
            self.name_popup.dismiss()
            Clock.schedule_once(lambda dt: self.show_welcome(), 0.5)
        else:
            self.name_input.hint_text = "Имя не может быть пустым"

    def show_welcome(self):
        if self.player_name:
            self.lbl_date.text = f"Привет, {self.player_name}!"
            Clock.schedule_once(lambda dt: self.restore_date(), 3)

    def restore_date(self):
        self.update_date()

    # ---------- вспомогательные ----------
    def _update_top_bar_rect(self, instance, value):
        self.top_bar_rect.size = instance.size
        self.top_bar_rect.pos = instance.pos

    @staticmethod
    def _format_coins(amount):
        if amount % 10 == 1 and amount % 100 != 11:
            return f"{amount} монета"
        elif 2 <= amount % 10 <= 4 and not (12 <= amount % 100 <= 14):
            return f"{amount} монеты"
        else:
            return f"{amount} монет"

    def update_date(self):
        now = datetime.now()
        month_names = ["января","февраля","марта","апреля","мая","июня",
                       "июля","августа","сентября","октября","ноября","декабря"]
        days_ru = ["понедельник","вторник","среда","четверг","пятница","суббота","воскресенье"]
        weekday = days_ru[now.weekday()]
        self.lbl_date.text = f"{weekday}, {now.day} {month_names[now.month-1]}"

    def add_coins_from_click(self):
        if self.click_sound:
            self.click_sound.stop()
            self.click_sound.play()
        self.coins += self.coin_amount_per_click
        self.lbl_coins.text = self._format_coins(self.coins)

    # ---------- потребности ----------
    def get_available_needs(self):
        available = list(NEEDS.keys())
        if self.has_cat:
            available.append('cat')
        return available

    def generate_need(self, dt=None):
        if self.active_need is not None:
            return
        available = self.get_available_needs()
        need = random.choice(available)
        self.active_need = need
        self.show_thought_bubble(need)

        if need in NEEDS:
            sound_file = NEEDS[need]['sound']
        else:
            sound_file = CAT_NEED[need]['sound']
        if sound_file:
            snd = SoundLoader.load(sound_file)
            if snd:
                snd.play()

        if self.need_reminder:
            Clock.unschedule(self.need_reminder)
        self.need_reminder = Clock.schedule_interval(self.remind_need, 10)

    def remind_need(self, dt):
        if self.active_need is None:
            return False
        need = self.active_need
        if need in NEEDS:
            sound_file = NEEDS[need]['sound']
        else:
            sound_file = CAT_NEED[need]['sound']
        if sound_file:
            snd = SoundLoader.load(sound_file)
            if snd:
                snd.play()
        return True

    def show_thought_bubble(self, need):
        self.hide_thought_bubble()
        if need in NEEDS:
            data = NEEDS[need]
        else:
            data = CAT_NEED[need]

        bubble = FloatLayout(size_hint=(None, None), size=(dp(100), dp(100)),
                             pos_hint={'x':0.02, 'top':0.95})
        try:
            bubble_img = Image(source='thought_bubble.png', size_hint=(1,1), pos_hint={'x':0,'y':0})
            bubble.add_widget(bubble_img)
        except:
            with bubble.canvas.before:
                Color(1,1,1,0.9)
                r = Rectangle(size=bubble.size, pos=bubble.pos)
            bubble.bind(size=lambda i, v: setattr(r, 'size', v))
            bubble.bind(pos=lambda i, v: setattr(r, 'pos', v))

        icon = Image(source=data['icon'], size_hint=(0.7,0.7), pos_hint={'center_x':0.5, 'center_y':0.5})
        bubble.add_widget(icon)
        self.game_area.add_widget(bubble)
        self.thought_bubble = bubble

        if self.need_text_label:
            self.need_text_label.text = data['text'] if data['text'] else ''

    def hide_thought_bubble(self):
        if self.thought_bubble:
            self.game_area.remove_widget(self.thought_bubble)
            self.thought_bubble = None
        if self.need_text_label:
            self.need_text_label.text = ''

    def satisfy_need(self, item_type):
        if self.active_need == item_type:
            self.active_need = None
            self.hide_thought_bubble()
            if self.need_reminder:
                Clock.unschedule(self.need_reminder)
                self.need_reminder = None
            self.coins += 20
            self.lbl_coins.text = self._format_coins(self.coins)

            if item_type == 'shower':
                self.stop_progress()
                if self.shower_done_sound:
                    self.shower_done_sound.stop()
                    self.shower_done_sound.play()
                self.burmaldochi.source = 'clean_burmaldochi.png'
                Clock.schedule_once(self.reset_burmaldochi_sprite, 5)
            elif item_type == 'cat':
                self.stop_progress()
                if self.eat_sound:
                    self.eat_sound.stop()
                    self.eat_sound.play()
            else:
                if self.eat_sound:
                    self.eat_sound.stop()
                    self.eat_sound.play()
            Clock.schedule_once(self.generate_need, random.randint(8, 20))
            return True
        return False

    def reset_burmaldochi_sprite(self, dt):
        self.burmaldochi.source = 'burmaldochi.png'

    # ---------- Прогресс-бар (общий для душа и котости) ----------
    def start_progress(self):
        if self.progress_timer is not None:
            return
        self.progress_value = 0
        self.create_progress_bar()
        self.update_progress_bar(0)
        self.progress_timer = Clock.schedule_interval(self.update_progress, 1/30)

    def stop_progress(self):
        if self.progress_timer:
            Clock.unschedule(self.progress_timer)
            self.progress_timer = None
        self.remove_progress_bar()

    def update_progress(self, dt):
        self.progress_value += dt / 3.0
        if self.progress_value >= 1.0:
            self.progress_value = 1.0
            self.update_progress_bar(1.0)
            if self.active_need == 'shower':
                self.satisfy_need('shower')
            elif self.active_need == 'cat':
                self.satisfy_need('cat')
        else:
            self.update_progress_bar(self.progress_value)

    def create_progress_bar(self):
        if self.progress_bar:
            return
        bar = ProgressBar(max=1, size_hint=(0.8, 0.05),
                          pos_hint={'center_x': 0.5, 'y': 0.05})
        self.progress_bar = bar
        self.game_area.add_widget(bar)

    def remove_progress_bar(self):
        if self.progress_bar:
            self.game_area.remove_widget(self.progress_bar)
            self.progress_bar = None

    def update_progress_bar(self, value):
        if self.progress_bar:
            self.progress_bar.value = value

    # ---------- Инвентарь фруктов ----------
    def create_fruit_inventory_bar(self):
        if self.inventory_bar:
            return
        bar = BoxLayout(size_hint=(1, 0.12), pos_hint={'x':0, 'y':0}, spacing=dp(5), padding=dp(5))
        with bar.canvas.before:
            Color(1,1,1,1)
            rect = Rectangle(size=bar.size, pos=bar.pos)
        bar.bind(size=lambda i, v: setattr(rect, 'size', v))
        bar.bind(pos=lambda i, v: setattr(rect, 'pos', v))
        self.inventory_bar = bar
        self.game_area.add_widget(bar)

    def remove_inventory_bar(self):
        if self.inventory_bar:
            self.game_area.remove_widget(self.inventory_bar)
            self.inventory_bar = None

    def update_inventory_display(self):
        if not self.inventory_bar or self.current_location != 'kitchen':
            return
        self.inventory_bar.clear_widgets()
        for fruit in self.fruits_inventory:
            img = Image(source=NEEDS[fruit]['icon'], size_hint=(None,1), width=dp(45))
            img.bind(on_touch_down=self.make_inventory_handler(fruit))
            self.inventory_bar.add_widget(img)

    def make_inventory_handler(self, item_type):
        def handler(widget, touch):
            if widget.collide_point(*touch.pos):
                self.consume_fruit(item_type)
        return handler

    def consume_fruit(self, fruit_type):
        if fruit_type in self.fruits_inventory:
            self.fruits_inventory.remove(fruit_type)
            if self.satisfy_need(fruit_type):
                print(f"{NEEDS[fruit_type]['text']} съеден успешно!")
            else:
                if self.wrong_sound:
                    self.wrong_sound.stop()
                    self.wrong_sound.play()
            self.update_inventory_display()

    # ---------- Смена локаций ----------
    def switch_location(self, location):
        if location == self.current_location:
            return
        if self.current_location in ('bathroom', 'garden'):
            self.stop_progress()
        if self.current_location == 'garden':
            self.hide_cat()

        self.current_location = location
        if location == 'start':
            self.full_bg.source = 'background.png'
            self.remove_inventory_bar()
        elif location == 'kitchen':
            self.full_bg.source = 'kitchen_bg.png'
            self.create_fruit_inventory_bar()
            self.update_inventory_display()
        elif location == 'bathroom':
            self.full_bg.source = 'bathroom_bg.png'
            self.remove_inventory_bar()
        elif location == 'garden':
            self.full_bg.source = 'garden_bg.png'
            self.remove_inventory_bar()
            if self.has_cat:
                self.show_cat()

    # ---------- Котость в саду ----------
    def show_cat(self):
        if self.cat_sprite:
            return
        self.cat_sprite = Image(
            source='cat_icon.png',
            size_hint=(None, None),
            size=(dp(80), dp(80))
        )
        self.jump_cat(0)
        self.game_area.add_widget(self.cat_sprite)
        self.cat_jump_timer = Clock.schedule_interval(self.jump_cat, 0.5)

    def hide_cat(self):
        if self.cat_sprite:
            self.game_area.remove_widget(self.cat_sprite)
            self.cat_sprite = None
        if self.cat_jump_timer:
            Clock.unschedule(self.cat_jump_timer)
            self.cat_jump_timer = None

    def jump_cat(self, dt):
        if not self.cat_sprite:
            return
        area_w, area_h = self.game_area.size
        cat_w, cat_h = self.cat_sprite.size
        new_x = random.uniform(0, area_w - cat_w)
        new_y = random.uniform(0, area_h - cat_h)
        self.cat_sprite.pos = (new_x, new_y)

    # ---------- Обработчики стрелок и кнопок ----------
    def on_arrow_left_click(self, widget, touch):
        if widget.collide_point(*touch.pos):
            locs = ['start', 'kitchen', 'bathroom', 'garden']
            idx = locs.index(self.current_location)
            self.switch_location(locs[(idx - 1) % len(locs)])

    def on_arrow_right_click(self, widget, touch):
        if widget.collide_point(*touch.pos):
            locs = ['start', 'kitchen', 'bathroom', 'garden']
            idx = locs.index(self.current_location)
            self.switch_location(locs[(idx + 1) % len(locs)])

    def on_shop_click(self, widget, touch):
        if not widget.collide_point(*touch.pos):
            return False
        self.show_shop_popup()
        return True

    def on_dev_click(self, widget, touch):
        if not widget.collide_point(*touch.pos):
            return False
        self.show_dev_popup()
        return True

    # ---------- Окна (разработчик, магазин) ----------
    def show_dev_popup(self):
        content = FloatLayout()
        with content.canvas.before:
            Color(1,1,1,1)
            self.dev_bg_rect = Rectangle(size=content.size, pos=content.pos)
            content.bind(size=self._update_dev_bg_rect, pos=self._update_dev_bg_rect)

        content.add_widget(Label(text="Хидео Кадзима", font_size=dp(24), bold=True,
                                 color=(0.2,0.2,0.2,1), size_hint=(1,0.4),
                                 pos_hint={'center_x':0.5, 'top':0.9}))
        btn_respect = Button(text='+респект', size_hint=(0.5,0.15),
                             pos_hint={'center_x':0.5, 'top':0.5})
        btn_respect.bind(on_release=self.give_respect)
        content.add_widget(btn_respect)

        btn_close = Button(text='Закрыть', size_hint=(0.5,0.12), pos_hint={'center_x':0.5, 'y':0.1})
        content.add_widget(btn_close)

        popup = Popup(title="Разработчик", content=content, size_hint=(0.8,0.5), auto_dismiss=False)
        btn_close.bind(on_release=popup.dismiss)
        popup.bind(on_dismiss=self.play_close_sound)
        popup.open()

    def give_respect(self, instance):
        if self.respect_sound:
            self.respect_sound.stop()
            self.respect_sound.play()

    def _update_dev_bg_rect(self, instance, value):
        if hasattr(self, 'dev_bg_rect'):
            self.dev_bg_rect.size = instance.size
            self.dev_bg_rect.pos = instance.pos

    def show_shop_popup(self):
        content = FloatLayout()
        with content.canvas.before:
            Color(1,1,1,1)
            self.shop_bg_rect = Rectangle(size=content.size, pos=content.pos)
            content.bind(size=self._update_shop_bg_rect, pos=self._update_shop_bg_rect)

        self.shop_grid = GridLayout(cols=2, spacing=dp(10), size_hint=(0.9,0.7),
                                    pos_hint={'center_x':0.5, 'top':0.9})

        for need_id, data in NEEDS.items():
            if need_id == 'shower':
                continue
            item_box = BoxLayout(orientation='vertical', spacing=dp(5))
            item_box.add_widget(Image(source=data['icon'], size_hint=(1,0.6)))
            item_box.add_widget(Label(text=f"{data['price']} монет", size_hint=(1,0.2), font_size=dp(14)))
            btn_buy = Button(text='Купить', size_hint=(1,0.2))
            btn_buy.bind(on_release=lambda btn, n=need_id: self.buy_item(n))
            item_box.add_widget(btn_buy)
            self.shop_grid.add_widget(item_box)

        cat_box = BoxLayout(orientation='vertical', spacing=dp(5))
        cat_box.add_widget(Image(source='cat_icon.png', size_hint=(1,0.6)))
        cat_box.add_widget(Label(text="1000 монет", size_hint=(1,0.2), font_size=dp(14)))
        if self.has_cat:
            btn_cat = Button(text='Куплено', size_hint=(1,0.2), disabled=True)
        else:
            btn_cat = Button(text='Купить', size_hint=(1,0.2))
            btn_cat.bind(on_release=self.buy_cat)
        cat_box.add_widget(btn_cat)
        self.shop_grid.add_widget(cat_box)

        content.add_widget(self.shop_grid)
        btn_close = Button(text='Закрыть', size_hint=(0.5,0.08), pos_hint={'center_x':0.5, 'y':0.05})
        content.add_widget(btn_close)

        popup = Popup(title='Магазин', content=content, size_hint=(0.9,0.85), auto_dismiss=False)
        btn_close.bind(on_release=popup.dismiss)
        popup.bind(on_dismiss=self.play_close_sound)
        popup.open()

    def buy_item(self, item_id):
        price = NEEDS[item_id]['price']
        if self.coins >= price:
            self.coins -= price
            self.lbl_coins.text = self._format_coins(self.coins)
            self.fruits_inventory.append(item_id)
            if self.inventory_bar and self.current_location == 'kitchen':
                self.update_inventory_display()
            print(f"Куплено: {item_id}")

    def buy_cat(self, instance):
        if self.coins >= 1000:
            self.coins -= 1000
            self.lbl_coins.text = self._format_coins(self.coins)
            self.has_cat = True
            self.save_save()
            for popup in App.get_running_app().root_window.children:
                if isinstance(popup, Popup) and popup.title == 'Магазин':
                    popup.dismiss()
                    self.show_shop_popup()
                    break
            if self.current_location == 'garden':
                self.show_cat()
        else:
            print("Недостаточно монет!")

    def _update_shop_bg_rect(self, instance, value):
        if hasattr(self, 'shop_bg_rect'):
            self.shop_bg_rect.size = instance.size
            self.shop_bg_rect.pos = instance.pos

    def play_close_sound(self, *args):
        if self.close_sound:
            self.close_sound.stop()
            self.close_sound.play()


class GameArea(FloatLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app

    def setup(self):
        self.app.burmaldochi = Image(
            source='burmaldochi.png', size_hint=(None, None),
            size=(dp(140), dp(140)), pos_hint={'center_x':0.5, 'center_y':0.5}
        )
        self.add_widget(self.app.burmaldochi)

        self.app.arrow_left = Image(
            source='arrow_left.png', size_hint=(None, None),
            size=(dp(50), dp(50)), pos_hint={'center_y':0.5, 'x':0.02}
        )
        self.app.arrow_left.bind(on_touch_down=self.app.on_arrow_left_click)
        self.add_widget(self.app.arrow_left)

        self.app.arrow_right = Image(
            source='arrow_right.png', size_hint=(None, None),
            size=(dp(50), dp(50)), pos_hint={'center_y':0.5, 'right':0.98}
        )
        self.app.arrow_right.bind(on_touch_down=self.app.on_arrow_right_click)
        self.add_widget(self.app.arrow_right)

        self.app.need_text_label = Label(text='', font_size=dp(16), bold=True, color=(0,0,0,1),
                                         size_hint=(None,None), size=(dp(150), dp(30)),
                                         pos_hint={'center_x':0.5, 'top':0.95})
        self.add_widget(self.app.need_text_label)

    def on_touch_down(self, touch):
        if self.app.cat_sprite and self.app.cat_sprite.collide_point(*touch.pos):
            if self.app.active_need == 'cat' and self.app.current_location == 'garden':
                self.app.start_progress()
                return True
            else:
                if self.app.purr_sound:
                    self.app.purr_sound.stop()
                    self.app.purr_sound.play()
                return True

        if self.app.burmaldochi.collide_point(*touch.pos):
            if self.app.active_need == 'shower' and self.app.current_location == 'bathroom':
                self.app.start_progress()
                return True
            else:
                self.app.add_coins_from_click()
                return True
        return super().on_touch_down(touch)


if __name__ == '__main__':
    BurmaldochiApp().run()

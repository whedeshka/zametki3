import json
import os
from datetime import datetime

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.popup import Popup
from kivy.uix.togglebutton import ToggleButton
from kivy.graphics import Color, Rectangle
from kivy.core.window import Window

DATA_FILE = "reminders_data.json"

THEMES = {
    "dark": {
        "bg_main": (0.07, 0.07, 0.08, 1),
        "bg_card": (0.12, 0.12, 0.13, 1),
        "bg_entry": (0.15, 0.15, 0.16, 1),
        "fg_main": (1, 1, 1, 1),
        "fg_sub": (0.6, 0.6, 0.65, 1),
        "fg_done": (0.4, 0.4, 0.42, 1),
        "accent": (0.03, 0.4, 1, 1)
    },
    "light": {
        "bg_main": (0.94, 0.95, 0.96, 1),
        "bg_card": (1, 1, 1, 1),
        "bg_entry": (0.89, 0.90, 0.92, 1),
        "fg_main": (0.02, 0.02, 0.02, 1),
        "fg_sub": (0.4, 0.4, 0.42, 1),
        "fg_done": (0.55, 0.55, 0.57, 1),
        "accent": (0.03, 0.4, 1, 1)
    }
}


class ColoredBoxLayout(BoxLayout):
    def __init__(self, bg_color=(1, 1, 1, 1), **kwargs):
        super().__init__(**kwargs)
        self.bg_color = bg_color
        with self.canvas.before:
            self.rect_color = Color(*bg_color)
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)

    def _update_rect(self, instance, value):
        self.rect.size = instance.size
        self.rect.pos = instance.pos

    def set_bg_color(self, color):
        self.bg_color = color
        self.rect_color.rgba = color


class TaskInputRow(BoxLayout):
    def __init__(self, text="", colors=None, remove_callback=None, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=45, spacing=5, **kwargs)
        self.colors = colors
        self.remove_callback = remove_callback

        self.lbl_bullet = Label(text="◯", size_hint_x=None, width=30, color=colors["fg_sub"])
        self.add_widget(self.lbl_bullet)

        self.entry = TextInput(
            text=text,
            hint_text="Пункт заметки...",
            multiline=False,
            background_color=colors["bg_entry"],
            foreground_color=colors["fg_main"],
            cursor_color=colors["fg_main"],
            padding=[10, 10, 10, 10]
        )
        self.add_widget(self.entry)

        self.btn_del = Button(
            text="✕",
            size_hint_x=None,
            width=35,
            background_color=(0, 0, 0, 0),
            color=colors["fg_sub"],
            font_size=16
        )
        self.btn_del.bind(on_release=lambda x: self.remove_callback(self))
        self.add_widget(self.btn_del)


class CardWidget(ColoredBoxLayout):
    def __init__(self, title, tasks, time_str, completed, colors, delete_callback, toggle_callback, **kwargs):
        super().__init__(
            bg_color=colors["bg_card"],
            orientation="vertical",
            size_hint_y=None,
            padding=12,
            spacing=8,
            **kwargs
        )
        self.colors = colors
        self.title_text = title
        self.tasks_data = tasks
        self.time_str = time_str
        self.completed = completed
        self.delete_callback = delete_callback
        self.toggle_callback = toggle_callback

        self.bind(minimum_height=self.setter('height'))
        self.build_ui()

    def build_ui(self):
        self.clear_widgets()

        # Шапка карточки
        header = BoxLayout(orientation="horizontal", size_hint_y=None, height=35, spacing=8)

        self.chk_main = CheckBox(
            active=self.completed,
            size_hint_x=None,
            width=35,
            color=self.colors["fg_done"] if self.completed else self.colors["fg_main"]
        )
        self.chk_main.bind(active=self.on_main_check)
        header.add_widget(self.chk_main)

        lbl_title = Label(
            text=f"[b]{self.title_text}[/b]",
            markup=True,
            color=self.colors["fg_done"] if self.completed else self.colors["fg_main"],
            halign="left",
            valign="middle"
        )
        lbl_title.bind(size=lbl_title.setter('text_size'))
        header.add_widget(lbl_title)

        lbl_time = Label(
            text=self.time_str,
            size_hint_x=None,
            width=50,
            color=self.colors["fg_sub"],
            font_size=12
        )
        header.add_widget(lbl_time)

        btn_del = Button(
            text="🗑",
            size_hint_x=None,
            width=35,
            background_color=(0, 0, 0, 0),
            color=self.colors["fg_sub"]
        )
        btn_del.bind(on_release=lambda x: self.delete_callback(self))
        header.add_widget(btn_del)

        self.add_widget(header)

        # Пункты
        for item in self.tasks_data:
            t_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=30, spacing=8, padding=[25, 0, 0, 0])

            c_box = CheckBox(
                active=item["done"],
                size_hint_x=None,
                width=30,
                color=self.colors["fg_done"] if item["done"] else self.colors["fg_main"]
            )
            c_box.bind(active=lambda cb, val, task=item: self.on_task_check(task, val))
            t_row.add_widget(c_box)

            t_lbl = Label(
                text=item["text"],
                color=self.colors["fg_done"] if (item["done"] or self.completed) else self.colors["fg_main"],
                halign="left",
                valign="middle"
            )
            t_lbl.bind(size=t_lbl.setter('text_size'))
            t_row.add_widget(t_lbl)

            self.add_widget(t_row)

    def on_main_check(self, checkbox, value):
        self.completed = value
        self.toggle_callback(self, value)

    def on_task_check(self, task, value):
        task["done"] = value
        self.build_ui()


class ReminderApp(App):
    def build(self):
        self.settings = {
            "main_check_action": "grey_and_down",
            "show_creation_time": True,
            "theme": "dark"
        }
        self.colors = THEMES[self.settings["theme"]]
        self.cards_list = []
        self.history_list = []
        self.input_rows = []

        # Главный контейнер
        self.root_layout = ColoredBoxLayout(bg_color=self.colors["bg_main"], orientation="vertical", padding=10,
                                            spacing=10)

        # --- Шапка ---
        header = ColoredBoxLayout(bg_color=self.colors["bg_main"], orientation="horizontal", size_hint_y=None,
                                  height=45)

        self.lbl_title = Label(
            text="[b]Все напоминания[/b]",
            markup=True,
            font_size=20,
            color=self.colors["fg_main"],
            halign="left"
        )
        self.lbl_title.bind(size=self.lbl_title.setter('text_size'))
        header.add_widget(self.lbl_title)

        self.btn_theme = Button(
            text="🌙" if self.settings["theme"] == "dark" else "☀️",
            size_hint_x=None,
            width=45,
            background_color=(0, 0, 0, 0),
            color=self.colors["fg_main"],
            font_size=18
        )
        self.btn_theme.bind(on_release=self.toggle_theme)
        header.add_widget(self.btn_theme)

        self.root_layout.add_widget(header)

        # --- Секция ввода ---
        self.input_card = ColoredBoxLayout(
            bg_color=self.colors["bg_card"],
            orientation="vertical",
            size_hint_y=None,
            padding=10,
            spacing=8
        )
        self.input_card.bind(minimum_height=self.input_card.setter('height'))

        self.title_entry = TextInput(
            hint_text="Название группы (например, Завтра)",
            multiline=False,
            size_hint_y=None,
            height=45,
            background_color=self.colors["bg_entry"],
            foreground_color=self.colors["fg_main"],
            cursor_color=self.colors["fg_main"],
            padding=[10, 10, 10, 10]
        )
        self.input_card.add_widget(self.title_entry)

        # Контейнер для динамических пунктов
        self.items_container = BoxLayout(orientation="vertical", size_hint_y=None, spacing=5)
        self.items_container.bind(minimum_height=self.items_container.setter('height'))
        self.input_card.add_widget(self.items_container)

        btn_box = BoxLayout(orientation="horizontal", size_hint_y=None, height=40, spacing=8)

        btn_add_row = Button(
            text="+ Пункт",
            background_color=self.colors["bg_entry"],
            color=self.colors["fg_main"]
        )
        btn_add_row.bind(on_release=lambda x: self.add_input_row())
        btn_box.add_widget(btn_add_row)

        btn_add_card = Button(
            text="Сохранить заметку",
            background_color=self.colors["accent"],
            color=(1, 1, 1, 1)
        )
        btn_add_card.bind(on_release=self.add_new_card)
        btn_box.add_widget(btn_add_card)

        self.input_card.add_widget(btn_box)
        self.root_layout.add_widget(self.input_card)

        # --- Список карточек заметок ---
        scroll_cards = ScrollView(size_hint=(1, 1))
        self.cards_container = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.cards_container.bind(minimum_height=self.cards_container.setter('height'))
        scroll_cards.add_widget(self.cards_container)
        self.root_layout.add_widget(scroll_cards)

        # Инициализация первого поля ввода
        self.add_input_row()

        self.load_data()
        return self.root_layout

    def add_input_row(self, text=""):
        row = TaskInputRow(text=text, colors=self.colors, remove_callback=self.remove_input_row)
        self.input_rows.append(row)
        self.items_container.add_widget(row)

    def remove_input_row(self, row_instance):
        if len(self.input_rows) > 1:
            self.input_rows.remove(row_instance)
            self.items_container.remove_widget(row_instance)

    def add_new_card(self, *args):
        title = self.title_entry.text.strip() or "Заметка"
        tasks = []
        for r in self.input_rows:
            val = r.entry.text.strip()
            if val:
                tasks.append({"text": val, "done": False})

        time_now = datetime.now().strftime("%H:%M")

        card_data = {
            "title": title,
            "tasks": tasks,
            "time": time_now,
            "completed": False
        }

        self.cards_list.append(card_data)
        self.render_card(card_data)

        # Сброс формы ввода
        self.title_entry.text = ""
        self.items_container.clear_widgets()
        self.input_rows.clear()
        self.add_input_row()

        self.save_data()

    def render_card(self, card_data):
        card = CardWidget(
            title=card_data["title"],
            tasks=card_data["tasks"],
            time_str=card_data.get("time", ""),
            completed=card_data.get("completed", False),
            colors=self.colors,
            delete_callback=self.delete_card,
            toggle_callback=self.toggle_card
        )
        card_data["widget"] = card

        if card_data.get("completed"):
            self.cards_container.add_widget(card)
        else:
            self.cards_container.add_widget(card, index=len(self.cards_container.children))

    def delete_card(self, card_widget):
        for item in self.cards_list:
            if item.get("widget") == card_widget:
                self.cards_list.remove(item)
                break
        self.cards_container.remove_widget(card_widget)
        self.save_data()

    def toggle_card(self, card_widget, is_completed):
        for item in self.cards_list:
            if item.get("widget") == card_widget:
                item["completed"] = is_completed
                # Переносим вниз при завершении
                self.cards_container.remove_widget(card_widget)
                if is_completed:
                    self.cards_container.add_widget(card_widget)
                else:
                    self.cards_container.add_widget(card_widget, index=len(self.cards_container.children))
                break
        self.save_data()

    def toggle_theme(self, *args):
        self.settings["theme"] = "light" if self.settings["theme"] == "dark" else "dark"
        self.colors = THEMES[self.settings["theme"]]
        self.btn_theme.text = "🌙" if self.settings["theme"] == "dark" else "☀️"

        self.root_layout.set_bg_color(self.colors["bg_main"])
        self.lbl_title.color = self.colors["fg_main"]
        self.btn_theme.color = self.colors["fg_main"]
        self.input_card.set_bg_color(self.colors["bg_card"])

        # Обновляем все карточки
        self.cards_container.clear_widgets()
        for card_data in self.cards_list:
            self.render_card(card_data)

        self.save_data()

    def save_data(self):
        save_cards = []
        for c in self.cards_list:
            save_cards.append({
                "title": c["title"],
                "time": c["time"],
                "completed": c["completed"],
                "tasks": c["tasks"]
            })
        data = {
            "settings": self.settings,
            "cards": save_cards
        }
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения: {e}")

    def load_data(self):
        if not os.path.exists(DATA_FILE):
            return
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            if "settings" in data:
                self.settings.update(data["settings"])
                self.colors = THEMES[self.settings["theme"]]
                self.btn_theme.text = "🌙" if self.settings["theme"] == "dark" else "☀️"

            if "cards" in data:
                self.cards_list = data["cards"]
                for card_data in self.cards_list:
                    self.render_card(card_data)
        except Exception as e:
            print(f"Ошибка загрузки: {e}")


if __name__ == "__main__":
    ReminderApp().run()
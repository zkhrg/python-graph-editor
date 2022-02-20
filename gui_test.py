import tkinter as tk
import math
from dialog import askstring
from tkinter import simpledialog
from enum import Enum, auto
from constants import *
from structures import *


# нужен для отслеживания статуса работы с программой
class EditingMode(Enum):
    DEFAULT = auto()
    DELETING_ELEMENT = auto()
    CONNECTING = auto()


class DragAndDropArea(tk.Canvas):
    def __init__(self, master, **kwargs):
        tk.Canvas.__init__(self, master, **kwargs)
        self.active = None
        self.active_text = None
        self.default_color = 'red'
        self.selecting_color = '#638ae6'  # синий
        self.edge_color = '#ab7738'
        self.selected_items = list()
        self.editing_mode = EditingMode.DEFAULT
        self.vertex_size = 100
        self.created_vertices = list()
        self.shift_length = 120

        # бинды на действия мыши
        self.bind('<ButtonPress-1>', self.get_item)
        self.bind('<B1-Motion>', self.move_active)
        self.bind('<ButtonRelease-1>', self.set_none)
        self.bind("<Button-2>", self.do_popup)

        # бинды на клавиатуру
        # добавить обработку на русской и не русской раскладке и в разном написании капосом и не капсом
        self.bind('<KeyPress-s>', self.switch_mode)
        self.bind('<KeyPress-c>', self.connect_edges)

        # меню
        self.vertex_menu = tk.Menu(self, tearoff=0)
        self.vertex_menu.add_command(label="Удалить вершину", command=self.delete_element)
        self.vertex_menu.add_separator()

        self.edge_menu = tk.Menu(self, tearoff=0)
        self.edge_menu.add_command(label="Удалить грань", command=self.delete_element)

        self.default_menu = tk.Menu(self, tearoff=0)
        self.default_menu.add_command(label="Создать вершину", command=self.create_vertex)
        self.default_menu.add_command(label="Соеднить вершины")

    # запуск меню в зависимости от нажатого элемента на экране
    def do_popup(self, event):
        try:
            card = self.find_withtag('current&&card')
            edge = self.find_withtag('current&&edge')
            if len(card):
                self.vertex_menu.tk_popup(event.x_root, event.y_root)
            elif len(edge):
                self.edge_menu.tk_popup(event.x_root, event.y_root)
            else:
                self.default_menu.tk_popup(event.x_root, event.y_root)

        except IndexError:
            print("oy")

    # снятие активного положения с вершины (нужно для перемещения)
    def set_none(self, event):
        self.active = None
        self.active_text = None

    # "касание" вершины для перемещения или выделения
    def get_item(self, event):
        try:
            if self.editing_mode == EditingMode.DEFAULT:
                # представляется возможность двигать только
                item = self.find_withtag('current&&card')
                self.active = item[0]
                text = self.find_withtag(f"text_card {item[0]}")
                self.active_text = text[0]
            elif self.editing_mode == EditingMode.CONNECTING:
                # тут должна производиться процедура что как мы сюда попали то
                # на шаре с его айди должен быть его индек в списке селектед айтемс
                self.connecting_selected_edges()
            else:
                pass

        except IndexError:
            print('Никакой элемент не был нажат')

    def move_active(self, event):
        if self.active is not None:
            coords = self.coords(self.active)
            width = coords[2] - coords[0]  # x2-x1
            height = coords[1] - coords[3]  # y1-y2

            x1 = event.x - width / 2
            y1 = event.y - height / 2
            x2 = event.x + width / 2
            y2 = event.y + height / 2
            txt_x = event.x
            txt_y = event.y

            self.coords(self.active, x1, y1, x2, y2)
            self.coords(self.active_text, txt_x, txt_y)
            try:
                self.update_tension(self.active)
            except IndexError:
                print('Связей между вершинами не найдено')

    # обновление линии которая связывает вершины
    def update_tension(self, tag, directed=True):
        tensions = self.find_withtag(f'card {tag}')
        for tension in tensions:
            bounded_cards = self.gettags(tension)
            weight_edge = self.find_withtag(f"parent {tension}")[0]
            bg_weight_edge = self.find_withtag(f"parent {weight_edge}")[0]
            card = bounded_cards[0].split()[-1]
            card2 = bounded_cards[1].split()[-1]
            x1, y1 = self.get_mid_point(card)
            x2, y2 = self.get_mid_point(card2)

            if directed:
                shift = self.calculate_shift(x1, y1, x2, y2)
                x_shift, y_shift, x_shift_weight, y_shift_weight, x_m, y_m = \
                    shift[0], shift[1], shift[2], shift[3], shift[4], shift[5]

                angle = self.calculate_angle(x1, y1, x2, y2)
                x_shift_d = abs(math.cos(math.radians(90 - abs(angle))) * self.vertex_size / 2)
                y_shift_d = abs(math.cos(math.radians(abs(angle))) * self.vertex_size / 2)

                if x2 <= x1 and y2 < y1:
                    x2 = x2 + x_shift_d
                    y2 = y2 + y_shift_d
                if x2 > x1 and y2 <= y1:
                    x2 = x2 - x_shift_d
                    y2 = y2 + y_shift_d
                if x2 >= x1 and y2 > y1:
                    x2 = x2 - x_shift_d
                    y2 = y2 - y_shift_d
                if x2 < x1 and y2 >= y1:
                    x2 = x2 + x_shift_d
                    y2 = y2 - y_shift_d
                self.coords(tension, x1, y1, x_shift, y_shift, x2, y2)

                self.coords(weight_edge, x_m+x_shift_weight*0.55, y_m+y_shift_weight*0.55)
                self.coords(bg_weight_edge, self.bbox(weight_edge))
                self.lower(tension)

    # создание вершины
    def draw_card(self, x, y, width, height, color):
        x1, y1 = x, y
        x2, y2 = x + width, y + height
        reference = self.create_oval(x1, y1, x2, y2, fill=color, tags='card')

        return reference

    # выстраивание связи между двумя гранями визуально
    def bind_tension(self, card, another_card, weight, directed=True):
        default_tag = 'edge'
        x1, y1 = self.get_mid_point(card)
        x2, y2 = self.get_mid_point(another_card)
        tag1 = f'card {card}'
        tag2 = f'card {another_card}'

        shift = self.calculate_shift(x1, y1, x2, y2)
        x_shift = shift[0]
        y_shift = shift[1]
        x_shift_d = shift[2]*0.6+shift[4]
        y_shift_d = shift[3]*0.6+shift[5]
        print(f"first: {x1, y1, x_shift, y_shift, x2, y2}")
        if directed:
            line = self.create_line(x1, y1,
                                    x_shift,
                                    y_shift,
                                    x2, y2,
                                    fill=self.edge_color, width=10,
                                    tags=(tag1, tag2, default_tag), smooth=1, arrow=tk.LAST,
                                    arrowshape=(30, 30, 10), )
            text_weight = self.create_text(x_shift_d, y_shift_d, text=weight, fill='black', tags=(f"parent {line}",),
                                           font=f"Courier_new {int(self.vertex_size/3.7)} normal")

            back_g = self.create_rectangle(self.bbox(text_weight),
                                           fill=self.edge_color,
                                           outline=self.edge_color, width=5, tags=(f"parent {text_weight}",))
            self.tag_lower(back_g, text_weight)
            self.update_tension(card)
        else:
            line = self.create_line(x1, y1,
                                    x_shift,
                                    y_shift, x2, y2, fill='blue', width=10,
                                    tags=(tag1, tag2, default_tag), )

        self.lower(line)

    # вычисление координат середины карточки отвечающей за вершину графа
    def get_mid_point(self, card):
        coords = self.coords(card)
        width = coords[2] - coords[0]  # x2-x1
        height = coords[1] - coords[3]  # y1-y2
        position = coords[0], coords[1]  # x1,y1

        mid_x = position[0] + width / 2
        mid_y = position[1] - height / 2

        return mid_x, mid_y

    # связывает выделененные вершины в том порядке, в котором они были выделены
    def connect_edges(self, e):
        if len(self.selected_items) > 1:
            for i in range(len(self.selected_items)-1):
                self.bind_tension(self.selected_items[i], self.selected_items[i+1])

    def switch_mode(self, e):
        if self.editing_mode == EditingMode.DEFAULT:
            self.editing_mode = EditingMode.CONNECTING
        elif self.editing_mode == EditingMode.CONNECTING:
            for item in self.selected_items:
                self.delete(self.find_withtag(f"parent {item}")[0])
                self.itemconfig(item, fill=self.default_color)
            self.selected_items.clear()
            self.editing_mode = EditingMode.DEFAULT

    def delete_element(self, event=None):
        item = self.find_withtag('current')[0]
        self.delete(item)
        try:
            text = self.find_withtag(f'text_card {item}')
            self.delete(text)
            tensions = self.find_withtag(f'card {item}')
            for tent in tensions:
                self.delete(tent)
        finally:
            pass

    def create_vertex(self):
        x, y = self.winfo_pointerx() - self.winfo_rootx(), self.winfo_pointery() - self.winfo_rooty()
        x = x - self.vertex_size / 2
        y = y - self.vertex_size / 2
        tx = x + self.vertex_size / 2
        ty = y + self.vertex_size / 2

        card = self.draw_card(x, y, self.vertex_size, self.vertex_size, self.default_color)
        self.create_text(tx, ty, font=f"Courier_new {int(self.vertex_size/2)} normal", text=f"{card}", fill='black',
                         state=tk.DISABLED, tags=(f"text_card {card}", ))

    # обновление показателя выделения вершин
    def update_selection(self):
        for selected_vertex_text in self.find_withtag("selected"):
            self.delete(selected_vertex_text)
        for vertex in self.selected_items:
            coords = self.get_mid_point(vertex)
            tx = coords[0] - self.vertex_size / 5
            ty = coords[1] - self.vertex_size / 5
            self.create_text(tx, ty, font=f"Courier_new {int(self.vertex_size / 5)} normal",
                             text=f"{self.selected_items.index(vertex)}",
                             fill='black',
                             state=tk.DISABLED, tags=(f"selected", f"parent {vertex}",),)

    def connecting_selected_edges(self):
        item = self.find_withtag('current&&card')[0]
        if item not in self.selected_items:
            self.itemconfig(item, fill=self.selecting_color)
            self.selected_items.append(item)
            if len(self.selected_items) == 2:
                answer = askstring(title="Настройка связи вершин", parent=self,
                                   prompt="Настройка связи вершин")
                self.bind_tension(self.selected_items[0], self.selected_items[1], answer[0])
                for item in self.selected_items:
                    self.itemconfig(item, fill=self.default_color)
                self.selected_items.clear()
        else:
            self.itemconfig(item, fill=self.default_color)
            self.selected_items.remove(item)

    @staticmethod
    def calculate_angle(x1, y1, x2, y2):
        if x2 - x1 == 0:
            m = 0
        elif y2 - y1 == 0:
            m = math.inf
        else:
            m = 1 / ((y2 - y1) / (x2 - x1))

        angle = math.degrees(math.atan(m))

        return angle

    def calculate_shift(self, x1, y1, x2, y2, additional=False):
        if additional:
            pass
        else:
            type_line = 'directed'
            if type_line == 'directed':
                mid_line_x = (x1 + x2) / 2
                mid_line_y = (y1 + y2) / 2

                angle = self.calculate_angle(x1, y1, x2, y2)

                x_shift_d = abs(math.cos(math.radians(abs(angle))) * self.shift_length)
                y_shift_d = abs(math.cos(math.radians(90 - abs(angle))) * self.shift_length)

                if angle <= 0:
                    x_shift = mid_line_x - x_shift_d
                    y_shift = mid_line_y - y_shift_d
                    if angle == 0 and y1 > y2:
                        x_shift = mid_line_x + x_shift_d
                        y_shift = mid_line_y + y_shift_d
                    if x1 < x2:
                        x_shift = mid_line_x + x_shift_d
                        y_shift = mid_line_y + y_shift_d
                        if angle == 0 and y2 > y1:
                            x_shift = mid_line_x + x_shift_d
                            y_shift = mid_line_y - y_shift_d
                else:
                    x_shift = mid_line_x + x_shift_d
                    y_shift = mid_line_y - y_shift_d
                    if x1 < x2:
                        x_shift = mid_line_x - x_shift_d
                        y_shift = mid_line_y + y_shift_d

                if angle == 0 and y1 > y1:
                    x_shift = mid_line_x - x_shift_d
                    y_shift = mid_line_y - y_shift_d

                if x2 <= x1 and y2 < y1:
                    x_shift_d = x_shift_d
                    y_shift_d = (-1)*y_shift_d
                if x2 > x1 and y2 <= y1:
                    x_shift_d = x_shift_d
                    y_shift_d = y_shift_d
                if x2 >= x1 and y2 > y1:
                    x_shift_d = (-1)*x_shift_d
                    y_shift_d = y_shift_d
                if x2 < x1 and y2 >= y1:
                    x_shift_d = (-1)*x_shift_d
                    y_shift_d = (-1)*y_shift_d

                return x_shift, y_shift, x_shift_d, y_shift_d, mid_line_x, mid_line_y


if __name__ == "__main__":
    window = tk.Tk()
    window.state('zoomed')
    area = DragAndDropArea(window, bg='white')
    area.pack(fill='both', expand=1)

    # нужно сделать фокусировку чтобы работало биндинг кнопок клавиатуры (клавиши)
    area.focus_set()
    window.mainloop()


# Нужно сделать чтобы менялся знак при развороте в какой-то момент, а так же для второй вершины делать знаки
# в противоположную строону чтобы вторая стрелка была не в нахлест сущствующией

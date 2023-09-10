from tkinter import filedialog, Canvas, Button, Tk, N, NW, W, SW, S, SE, E, NE, CENTER
from core import runni_bota, vypni_bota
import shutil, os, csv, random, threading
from sender import send_command

# konstanty pro snapovani bloku
CANVAS_WIDTH = 1000
CANVAS_HEIGHT = 700
SNAP_TRESHOLD = 15
RECTANGLE_SIDE_SIZE = 100
CORE_SIDE_SIZE = RECTANGLE_SIDE_SIZE # zatim blbne, kdyz je jiny nez RECTANGLE_SIDE_SIZE
EDGE_ZONE_SIZE = RECTANGLE_SIDE_SIZE+10
FONT_SIZE = 18
FONT_SIZE_SMALL = 12
FONT_FAMILY = "Arial"
UNSNAP_TRESHOLD = 30
# FONT_FAMILY jsou "Arial", "Calibri", "Comic Sans MS", "Courier New", "Georgia", "Helvetica", "Impact", "Lucida Console", "Lucida Sans Unicode", "Palatino Linotype", "Tahoma", "Times New Roman", "Trebuchet MS", "Verdana"

# konstanty pro bota
COG_ACTIVATION_PATH = "cogs/activation.csv"

class _SnappableRectangle:
    
    def __init__(self, canvas, x1, y1, x2, y2, fill, input_root):
        self.associated_file = None
        self.bottom = None
        self.canvas = canvas
        self.center = [int((x1+x2)/2), int((y1+y2)/2)]
        self.is_active = False
        self.last_pos = (abs(x2-x1), abs(y2-y1))
        self.left = None
        self.name = None
        self.original_pos = (abs(x2-x1), abs(y2-y1))
        self.path = None
        self.prev_x = 0
        self.prev_y = 0
        self.rect = canvas.create_rectangle(x1, y1, x2, y2, fill=fill, tags="rectangle")
        self.right = None
        self.root = input_root
        self.snap_distance = SNAP_TRESHOLD
        self.tag = str(self.root.get_id())
        self.text_string = "PLACE_HOLDER"
        self.text_object = self.canvas.create_text((x1+x2)//2, (y1+y2)//2, text=self.text_string, font=(FONT_FAMILY, FONT_SIZE_SMALL), fill="white")
        self.top = None
        self.unsnap_force = UNSNAP_TRESHOLD
        self.window_id = None

        # pohyb vykresleneho ctverce
        self.canvas.tag_bind(self.rect, '<ButtonPress-1>', self.start_drag)
        self.canvas.tag_bind(self.rect, '<B1-Motion>', self.drag)
        self.canvas.tag_bind(self.rect, '<ButtonRelease-1>', self.stop_drag)

        # pohyb vykresleneho napisu na ctverci
        self.canvas.tag_bind(self.text_object, '<ButtonPress-1>', self.start_drag)
        self.canvas.tag_bind(self.text_object, '<B1-Motion>', self.drag)
        self.canvas.tag_bind(self.text_object, '<ButtonRelease-1>', self.stop_drag)

        self.canvas.latest_rectangle = self

    def add_name_and_path(self):
            self.path = filedialog.askopenfilename(title="Select Valid Discord Cog File", initialdir="storage/", filetypes=(("Discord Cog", "*.py"),))
            if not self.path:
                return
            self.name = os.path.basename(self.path)
            self.name, _ = os.path.splitext(self.name)

            # aktualizace labelu
            if self.name:
                self.text_string = str(self.name)
            else:
                self.text_string = "NAME_ERROR"
            self.canvas.itemconfig(self.text_object, text=self.text_string)

    def as_dict(self):
        return {'left': self.left, 'right': self.right, 'top': self.top, 'bottom': self.bottom}

    def delete(self):
        self.canvas.delete(self.rect)
        self.canvas.delete(self.text)
    
    def drag(self, event):
        dx = event.x - self.last_pos[0]
        dy = event.y - self.last_pos[1]
        self.canvas.move(self.rect, dx, dy)
        self.canvas.move(self.text_object, dx, dy)
        self.last_pos = (event.x, event.y)

        # for other_rect in self.canvas.find_withtag('draggable'):
        #     if other_rect != self.rect:
        #         self.snap_to(other_rect)

    def start_drag(self, event):
        self.original_pos = self.canvas.coords(self.rect)[:2]
        self.last_pos = (event.x, event.y)

    def stop_drag(self, event):
        self.update_center()
    
        self.left, self.right, self.top, self.bottom = None, None, None, None
        # kontrola stran na pripojeni
        for item in self.root.rectangles:
            ...
        # for core

    def update_center(self):
        x1, y1, x2, y2 = self.canvas.coords(self.rect)
        self.center = [int((x1+x2)/2), int((y1+y2)/2)]

class Tk_extended(Tk):
    def __init__(self, *args, **kwargs):
        # dedicnost
        super().__init__(*args, **kwargs)       
        
        # setup promennych
        self.rectangles = []
        self.last_id = 0
        self.last_rectangle = None

        # setup inteligentnich objektu
        self.canvas = Canvas(self, bg="white", width=CANVAS_WIDTH, height=CANVAS_HEIGHT)
        self.core = _SnappableRectangle(canvas=self.canvas, x1=EDGE_ZONE_SIZE, y1=EDGE_ZONE_SIZE, x2=EDGE_ZONE_SIZE+CORE_SIDE_SIZE, y2=EDGE_ZONE_SIZE+CORE_SIDE_SIZE, fill="black", input_root=self)
        self.core.canvas.itemconfig(self.core.text_object, text="CORE")
        self.rectangles.append(self.core)

    def delete_last_rectangle(self):
        # TODO: osetrit krajni pripady, aby nedoslo k chybe
        if self.last_rectangle:
            self.canvas.delete(self.last_rectangle.tag)
            try:
                self.last_rectangle = self.rectangles[-1]
            except IndexError:
                self.last_rectangle = None

    def does_overlap(self, rect1, rect2):
        ax, ay = rect1.center
        bx, by = rect2.center
        
        # kontrola levo, pravo
        if ax > (bx+RECTANGLE_SIDE_SIZE+UNSNAP_TRESHOLD) or ax < (bx-RECTANGLE_SIDE_SIZE-UNSNAP_TRESHOLD):
            return False
            
        # kontrola nahoru, dolu
        if ay > (by+RECTANGLE_SIDE_SIZE+UNSNAP_TRESHOLD) or ay < (by-RECTANGLE_SIDE_SIZE-UNSNAP_TRESHOLD):
            return False
            
        return True

    def drag_rectangle(self, event):
        closest = self.closest_tag(self.canvas, event.x, event.y)

        if "draggable" in self.canvas.gettags(closest):
            self.canvas.move(closest, event.x - self.canvas.coords(closest)[0], event.y - self.canvas.coords(closest)[1])
            if self.is_snapped_to_core(closest):
                self.canvas.itemconfig(closest, fill="green")
            else:
                self.canvas.itemconfig(closest, fill="blue")
    
    def get_id(self):
        self.last_id += 1
        return self.last_id

    def is_snapped_to_core(self, rectangle):
        r_coords = self.canvas.coords(rectangle)
        core_coords = self.canvas.coords(self.core_rectangle)
        
        horizontal_snapped = r_coords[2] == core_coords[0] or r_coords[0] == core_coords[2]
        vertical_snapped = r_coords[3] == core_coords[1] or r_coords[1] == core_coords[3]
        
        return horizontal_snapped or vertical_snapped

    def mainloop_extended(self):
        self.tkinter_extended_setup_function()
        super().mainloop()

    def spawn_rectangle(self):
        x1 = random.randint((0 + EDGE_ZONE_SIZE), (CANVAS_WIDTH - EDGE_ZONE_SIZE))
        y1 = random.randint((0 + EDGE_ZONE_SIZE), (CANVAS_HEIGHT - EDGE_ZONE_SIZE))
        x2, y2 = x1+RECTANGLE_SIDE_SIZE, y1+RECTANGLE_SIDE_SIZE
        self.last_rectangle = _SnappableRectangle(canvas=self.canvas, x1=x1, y1=y1, x2=x2, y2=y2, fill=str(self.get_random_color()), input_root=self)

        _overlap_issues = True
        while _overlap_issues:
            for other_rectangle in self.rectangles:
                if self.does_overlap(self.last_rectangle, other_rectangle):
                    self.delete_last_rectangle()
                    x1 = random.randint((0 + EDGE_ZONE_SIZE), (CANVAS_WIDTH - EDGE_ZONE_SIZE))
                    y1 = random.randint((0 + EDGE_ZONE_SIZE), (CANVAS_HEIGHT - EDGE_ZONE_SIZE))
                    x2, y2 = x1+RECTANGLE_SIDE_SIZE, y1+RECTANGLE_SIDE_SIZE
                    self.last_rectangle = _SnappableRectangle(canvas=self.canvas, x1=x1, y1=y1, x2=x2, y2=y2, fill=str(self.get_random_color()), input_root=self)
                    _overlap_issues = True
                    continue
                else:
                    _overlap_issues = False

        self.last_rectangle.add_name_and_path()
        self.rectangles.append(self.last_rectangle)

        return self.last_rectangle

    def tkinter_extended_setup_function(self):
        self.title("Discord Cog Manager")
        
        self.canvas.pack(pady=20, padx=20)
        self.canvas.bind("<B1-Motion>", self.drag_rectangle)

        spawn_button = Button(self, text="Spawn Rectangle", command=self.spawn_rectangle, font=(FONT_FAMILY, FONT_SIZE))
        spawn_button.pack(pady=10)

        delete_button = Button(self, text="Delete Last Rectangle", command=self.delete_last_rectangle, font=(FONT_FAMILY, FONT_SIZE))
        delete_button.pack(pady=10)

    @staticmethod
    def activate_cog(cog):
        print(f"Load cogs.{cog}")
        send_command(f"Load cogs.{cog}")

    @staticmethod
    def closest_tag(canvas, x, y):
        min_distance = float("inf")
        closest_item = None

        for item in canvas.find_all():
            coords = canvas.coords(item)
            for i in range(0, len(coords), 2):
                item_x = coords[i]
                item_y = coords[i+1]
                
                distance = ((x - item_x)**2 + (y - item_y)**2)**0.5
                if distance < min_distance:
                    min_distance = distance
                    closest_item = item

        return closest_item

    @staticmethod
    def deactivate_cog(cog):
        print(f"Unload cogs.{cog}")
        send_command(f"Unload cogs.{cog}")

    # @staticmethod
    # def does_overlap(x1, y1, width, height, rectangles):
    #     left = x1 - width/2
    #     right = x1 + width/2
    #     top = y1 - height/2
    #     bottom = y1 + height/2
        
    #     for rect in rectangles:
    #         rect_dict = rect.as_dict()
    #         if (left < rect_dict['right'] and right > rect_dict['left'] and
    #             top < rect_dict['bottom'] and bottom > rect_dict['top']):
    #             return True

    #     return False
    
    @staticmethod
    def get_random_color():
        return "#{:06x}".format(random.randint(0, 0xFFFFFF))

if __name__ == "__main__":
    GUI = Tk_extended()
    GUI.mainloop_extended()
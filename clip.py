import gi
import cairo
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk
import base64
import requests
import os


api_key = os.environ["OPENAI_API_KEY"]

# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


class Screenshot(Gtk.Window):
    def __init__(self):
        super(Screenshot, self).__init__()
        self.set_decorated(False)
        self.set_app_paintable(True)
        self.set_keep_above(True)  # Keep window on top

        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)

        self.set_size_request(Gdk.Screen.width(), Gdk.Screen.height())

        self.connect("draw", self.area_draw)
        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)

        self.start_x = 0
        self.start_y = 0
        self.width = 0
        self.height = 0
        self.drawing = False

        self.was_widget_event = True

        self.set_title("ClipGPT")  # Set a specific window title

        # Create a Gtk.Fixed container
        self.fixed_container = Gtk.Fixed()
        self.add(self.fixed_container)
        self.fixed_container.hide()

        # Create a textbox and button but do not show them yet
        self.textbox = Gtk.Entry()
        self.textbox_event_box = Gtk.EventBox()
        self.textbox_event_box.add(self.textbox)
        self.textbox_event_box.connect("button-press-event", self.on_textbox_clicked)
        self.textbox_event_box.connect("button-release-event", self.on_textbox_clicked)
        self.fixed_container.put(self.textbox_event_box, 0, 0)

        self.button = Gtk.Button(label="Submit")
        self.button.connect("clicked", self.on_button_clicked)
        self.fixed_container.put(self.button, 0, 0)  # Adding to fixed container

        self.textview = Gtk.TextView()
        self.textbuffer = self.textview.get_buffer()
        self.textview_event_box = Gtk.EventBox()
        self.textview_event_box.add(self.textview)
        self.textview_event_box.connect("button-press-event", self.on_textbox_clicked)
        self.textview_event_box.connect("button-release-event", self.on_textbox_clicked)
        self.textview.set_size_request(400, 300)  # Adjust size as needed
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.textview.set_editable(False)
        self.fixed_container.put(self.textview_event_box, 0, 0)

    def on_textbox_clicked(self, widget, event):
        # Handle the textbox click event
        # This prevents the drawing code from being triggered
        print("textbox clicked")

        return True


    def hide(self):
        self.textbox.hide()
        self.textview.hide()
        self.button.hide()

    def area_draw(self, widget, cr):
        cr.set_source_rgba(0, 0, 0, 0.5)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        if self.drawing:
            cr.set_line_width(3)
            cr.set_source_rgba(1, 0, 0, 0.8)
            cr.rectangle(self.start_x, self.start_y, self.width, self.height)
            cr.stroke()

    def on_button_press(self, widget, event):
        self.start_x = event.x
        self.start_y = event.y
        self.drawing = True
        self.textbox.hide()
        self.button.hide()
        self.textview.hide()

    def on_motion_notify(self, widget, event):
        if self.drawing:
            self.width = event.x - self.start_x
            self.height = event.y - self.start_y
            self.queue_draw()

    def on_button_release(self, widget, event):
        self.drawing = False
        self.capture_area()
        self.show_textbox_and_button(event.x, event.y)

    def show_textbox_and_button(self, x, y):
        self.fixed_container.move(self.button, int(x) + 210, int(y))
        self.button.set_size_request(100, 30)
        self.button.show()

        self.fixed_container.move(self.textbox_event_box, int(x), int(y))
        self.textbox.set_size_request(200, 20)
        self.textbox.show()

        self.textbox.grab_focus()

    def on_button_clicked(self, button):
        text = self.textbox.get_text()
        print("Text from textbox:", text)

        base64_image = encode_image("screenshot.png")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        payload = {
            "model": "gpt-4-vision-preview",
            # "stream": True,
            "messages": [
              {
                "role": "user",
                "content": [
                  {
                    "type": "text",
                    "text": text
                  },
                  {
                    "type": "image_url",
                    "image_url": {
                      "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                  }
                ]
              }
            ],
            "max_tokens": 300
        }

        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

        # full_content = ""
        # for chunk in response:
        #     full_content += str(chunk)
        #     print(chunk, "\n", full_content, "\n")
        #     lines = full_content.split("\n")
        #     for line in lines:
        #         if line.startswith("data:"):
        #             print("Line: ", line, "\n")


        print(response.json())

        ai_msg = response.json()["choices"][0]["message"]["content"]

        self.textbuffer.set_text(ai_msg)

        self.textview.show()

    def capture_area(self):
        # Capture the screen area and save it as an image
        gdk_window = Gdk.get_default_root_window()
        x, y, width, height = self.get_position() + self.get_size()
        pb = Gdk.pixbuf_get_from_window(gdk_window, self.start_x, self.start_y, int(self.width), int(self.height))
        pb.savev("screenshot.png", "png", [], [])

def main():
    window = Screenshot()
    window.connect("destroy", Gtk.main_quit)
    window.show_all()
    window.hide()
    window.connect("button-press-event", window.on_button_press)
    window.connect("motion-notify-event", window.on_motion_notify)
    window.connect("button-release-event", window.on_button_release)
    Gtk.main()

if __name__ == "__main__":
    main()


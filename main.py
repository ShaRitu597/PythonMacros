import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
import pyautogui
from pynput import mouse, keyboard
import threading
import json
import time

class MacroStep:
    def __init__(self, action, params):
        self.action = action
        self.params = params

    def to_dict(self):
        return {'action': self.action, 'params': self.params}

    @staticmethod
    def from_dict(data):
        return MacroStep(data['action'], data['params'])

class Macro:
    def __init__(self, steps=None):
        self.steps = steps if steps else []

    def add_step(self, step):
        self.steps.append(step)

    def to_dict(self):
        return [step.to_dict() for step in self.steps]

    @staticmethod
    def from_dict(data):
        return Macro([MacroStep.from_dict(step) for step in data])

class MacroApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Python Macro Recorder")
        self.macro = Macro()
        self.recording = False
        self.setup_gui()

    def setup_gui(self):
        frame = tk.Frame(self.root)
        frame.pack(padx=10, pady=10)

        self.record_btn = tk.Button(frame, text="Record Macro", command=self.start_recording)
        self.record_btn.grid(row=0, column=0, padx=5, pady=5)

        self.edit_btn = tk.Button(frame, text="Edit/Create Macro", command=self.edit_macro)
        self.edit_btn.grid(row=0, column=1, padx=5, pady=5)

        self.play_btn = tk.Button(frame, text="Play Macro", command=self.play_macro)
        self.play_btn.grid(row=0, column=2, padx=5, pady=5)

        self.save_btn = tk.Button(frame, text="Save Macro", command=self.save_macro)
        self.save_btn.grid(row=1, column=0, padx=5, pady=5)

        self.load_btn = tk.Button(frame, text="Load Macro", command=self.load_macro)
        self.load_btn.grid(row=1, column=1, padx=5, pady=5)

        self.status_label = tk.Label(frame, text="Status: Ready")
        self.status_label.grid(row=2, column=0, columnspan=3, pady=10)

    def start_recording(self):
        if self.recording:
            return
        self.recording = True
        self.status_label.config(text="Status: Recording... Press ESC to stop.")
        self.record_thread = threading.Thread(target=self.record_macro_thread, daemon=True)
        self.record_thread.start()

    def record_macro_thread(self):
        self.macro = Macro()
        messagebox.showinfo("Recording", "Macro recording started. Press ESC to stop.")
        self.recording = True
        self._stop_recording = False
        events = []

        def on_click(x, y, button, pressed):
            if not self.recording:
                return False
            if pressed:
                events.append(MacroStep('click', {'x': x, 'y': y, 'button': str(button)}))
            else:
                events.append(MacroStep('release_click', {'x': x, 'y': y, 'button': str(button)}))

        def on_move(x, y):
            if not self.recording:
                return False
            events.append(MacroStep('move', {'x': x, 'y': y}))

        def on_press(key):
            if not self.recording:
                return False
            if key == keyboard.Key.esc:
                self.recording = False
                return False
            try:
                events.append(MacroStep('key_press', {'key': key.char if hasattr(key, 'char') else str(key)}))
            except Exception:
                events.append(MacroStep('key_press', {'key': str(key)}))

        def on_release(key):
            if not self.recording:
                return False
            try:
                events.append(MacroStep('key_release', {'key': key.char if hasattr(key, 'char') else str(key)}))
            except Exception:
                events.append(MacroStep('key_release', {'key': str(key)}))

        mouse_listener = mouse.Listener(on_click=on_click, on_move=on_move)
        keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        mouse_listener.start()
        keyboard_listener.start()
        mouse_listener.join()
        keyboard_listener.join()
        self.macro.steps.extend(events)
        self.status_label.config(text="Status: Ready")
        messagebox.showinfo("Recording", "Macro recording stopped.")

    def edit_macro(self):
        EditMacroWindow(self.root, self.macro)

    def play_macro(self):
        threading.Thread(target=self.play_macro_thread, daemon=True).start()

    def play_macro_thread(self):
        from pynput.keyboard import Controller as KeyboardController
        from pynput.mouse import Controller as MouseController, Button
        self.status_label.config(text="Status: Playing macro...")
        kb = KeyboardController()
        ms = MouseController()
        for step in self.macro.steps:
            if step.action == 'move':
                ms.position = (step.params['x'], step.params['y'])
            elif step.action == 'click':
                btn = Button.left if 'left' in step.params['button'] else Button.right
                ms.position = (step.params['x'], step.params['y'])
                ms.press(btn)
            elif step.action == 'release_click':
                btn = Button.left if 'left' in step.params['button'] else Button.right
                ms.position = (step.params['x'], step.params['y'])
                ms.release(btn)
            elif step.action == 'key_press':
                try:
                    kb.press(step.params['key'])
                except Exception:
                    pass
            elif step.action == 'key_release':
                try:
                    kb.release(step.params['key'])
                except Exception:
                    pass
            elif step.action == 'wait_pixel':
                x, y, color = step.params['x'], step.params['y'], step.params['color']
                while pyautogui.pixel(x, y) != tuple(color):
                    time.sleep(0.1)
            time.sleep(0.2)
        self.status_label.config(text="Status: Ready")

    def save_macro(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if file_path:
            with open(file_path, 'w') as f:
                json.dump(self.macro.to_dict(), f)
            messagebox.showinfo("Saved", "Macro saved successfully.")

    def load_macro(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file_path:
            with open(file_path, 'r') as f:
                data = json.load(f)
                self.macro = Macro.from_dict(data)
            messagebox.showinfo("Loaded", "Macro loaded successfully.")

class EditMacroWindow:
    def __init__(self, master, macro):
        self.top = tk.Toplevel(master)
        self.top.title("Edit/Create Macro")
        self.macro = macro
        self.listbox = tk.Listbox(self.top, width=50)
        self.listbox.pack(padx=10, pady=10)
        self.refresh_list()
        btn_frame = tk.Frame(self.top)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Add Step", command=self.add_step).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Edit Step", command=self.edit_step).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Remove Step", command=self.remove_step).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Close", command=self.top.destroy).pack(side=tk.LEFT, padx=5)
    def edit_step(self):
        sel = self.listbox.curselection()
        if sel:
            idx = sel[0]
            step = self.macro.steps[idx]
            action = simpledialog.askstring("Action", f"Edit action (current: {step.action}):", initialvalue=step.action)
            params = step.params.copy()
            if action == 'move' or action == 'click':
                params['x'] = int(simpledialog.askstring("X", f"Edit X position (current: {params.get('x', '')}):", initialvalue=params.get('x', '')))
                params['y'] = int(simpledialog.askstring("Y", f"Edit Y position (current: {params.get('y', '')}):", initialvalue=params.get('y', '')))
                if action == 'click':
                    params['button'] = simpledialog.askstring("Button", f"Edit button (current: {params.get('button', 'Button.left')}):", initialvalue=params.get('button', 'Button.left'))
            elif action == 'wait_pixel':
                params['x'] = int(simpledialog.askstring("X", f"Edit X position (current: {params.get('x', '')}):", initialvalue=params.get('x', '')))
                params['y'] = int(simpledialog.askstring("Y", f"Edit Y position (current: {params.get('y', '')}):", initialvalue=params.get('y', '')))
                color_str = simpledialog.askstring("Color", f"Edit RGB color (current: {params.get('color', '')}):", initialvalue=','.join(str(c) for c in params.get('color', [255,255,255])))
                params['color'] = [int(c) for c in color_str.split(',')]
            elif action == 'key_press' or action == 'key_release':
                params['key'] = simpledialog.askstring("Key", f"Edit key (current: {params.get('key', '')}):", initialvalue=params.get('key', ''))
            self.macro.steps[idx] = MacroStep(action, params)
            self.refresh_list()

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        for i, step in enumerate(self.macro.steps):
            self.listbox.insert(tk.END, f"{i+1}: {step.action} {step.params}")

    def add_step(self):
        action = simpledialog.askstring("Action", "Enter action (move/click/wait_pixel):")
        params = {}
        if action == 'move' or action == 'click':
            params['x'] = int(simpledialog.askstring("X", "Enter X position:"))
            params['y'] = int(simpledialog.askstring("Y", "Enter Y position:"))
        elif action == 'wait_pixel':
            params['x'] = int(simpledialog.askstring("X", "Enter X position:"))
            params['y'] = int(simpledialog.askstring("Y", "Enter Y position:"))
            color_str = simpledialog.askstring("Color", "Enter RGB color (e.g. 255,255,255):")
            params['color'] = [int(c) for c in color_str.split(',')]
        self.macro.add_step(MacroStep(action, params))
        self.refresh_list()

    def remove_step(self):
        sel = self.listbox.curselection()
        if sel:
            idx = sel[0]
            del self.macro.steps[idx]
            self.refresh_list()

def main():
    root = tk.Tk()
    app = MacroApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()

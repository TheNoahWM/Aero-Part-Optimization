import ast
import operator as op
import tkinter as tk
from tkinter import messagebox
import sys
import os

# ==========================================
# PART 1: The Reader Class
# ==========================================
class container:
    def __init__(self):
        pass

class read:
    def __init__(self, filename):
        self.filename = filename
        self.allowed_ops = {
            ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
            ast.Div: op.truediv, ast.USub: op.neg, ast.Pow: op.pow,
        }

    def safe_eval(self, expr):
        def _eval(node):
            if isinstance(node, ast.Constant): return node.n
            elif isinstance(node, ast.UnaryOp): return self.allowed_ops[type(node.op)](_eval(node.operand))
            elif isinstance(node, ast.BinOp): return self.allowed_ops[type(node.op)](_eval(node.left), _eval(node.right))
            else: raise ValueError(f"Unsupported expression: {expr}")
        return _eval(ast.parse(expr, mode='eval').body)

    def load(self):
        a = container()
        try:
            with open(self.filename) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"): continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip(); value = value.strip()
                        if value.startswith("$"): value = value[1:].strip()
                        else:
                            try: value = self.safe_eval(value)
                            except: pass
                        setattr(a, key, value)
        except FileNotFoundError:
            print(f"Error: '{self.filename}' not found.")
        return a

# ==========================================
# PART 2: The GUI Classes
# ==========================================

class ConfigEditor:
    def __init__(self, master, filename):
        self.master = master
        self.filename = filename
        self.action = "close" # Default action
        
        master.title(f"Editing: {os.path.basename(filename)}")
        master.geometry("600x650")

        # Scroll Setup
        self.canvas = tk.Canvas(master)
        self.scrollbar = tk.Scrollbar(master, orient="vertical", command=self.canvas.yview)
        self.frame = tk.Frame(self.canvas)
        self.frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        self.entries = {}
        self.load_data()
        
        # Buttons
        btn_frame = tk.Frame(master, bg="#eeeeee", pady=10)
        btn_frame.pack(side="bottom", fill="x")

        # Back
        tk.Button(btn_frame, text="<< Back", command=self.go_back, bg="#ffebcd", width=12).pack(side="left", padx=10)
        # Save
        tk.Button(btn_frame, text="Save", command=self.save_only, bg="white", width=10).pack(side="left", padx=5)
        # Save & Run
        tk.Button(btn_frame, text="Save & Run", command=self.save_and_run, bg="#ccffcc", width=12).pack(side="left", padx=5)
        # Exit
        tk.Button(btn_frame, text="Exit App", command=self.exit_app, bg="#ffcccc", width=10).pack(side="right", padx=10)

    def load_data(self):
        try:
            with open(self.filename, "r") as f:
                r = 0
                for line in f:
                    line = line.strip()
                    if not line: continue
                    if line.startswith("#"):
                        tk.Label(self.frame, text=line, fg="gray").grid(row=r, column=0, columnspan=2, sticky="w", padx=10, pady=2)
                        r += 1
                    elif "=" in line:
                        k, v = line.split("=", 1)
                        tk.Label(self.frame, text=k.strip(), font=("Arial", 10, "bold")).grid(row=r, column=0, sticky="e", padx=10, pady=5)
                        e = tk.Entry(self.frame, width=45); e.insert(0, v.strip()); e.grid(row=r, column=1, sticky="w", padx=10, pady=5)
                        self.entries[k.strip()] = e; r += 1
        except: tk.Label(self.frame, text="File not found!", fg="red").pack()

    def write(self):
        try:
            with open(self.filename, "w") as f:
                f.write(f"# Updated via GUI\n")
                for k, e in self.entries.items(): f.write(f"{k} = {e.get()}\n")
            return True
        except Exception as e:
            messagebox.showerror("Error", str(e)); return False

    def save_only(self):
        if self.write(): messagebox.showinfo("Saved", "File saved!")

    def save_and_run(self):
        if self.write():
            self.action = "run"
            self.master.destroy()

    def go_back(self):
        self.action = "back"
        self.master.destroy()

    def exit_app(self):
        sys.exit() # Hard exit

class Dashboard:
    def __init__(self, master, files_dict):
        self.master = master
        self.selected_file = None
        self.action = "exit" # Default

        master.title("Sim Dashboard")
        master.geometry("350x550")
        
        tk.Label(master, text="Simulation Control", font=("Arial", 16, "bold")).pack(pady=20)
        tk.Label(master, text="Edit Parameters:", fg="gray").pack(pady=5)
        
        for label, path in files_dict.items():
            tk.Button(master, text=f"Edit {label}", command=lambda p=path: self.select_file(p), width=25, pady=5).pack(pady=5)
        
        tk.Label(master, text="-"*30).pack(pady=20)
        tk.Button(master, text="RUN SIMULATION", command=self.run_sim, bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), width=20, height=2).pack(pady=10)
        tk.Button(master, text="Exit App", command=sys.exit, bg="#ffcccc").pack(side="bottom", pady=20)

    def select_file(self, path):
        self.selected_file = path
        self.action = "edit"
        self.master.destroy()

    def run_sim(self):
        self.action = "run"
        self.master.destroy()

# ==========================================
# PART 3: The Main Controller Loop
# ==========================================

def open_editor_window(filename):
    """Opens editor, returns 'back', 'run', or 'close'"""
    root = tk.Tk()
    app = ConfigEditor(root, filename)
    root.mainloop()
    return app.action

def open_dashboard_window(files_dict):
    """Opens dashboard, returns ('edit', filepath) or ('run', None)"""
    root = tk.Tk()
    app = Dashboard(root, files_dict)
    root.mainloop()
    return app.action, app.selected_file

def show_launcher(files_dict, script_name=None):
    """
    Main loop that switches between Dashboard and Editor.
    Only returns when the user actually wants to RUN the simulation.
    """
    while True:
        # 1. Show Dashboard
        action, filepath = open_dashboard_window(files_dict)
        
        if action == "run":
            return # Break loop -> Run Main Script
        
        elif action == "edit":
            # 2. Show Editor (Loop until they go back or run)
            while True:
                editor_action = open_editor_window(filepath)
                
                if editor_action == "run":
                    return # Break all loops -> Run Main Script
                elif editor_action == "back":
                    break # Break inner loop -> Go back to Dashboard
                else:
                    # If window closed with X, assume we want to go back to dashboard (or exit)
                    break
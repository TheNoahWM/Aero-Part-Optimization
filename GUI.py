import tkinter as tk
from tkinter import messagebox
from tkinter import scrolledtext
import sys
import os

# --- CONFIGURATION ---
FILENAME = "C:/Users/noahw/Documents/DBF Coding/Tail Optimization/Tail_Input_Parameters.txt"  # Change this to your actual file name

class ConfigEditor:
    def __init__(self, master):
        self.master = master
        master.title("Config Editor")
        master.geometry("500x600")

        self.data_entries = {}
        self.comments = [] # To store lines that are comments so we don't lose them completely
        
        # 1. Main Frame with Scrollbar (in case you have many parameters)
        self.canvas = tk.Canvas(master)
        self.scrollbar = tk.Scrollbar(master, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # 2. Load the data
        self.load_data()

        # 3. Create Buttons (Save, Run)
        self.button_frame = tk.Frame(master)
        self.button_frame.pack(side="bottom", fill="x", pady=10)

        self.btn_save = tk.Button(self.button_frame, text="Save Changes", command=self.save_data, bg="#dddddd")
        self.btn_save.pack(side="left", padx=20, expand=True)

        self.btn_quit = tk.Button(self.button_frame, text="Quit", command=master.quit, bg="#ffcccc")
        self.btn_quit.pack(side="right", padx=20, expand=True)

    def load_data(self):
        """Reads the raw file to preserve formulas like 60/39.37"""
        try:
            with open(FILENAME, "r") as f:
                row_idx = 0
                for line in f:
                    line = line.strip()
                    # Skip empty lines
                    if not line: 
                        continue
                    
                    # Store comments blindly (simple handling)
                    if line.startswith("#"):
                        tk.Label(self.scrollable_frame, text=line, fg="gray").grid(row=row_idx, column=0, columnspan=2, sticky="w", padx=5)
                        row_idx += 1
                        continue

                    # Handle Key = Value
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()

                        # Create Label
                        lbl = tk.Label(self.scrollable_frame, text=key, font=("Arial", 10, "bold"))
                        lbl.grid(row=row_idx, column=0, sticky="e", padx=5, pady=2)

                        # Create Input Box
                        entry = tk.Entry(self.scrollable_frame, width=40)
                        entry.insert(0, value) # Insert current value
                        entry.grid(row=row_idx, column=1, sticky="w", padx=5, pady=2)

                        # Store reference to entry so we can get value later
                        self.data_entries[key] = entry
                        row_idx += 1
                        
        except FileNotFoundError:
            messagebox.showerror("Error", f"Could not find {FILENAME}")

    def save_data(self):
        """Writes the inputs back to the file"""
        try:
            with open(FILENAME, "w") as f:
                # Note: This simple saver rewrites the file. 
                # To keep complex comment structures, you'd need a more complex parser.
                
                f.write(f"# Updated config file\n")
                
                for key, entry_widget in self.data_entries.items():
                    val = entry_widget.get()
                    f.write(f"{key} = {val}\n")
            
            messagebox.showinfo("Success", "File Saved Successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ConfigEditor(root)
    root.mainloop()
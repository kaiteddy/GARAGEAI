#!/usr/bin/env python3
"""
Complete Garage Management System Launcher

This script provides a simple launcher for the Complete Garage Management System
that integrates GA4 data with MOT reminders, customer management, invoicing, and more.
"""

import os
import sys
import subprocess
import webbrowser
import time
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path

def find_python_executable():
    """Find the Python executable to use"""
    # Try using the current Python interpreter
    python_exe = sys.executable
    if python_exe and os.path.exists(python_exe):
        return python_exe
    
    # Try common Python paths
    common_paths = [
        "python",
        "python3",
        r"C:\Python39\python.exe",
        r"C:\Python310\python.exe",
        r"C:\Python311\python.exe",
        r"C:\Program Files\Python39\python.exe",
        r"C:\Program Files\Python310\python.exe",
        r"C:\Program Files\Python311\python.exe"
    ]
    
    for path in common_paths:
        try:
            # Check if the command exists and is executable
            subprocess.run([path, "--version"], capture_output=True, check=True)
            return path
        except (subprocess.SubprocessError, FileNotFoundError):
            continue
    
    return None

def find_ga4_installation():
    """Find GA4 installation directory"""
    # Common installation paths
    common_paths = [
        r"C:\Program Files (x86)\Garage Assistant GA4",
        r"C:\Program Files\Garage Assistant GA4",
        r"C:\Garage Assistant GA4"
    ]
    
    # Check common paths
    for path in common_paths:
        if os.path.exists(path) and os.path.isdir(path):
            return path
    
    # Check if environment variable is set
    if 'GA4_PATH' in os.environ:
        path = os.environ['GA4_PATH']
        if os.path.exists(path) and os.path.isdir(path):
            return path
    
    return None

def launch_system(system_script, ga4_path=None, port=5000, debug=False):
    """Launch the specified system script"""
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Find Python executable
    python_exe = find_python_executable()
    if not python_exe:
        messagebox.showerror("Error", "Could not find Python executable. Please install Python 3.6 or higher.")
        return False
    
    # Check if system script exists
    system_script_path = os.path.join(script_dir, system_script)
    if not os.path.exists(system_script_path):
        messagebox.showerror("Error", f"Could not find {system_script} at {system_script_path}")
        return False
    
    # Build command
    cmd = [python_exe, system_script_path]
    if ga4_path:
        cmd.extend(["--ga4-path", ga4_path])
    if port:
        cmd.extend(["--port", str(port)])
    if debug:
        cmd.append("--debug")
    
    try:
        # Run the system script
        process = subprocess.Popen(
            cmd,
            cwd=script_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Wait for the server to start
        started = False
        for line in process.stdout:
            print(line.strip())
            if "Running on http://" in line:
                started = True
                # Extract the URL from the output
                url = line.strip().split("Running on ")[1].split()[0]
                # Open web browser
                print(f"Opening browser to {url}")
                webbrowser.open(url)
                break
            
            # Check for 5 seconds max
            if process.poll() is not None:
                break
        
        if not started and process.poll() is None:
            # If we didn't see the "Running on" message but the process is still running,
            # assume it started successfully and open the browser
            url = f"http://localhost:{port}"
            print(f"Opening browser to {url}")
            webbrowser.open(url)
            started = True
        
        if not started:
            error_output = process.stderr.read()
            messagebox.showerror("Error", f"Could not start the system. Error: {error_output}")
            return False
        
        return process
    
    except Exception as e:
        messagebox.showerror("Error", f"Error launching system: {str(e)}")
        return False

class LauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Garage Management System Launcher")
        self.root.geometry("600x400")
        self.root.resizable(True, True)
        
        self.process = None
        self.ga4_path = find_ga4_installation() or ""
        
        self.create_widgets()
    
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Complete Garage Management System", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # GA4 Path
        ga4_frame = ttk.Frame(main_frame)
        ga4_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(ga4_frame, text="GA4 Installation Path:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.ga4_path_var = tk.StringVar(value=self.ga4_path)
        ga4_entry = ttk.Entry(ga4_frame, textvariable=self.ga4_path_var, width=40)
        ga4_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(ga4_frame, text="Browse", command=self.browse_ga4_path).pack(side=tk.LEFT, padx=(10, 0))
        
        # Port
        port_frame = ttk.Frame(main_frame)
        port_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(port_frame, text="Port:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.port_var = tk.IntVar(value=5000)
        port_entry = ttk.Entry(port_frame, textvariable=self.port_var, width=10)
        port_entry.pack(side=tk.LEFT)
        
        # Debug mode
        self.debug_var = tk.BooleanVar(value=False)
        debug_check = ttk.Checkbutton(main_frame, text="Debug Mode", variable=self.debug_var)
        debug_check.pack(anchor=tk.W, pady=5)
        
        # Separator
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=20)
        
        # Launch buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        # Complete System button
        complete_button = ttk.Button(
            buttons_frame, 
            text="Launch Complete System", 
            command=self.launch_complete_system,
            style="Accent.TButton"
        )
        complete_button.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # MOT Reminder button
        mot_button = ttk.Button(
            buttons_frame, 
            text="Launch MOT Reminder", 
            command=self.launch_mot_reminder
        )
        mot_button.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Direct Access button
        direct_button = ttk.Button(
            buttons_frame, 
            text="Launch GA4 Direct Access", 
            command=self.launch_direct_access
        )
        direct_button.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Status
        self.status_var = tk.StringVar(value="Ready to launch")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, font=("Helvetica", 10))
        status_label.pack(pady=(20, 0))
        
        # Configure style for accent button
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Helvetica", 10, "bold"))
    
    def browse_ga4_path(self):
        from tkinter import filedialog
        path = filedialog.askdirectory(title="Select GA4 Installation Directory")
        if path:
            self.ga4_path_var.set(path)
    
    def launch_complete_system(self):
        self.stop_current_process()
        self.status_var.set("Launching Complete Garage Management System...")
        self.root.update()
        
        self.process = launch_system(
            "integrated_system.py",
            ga4_path=self.ga4_path_var.get(),
            port=self.port_var.get(),
            debug=self.debug_var.get()
        )
        
        if self.process:
            self.status_var.set("Complete Garage Management System is running")
        else:
            self.status_var.set("Failed to launch Complete Garage Management System")
    
    def launch_mot_reminder(self):
        self.stop_current_process()
        self.status_var.set("Launching MOT Reminder System...")
        self.root.update()
        
        self.process = launch_system(
            "launch_mot_reminder.py",
            ga4_path=self.ga4_path_var.get(),
            port=self.port_var.get(),
            debug=self.debug_var.get()
        )
        
        if self.process:
            self.status_var.set("MOT Reminder System is running")
        else:
            self.status_var.set("Failed to launch MOT Reminder System")
    
    def launch_direct_access(self):
        self.stop_current_process()
        self.status_var.set("Launching GA4 Direct Access Tool...")
        self.root.update()
        
        # Get the directory of this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Find Python executable
        python_exe = find_python_executable()
        if not python_exe:
            messagebox.showerror("Error", "Could not find Python executable. Please install Python 3.6 or higher.")
            self.status_var.set("Failed to launch GA4 Direct Access Tool")
            return
        
        # Check if ga4_direct_access.py exists
        direct_access_script = os.path.join(script_dir, "ga4_direct_access.py")
        if not os.path.exists(direct_access_script):
            messagebox.showerror("Error", f"Could not find ga4_direct_access.py at {direct_access_script}")
            self.status_var.set("Failed to launch GA4 Direct Access Tool")
            return
        
        try:
            # Run the direct access script
            cmd = [python_exe, direct_access_script]
            if self.ga4_path_var.get():
                cmd.extend(["--ga4-path", self.ga4_path_var.get()])
            
            self.process = subprocess.Popen(
                cmd,
                cwd=script_dir
            )
            
            self.status_var.set("GA4 Direct Access Tool is running")
        
        except Exception as e:
            messagebox.showerror("Error", f"Error launching GA4 Direct Access Tool: {str(e)}")
            self.status_var.set("Failed to launch GA4 Direct Access Tool")
    
    def stop_current_process(self):
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                pass
    
    def on_closing(self):
        self.stop_current_process()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = LauncherApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()

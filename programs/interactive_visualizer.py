#!/usr/bin/env python3
"""
Interactive Foot Pressure Sensor Data Visualization Tool
Supports user upload of H5 data files and video files, with different visualization modes
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import os
import threading
import sys
from pathlib import Path

class InteractiveVisualizer:
    def __init__(self, root):
        self.root = root
        self.root.title("Foot Pressure Sensor Data Visualization Tool")
        self.root.geometry("700x600")
        
        # File path variables
        self.h5_file_path = tk.StringVar()
        self.video_file_path = tk.StringVar()
        
        # Mode selection variable
        self.visualization_mode = tk.StringVar(value="with_video")
        
        self.setup_ui()
        
    def on_mode_change(self):
        """Handle mode switching"""
        mode = self.visualization_mode.get()
        if mode == "no_video":
            # No Video mode: disable video file selection
            self.video_label.config(text="Video File (Optional):")
            self.video_entry.config(state="disabled")
            self.video_button.config(state="disabled")
        else:
            # With Video mode: enable video file selection
            self.video_label.config(text="Video File:")
            self.video_entry.config(state="normal")
            self.video_button.config(state="normal")
        
    def setup_ui(self):
        """Setup user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="Foot Pressure Sensor Data Visualization Tool", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # File selection area
        file_frame = ttk.LabelFrame(main_frame, text="File Selection", padding="10")
        file_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # H5 file selection
        ttk.Label(file_frame, text="H5 Data File:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(file_frame, textvariable=self.h5_file_path, width=50).grid(row=0, column=1, padx=(10, 5), pady=5)
        ttk.Button(file_frame, text="Browse", command=self.browse_h5_file).grid(row=0, column=2, pady=5)
        
        # Video file selection
        self.video_label = ttk.Label(file_frame, text="Video File:")
        self.video_label.grid(row=1, column=0, sticky=tk.W, pady=5)
        self.video_entry = ttk.Entry(file_frame, textvariable=self.video_file_path, width=50)
        self.video_entry.grid(row=1, column=1, padx=(10, 5), pady=5)
        self.video_button = ttk.Button(file_frame, text="Browse", command=self.browse_video_file)
        self.video_button.grid(row=1, column=2, pady=5)
        
        # Visualization mode selection
        mode_frame = ttk.LabelFrame(main_frame, text="Visualization Mode", padding="10")
        mode_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 20))
        
        ttk.Radiobutton(mode_frame, text="With Video (Include Video Frames)", 
                       variable=self.visualization_mode, value="with_video",
                       command=self.on_mode_change).grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Radiobutton(mode_frame, text="No Video (Sensor Data Only)", 
                       variable=self.visualization_mode, value="no_video",
                       command=self.on_mode_change).grid(row=1, column=0, sticky=tk.W, pady=5)
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=(0, 20))
        
        self.start_button = ttk.Button(button_frame, text="Start Visualization", 
                                     command=self.start_visualization, style="Accent.TButton")
        self.start_button.grid(row=0, column=0, padx=(0, 10))
        
        self.clear_button = ttk.Button(button_frame, text="Clear Selection", 
                                     command=self.clear_selections)
        self.clear_button.grid(row=0, column=1)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Status label
        self.status_label = ttk.Label(main_frame, text="Please select files and start visualization", 
                                    foreground="blue")
        self.status_label.grid(row=5, column=0, columnspan=3)
        
        # Log text area
        log_frame = ttk.LabelFrame(main_frame, text="Processing Log", padding="10")
        log_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        
        self.log_text = tk.Text(log_frame, height=10, width=70)
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(6, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Initialize mode state
        self.on_mode_change()
        
    def browse_h5_file(self):
        """Browse H5 file"""
        filename = filedialog.askopenfilename(
            title="Select H5 Data File",
            filetypes=[("HDF5 files", "*.h5"), ("All files", "*.*")]
        )
        if filename:
            self.h5_file_path.set(filename)
            self.log_message(f"Selected H5 file: {os.path.basename(filename)}")
    
    def browse_video_file(self):
        """Browse video file"""
        filename = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("Video files", "*.MOV *.mp4 *.avi"), ("All files", "*.*")]
        )
        if filename:
            self.video_file_path.set(filename)
            self.log_message(f"Selected video file: {os.path.basename(filename)}")
    
    def clear_selections(self):
        """Clear all selections"""
        self.h5_file_path.set("")
        self.video_file_path.set("")
        self.log_text.delete(1.0, tk.END)
        self.status_label.config(text="Please select files and start visualization", foreground="blue")
    
    def log_message(self, message):
        """Add log message"""
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def validate_inputs(self):
        """Validate input files"""
        if not self.h5_file_path.get():
            messagebox.showerror("Error", "Please select H5 data file")
            return False
        
        if not os.path.exists(self.h5_file_path.get()):
            messagebox.showerror("Error", "H5 file does not exist")
            return False
        
        # Only With Video mode requires video file
        if self.visualization_mode.get() == "with_video":
            if not self.video_file_path.get():
                messagebox.showerror("Error", "With Video mode requires video file selection")
                return False
            
            if not os.path.exists(self.video_file_path.get()):
                messagebox.showerror("Error", "Video file does not exist")
                return False
        
        return True
    
    def start_visualization(self):
        """Start visualization generation"""
        if not self.validate_inputs():
            return
        
        # Disable start button
        self.start_button.config(state="disabled")
        self.progress.start()
        self.status_label.config(text="Generating visualization...", foreground="orange")
        
        # Run in new thread
        thread = threading.Thread(target=self.run_visualization)
        thread.daemon = True
        thread.start()
    
    def run_visualization(self):
        """Run visualization generation"""
        try:
            h5_file = self.h5_file_path.get()
            video_file = self.video_file_path.get()
            mode = self.visualization_mode.get()
            
            self.log_message("=" * 60)
            self.log_message(f"Starting visualization generation - Mode: {mode}")
            self.log_message(f"H5 file: {os.path.basename(h5_file)}")
            if video_file:
                self.log_message(f"Video file: {os.path.basename(video_file)}")
            
            # Switch to project root directory
            project_root = Path(__file__).parent.parent
            os.chdir(project_root)
            self.log_message(f"Working directory: {project_root}")
            
            # Select different scripts based on mode
            if mode == "with_video":
                self.log_message("Step 1/2: Running viz_generate_frames.py...")
                self.log_message("Progress: Generating frames with video synchronization...")
                cmd = [
                    sys.executable, "programs/viz_generate_frames.py",
                    h5_file, video_file
                ]
            else:  # no_video
                self.log_message("Step 1/2: Running viz_sensor_data_no_video.py...")
                self.log_message("Progress: Generating frames with sensor data only...")
                cmd = [
                    sys.executable, "programs/viz_sensor_data_no_video.py",
                    h5_file
                ]
            
            # Run first script
            self.log_message("Executing command: " + " ".join(cmd))
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
            
            if result.returncode != 0:
                self.log_message(f"Error: {result.stderr}")
                self.root.after(0, lambda: self.visualization_failed(f"Frame generation failed: {result.stderr}"))
                return
            
            self.log_message("✓ Frame generation completed successfully!")
            self.log_message("Step 2/2: Running frames_to_video_html.py...")
            self.log_message("Progress: Creating interactive HTML player...")
            
            # Run HTML generation script
            html_cmd = [sys.executable, "programs/frames_to_video_html.py", h5_file]
            self.log_message("Executing command: " + " ".join(html_cmd))
            html_result = subprocess.run(html_cmd, capture_output=True, text=True, cwd=project_root)
            
            if html_result.returncode != 0:
                self.log_message(f"Warning: {html_result.stderr}")
            else:
                self.log_message("✓ HTML generation completed successfully!")
            
            self.log_message("=" * 60)
            self.log_message("🎉 Visualization generation completed!")
            self.log_message("Output files:")
            self.log_message(f"  - Frames: frames/{os.path.splitext(os.path.basename(h5_file))[0]}/")
            self.log_message(f"  - HTML: exported_html/")
            
            # Success completion
            self.root.after(0, self.visualization_success)
            
        except Exception as e:
            self.log_message(f"Error occurred: {str(e)}")
            self.root.after(0, lambda: self.visualization_failed(f"Error occurred: {str(e)}"))
    
    def visualization_success(self):
        """Visualization generation successful"""
        self.progress.stop()
        self.start_button.config(state="normal")
        self.status_label.config(text="Visualization completed successfully!", foreground="green")
        
        # Ask if user wants to open output folder
        if messagebox.askyesno("Success", "Visualization generation completed!\nWould you like to open the output folder?"):
            output_dir = Path("exported_html")
            if output_dir.exists():
                if sys.platform == "darwin":  # macOS
                    subprocess.run(["open", str(output_dir)])
                elif sys.platform == "win32":  # Windows
                    subprocess.run(["explorer", str(output_dir)])
                else:  # Linux
                    subprocess.run(["xdg-open", str(output_dir)])
    
    def visualization_failed(self, error_msg):
        """Visualization generation failed"""
        self.progress.stop()
        self.start_button.config(state="normal")
        self.status_label.config(text="Generation failed", foreground="red")
        messagebox.showerror("Error", f"Visualization generation failed:\n{error_msg}")

def main():
    """Main function"""
    root = tk.Tk()
    
    # Set style
    style = ttk.Style()
    style.theme_use('clam')
    
    # Create application
    app = InteractiveVisualizer(root)
    
    # Run application
    root.mainloop()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Simple GUI for Point Annotation
Click to assign foreground/background points on images
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageDraw
import json
import os
from pathlib import Path

class PointAnnotationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Point Annotation Tool")
        self.root.geometry("1400x900")
        
        # State variables
        self.current_image = None
        self.current_image_path = None
        self.photo = None
        self.canvas_image = None
        self.scale_factor = 1.0
        self.canvas_width = 800
        self.canvas_height = 600
        
        # Directory and image management
        self.image_directory = None
        self.image_files = []
        self.current_image_index = 0
        self.slider_updating = False  # Prevent slider feedback loops
        
        # Annotation data
        self.foreground_points = []
        self.background_points = []
        self.point_mode = "foreground"  # "foreground" or "background"
        
        # Setup GUI
        self.setup_gui()
        
    def setup_gui(self):
        """Setup the GUI layout"""
        
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Control panel (left side)
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # File operations
        file_frame = ttk.LabelFrame(control_frame, text="File Operations", padding=10)
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(file_frame, text="Select Directory", command=self.select_directory).pack(fill=tk.X, pady=2)
        ttk.Button(file_frame, text="Load Single Image", command=self.load_single_image).pack(fill=tk.X, pady=2)
        ttk.Button(file_frame, text="Save Annotations", command=self.save_annotations).pack(fill=tk.X, pady=2)
        
        # Navigation frame
        nav_frame = ttk.LabelFrame(control_frame, text="Navigation", padding=10)
        nav_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Navigation buttons
        nav_buttons_frame = ttk.Frame(nav_frame)
        nav_buttons_frame.pack(fill=tk.X, pady=2)
        
        ttk.Button(nav_buttons_frame, text="◀ Previous", command=self.previous_image).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(nav_buttons_frame, text="Next ▶", command=self.next_image).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Frame selector
        frame_selector_frame = ttk.Frame(nav_frame)
        frame_selector_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(frame_selector_frame, text="Frame:").pack(side=tk.LEFT)
        
        # Frame number entry
        self.frame_entry = ttk.Entry(frame_selector_frame, width=8)
        self.frame_entry.pack(side=tk.LEFT, padx=(5, 5))
        self.frame_entry.bind('<Return>', self.jump_to_frame_entry)
        
        ttk.Button(frame_selector_frame, text="Go", command=self.jump_to_frame_entry).pack(side=tk.LEFT, padx=(0, 5))
        
        # Frame slider
        self.frame_var = tk.IntVar()
        self.frame_slider = ttk.Scale(nav_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                                     variable=self.frame_var, command=self.on_slider_change)
        self.frame_slider.pack(fill=tk.X, pady=2)
        
        # Quick jump buttons
        quick_jump_frame = ttk.Frame(nav_frame)
        quick_jump_frame.pack(fill=tk.X, pady=2)
        
        ttk.Button(quick_jump_frame, text="First", command=self.jump_to_first).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(quick_jump_frame, text="-10", command=lambda: self.jump_relative(-10)).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_jump_frame, text="-100", command=lambda: self.jump_relative(-100)).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_jump_frame, text="+100", command=lambda: self.jump_relative(100)).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_jump_frame, text="+10", command=lambda: self.jump_relative(10)).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_jump_frame, text="Last", command=self.jump_to_last).pack(side=tk.RIGHT, padx=(2, 0))
        
        # Image info
        self.image_info_label = ttk.Label(nav_frame, text="No directory selected")
        self.image_info_label.pack(pady=2)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(nav_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=2)
        
        # Point mode selection
        mode_frame = ttk.LabelFrame(control_frame, text="Point Mode", padding=10)
        mode_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.mode_var = tk.StringVar(value="foreground")
        ttk.Radiobutton(mode_frame, text="Foreground (Green)", variable=self.mode_var, 
                       value="foreground", command=self.change_mode).pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="Background (Red)", variable=self.mode_var, 
                       value="background", command=self.change_mode).pack(anchor=tk.W)
        
        # Point management
        points_frame = ttk.LabelFrame(control_frame, text="Point Management", padding=10)
        points_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(points_frame, text="Clear All Points", command=self.clear_all_points).pack(fill=tk.X, pady=2)
        ttk.Button(points_frame, text="Clear Foreground", command=self.clear_foreground).pack(fill=tk.X, pady=2)
        ttk.Button(points_frame, text="Clear Background", command=self.clear_background).pack(fill=tk.X, pady=2)
        ttk.Button(points_frame, text="Undo Last Point", command=self.undo_last_point).pack(fill=tk.X, pady=2)
        
        # Separator
        ttk.Separator(points_frame, orient='horizontal').pack(fill=tk.X, pady=5)
        
        ttk.Button(points_frame, text="Delete Current Annotations", command=self.clear_current_annotations).pack(fill=tk.X, pady=2)
        ttk.Button(points_frame, text="Batch Save All", command=self.batch_save_all_annotations).pack(fill=tk.X, pady=2)
        
        # Point counts
        self.fg_count_label = ttk.Label(points_frame, text="Foreground: 0")
        self.fg_count_label.pack(anchor=tk.W, pady=2)
        
        self.bg_count_label = ttk.Label(points_frame, text="Background: 0")
        self.bg_count_label.pack(anchor=tk.W, pady=2)
        
        # Instructions
        instructions_frame = ttk.LabelFrame(control_frame, text="Instructions", padding=10)
        instructions_frame.pack(fill=tk.X, pady=(0, 10))
        
        instructions = """
1. Select directory or load single image
2. Navigate using buttons, slider, or entry
3. Select point mode (F/B keys)
4. Click on image to add points
5. Green = Foreground, Red = Background
6. Annotations auto-save when switching

Navigation:
- Slider: Drag to any frame
- Entry: Type frame # and press Enter
- Quick jumps: -100, -10, +10, +100

Keyboard shortcuts:
- F: Foreground mode
- B: Background mode
- C: Clear all points
- S: Save annotations
- ←/→: Navigate frames
- Space: Next frame
- Home/End: First/Last frame
- PgUp/PgDn: Jump ±10 frames
        """
        ttk.Label(instructions_frame, text=instructions, justify=tk.LEFT).pack()
        
        # Canvas frame (right side)
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Canvas with scrollbars
        self.canvas = tk.Canvas(canvas_frame, bg="white", width=self.canvas_width, height=self.canvas_height)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack scrollbars and canvas
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind events
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.root.bind("<Key>", self.on_key_press)
        self.root.focus_set()  # Enable keyboard events
        
    def select_directory(self):
        """Select a directory containing images"""
        
        directory = filedialog.askdirectory(title="Select Image Directory")
        
        if directory:
            self.image_directory = directory
            
            # Find all image files
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif', '.webp'}
            self.image_files = []
            
            for file_path in Path(directory).iterdir():
                if file_path.suffix.lower() in image_extensions:
                    self.image_files.append(str(file_path))
            
            self.image_files.sort()  # Sort alphabetically
            
            if self.image_files:
                self.current_image_index = 0
                self.load_current_image()
                self.update_navigation_info()
                print(f"✓ Loaded directory with {len(self.image_files)} images")
            else:
                messagebox.showwarning("Warning", "No image files found in selected directory")
    
    def load_single_image(self):
        """Load a single image file (legacy mode)"""
        
        file_path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff *.gif *.webp"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            # Set up single image mode
            self.image_directory = str(Path(file_path).parent)
            self.image_files = [file_path]
            self.current_image_index = 0
            self.load_current_image()
            self.update_navigation_info()
    
    def load_current_image(self):
        """Load the current image based on index"""
        
        if not self.image_files or self.current_image_index >= len(self.image_files):
            return
        
        # Save current annotations before switching
        if self.current_image_path and (self.foreground_points or self.background_points):
            self.auto_save_annotations()
        
        file_path = self.image_files[self.current_image_index]
        
        try:
            self.current_image_path = file_path
            self.current_image = Image.open(file_path)
            
            # Load existing annotations for this image
            self.load_existing_annotations()
            
            # Display image
            self.display_image()
            
            # Update window title
            self.root.title(f"Point Annotation Tool - {Path(file_path).name}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {e}")
    
    def previous_image(self):
        """Navigate to previous image"""
        
        if not self.image_files:
            return
        
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self.load_current_image()
            self.update_navigation_info()
    
    def next_image(self):
        """Navigate to next image"""
        
        if not self.image_files:
            return
        
        if self.current_image_index < len(self.image_files) - 1:
            self.current_image_index += 1
            self.load_current_image()
            self.update_navigation_info()
    
    def update_navigation_info(self):
        """Update navigation information display"""
        
        if not self.image_files:
            self.image_info_label.config(text="No directory selected")
            self.progress_var.set(0)
            self.frame_slider.configure(to=0)
            self.frame_entry.delete(0, tk.END)
            return
        
        current = self.current_image_index + 1
        total = len(self.image_files)
        filename = Path(self.image_files[self.current_image_index]).name
        
        # Extract frame number from filename for display
        frame_num = self.extract_frame_index(filename)
        
        self.image_info_label.config(text=f"{current}/{total}: {filename} (Frame {frame_num})")
        self.progress_var.set((current / total) * 100)
        
        # Update slider and entry
        self.slider_updating = True
        self.frame_slider.configure(to=total-1)
        self.frame_var.set(self.current_image_index)
        self.frame_entry.delete(0, tk.END)
        self.frame_entry.insert(0, str(current))
        self.slider_updating = False
    
    def get_annotation_path(self, image_path):
        """Get the annotation file path that preserves source directory structure"""
        
        image_path = Path(image_path)
        
        # Get the source directory name
        source_dir_name = image_path.parent.name
        
        # Create annotation directory structure: annotations/{source_dir_name}/
        annotation_dir = Path('annotations') / source_dir_name
        annotation_dir.mkdir(parents=True, exist_ok=True)
        
        # Annotation file path
        annotation_path = annotation_dir / f"{image_path.stem}_annotations.json"
        
        return annotation_path
    
    def load_existing_annotations(self):
        """Load existing annotations for the current image"""
        
        if not self.current_image_path:
            return
        
        # Clear current annotations
        self.foreground_points = []
        self.background_points = []
        
        # Look for existing annotation file
        annotation_path = self.get_annotation_path(self.current_image_path)
        
        if annotation_path.exists():
            try:
                with open(annotation_path, 'r') as f:
                    annotations = json.load(f)
                
                self.foreground_points = annotations.get("foreground_points", [])
                self.background_points = annotations.get("background_points", [])
                
                print(f"✓ Loaded existing annotations: {len(self.foreground_points)} FG, {len(self.background_points)} BG")
                
            except Exception as e:
                print(f"⚠ Failed to load existing annotations: {e}")
        
        # Update display
        self.update_point_counts()
    
    def display_image(self):
        """Display the current image on canvas"""
        
        if self.current_image is None:
            return
        
        # Calculate scale to fit canvas
        img_width, img_height = self.current_image.size
        canvas_width = self.canvas.winfo_width() or self.canvas_width
        canvas_height = self.canvas.winfo_height() or self.canvas_height
        
        scale_x = canvas_width / img_width
        scale_y = canvas_height / img_height
        self.scale_factor = min(scale_x, scale_y, 1.0)  # Don't upscale
        
        # Resize image
        new_width = int(img_width * self.scale_factor)
        new_height = int(img_height * self.scale_factor)
        
        display_image = self.current_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Convert to PhotoImage
        self.photo = ImageTk.PhotoImage(display_image)
        
        # Clear canvas and add image
        self.canvas.delete("all")
        self.canvas_image = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        
        # Update scroll region
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
        # Redraw points
        self.draw_points()
    
    def on_canvas_click(self, event):
        """Handle canvas click events"""
        
        if self.current_image is None:
            return
        
        # Get click coordinates relative to image
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Convert to original image coordinates
        original_x = int(canvas_x / self.scale_factor)
        original_y = int(canvas_y / self.scale_factor)
        
        # Add point based on current mode
        if self.point_mode == "foreground":
            self.foreground_points.append((original_x, original_y))
        else:
            self.background_points.append((original_x, original_y))
        
        # Redraw points
        self.draw_points()
        
        # Update counters
        self.update_point_counts()
    
    def draw_points(self):
        """Draw all annotation points on canvas"""
        
        # Remove existing point drawings
        self.canvas.delete("point")
        
        # Draw foreground points (green)
        for x, y in self.foreground_points:
            canvas_x = x * self.scale_factor
            canvas_y = y * self.scale_factor
            self.canvas.create_oval(
                canvas_x - 5, canvas_y - 5, canvas_x + 5, canvas_y + 5,
                fill="green", outline="darkgreen", width=2, tags="point"
            )
        
        # Draw background points (red)
        for x, y in self.background_points:
            canvas_x = x * self.scale_factor
            canvas_y = y * self.scale_factor
            self.canvas.create_oval(
                canvas_x - 5, canvas_y - 5, canvas_x + 5, canvas_y + 5,
                fill="red", outline="darkred", width=2, tags="point"
            )
    
    def change_mode(self):
        """Change point annotation mode"""
        self.point_mode = self.mode_var.get()
    
    def clear_all_points(self):
        """Clear all annotation points"""
        self.foreground_points = []
        self.background_points = []
        self.draw_points()
        self.update_point_counts()
    
    def clear_foreground(self):
        """Clear foreground points"""
        self.foreground_points = []
        self.draw_points()
        self.update_point_counts()
    
    def clear_background(self):
        """Clear background points"""
        self.background_points = []
        self.draw_points()
        self.update_point_counts()
    
    def undo_last_point(self):
        """Remove the last added point"""
        if self.point_mode == "foreground" and self.foreground_points:
            self.foreground_points.pop()
        elif self.point_mode == "background" and self.background_points:
            self.background_points.pop()
        
        self.draw_points()
        self.update_point_counts()
    
    def update_point_counts(self):
        """Update point count labels"""
        self.fg_count_label.config(text=f"Foreground: {len(self.foreground_points)}")
        self.bg_count_label.config(text=f"Background: {len(self.background_points)}")
    
    def save_annotations(self):
        """Save annotations to JSON file (manual save)"""
        
        if self.current_image_path is None:
            messagebox.showwarning("Warning", "No image loaded")
            return
        
        if not self.foreground_points and not self.background_points:
            messagebox.showwarning("Warning", "No points to save")
            return
        
        # Get the structured annotation path
        default_path = self.get_annotation_path(self.current_image_path)
        
        file_path = filedialog.asksaveasfilename(
            title="Save Annotations",
            defaultextension=".json",
            initialdir=str(default_path.parent),
            initialfile=default_path.name,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            self._save_annotations_to_file(file_path)
    
    def auto_save_annotations(self):
        """Automatically save annotations when switching images"""
        
        if not self.current_image_path:
            return
        
        if not self.foreground_points and not self.background_points:
            return  # Nothing to save
        
        # Auto-save with structured path
        file_path = self.get_annotation_path(self.current_image_path)
        
        self._save_annotations_to_file(str(file_path), show_message=False)
    
    def extract_frame_index(self, filename):
        """Extract frame index from filename like 'frame_000000.jpg'"""
        try:
            import re
            match = re.search(r'frame_(\d+)', filename)
            if match:
                return int(match.group(1))
            else:
                return 0
        except:
            return 0
    
    def _save_annotations_to_file(self, file_path, show_message=True):
        """Internal method to save annotations to a specific file"""
        
        try:
            # Get source directory information
            image_path = Path(self.current_image_path)
            source_dir_name = image_path.parent.name
            source_dir_path = str(image_path.parent)
            
            # Extract frame index from filename
            frame_index = self.extract_frame_index(image_path.name)
            
            annotations = {
                "image_path": str(self.current_image_path),
                "image_filename": image_path.name,
                "frame_index": frame_index,
                "source_directory": source_dir_path,
                "source_directory_name": source_dir_name,
                "image_size": self.current_image.size,
                "foreground_points": self.foreground_points,
                "background_points": self.background_points,
                "total_points": len(self.foreground_points) + len(self.background_points),
                "annotation_created": str(Path(file_path).parent),
                "annotation_structure": f"annotations/{source_dir_name}/",
                "video_sequence_info": {
                    "is_video_frame": True,
                    "frame_number": frame_index,
                    "sequence_name": source_dir_name
                }
            }
            
            with open(file_path, 'w') as f:
                json.dump(annotations, f, indent=2)
            
            if show_message:
                messagebox.showinfo("Success", f"Annotations saved to {file_path}")
            else:
                print(f"✓ Auto-saved annotations: {Path(file_path).name} -> {source_dir_name}/ (frame {frame_index})")
                
        except Exception as e:
            if show_message:
                messagebox.showerror("Error", f"Failed to save annotations: {e}")
            else:
                print(f"⚠ Auto-save failed: {e}")
    
    def batch_save_all_annotations(self):
        """Save annotations for all images that have points"""
        
        if not self.image_files:
            messagebox.showwarning("Warning", "No directory loaded")
            return
        
        # Save current image first
        if self.current_image_path and (self.foreground_points or self.background_points):
            self.auto_save_annotations()
        
        saved_count = 0
        
        # Check all images for existing annotations in structured directories
        for image_path in self.image_files:
            annotation_path = self.get_annotation_path(image_path)
            if annotation_path.exists():
                saved_count += 1
        
        source_dir_name = Path(self.image_files[0]).parent.name if self.image_files else "unknown"
        messagebox.showinfo("Batch Save", 
                          f"Annotations exist for {saved_count}/{len(self.image_files)} images\n"
                          f"Saved in: annotations/{source_dir_name}/")
    
    def clear_current_annotations(self):
        """Clear annotations for current image and delete file"""
        
        if not self.current_image_path:
            return
        
        # Clear points
        self.clear_all_points()
        
        # Delete annotation file if it exists
        annotation_path = self.get_annotation_path(self.current_image_path)
        
        if annotation_path.exists():
            try:
                annotation_path.unlink()
                print(f"✓ Deleted annotation file: {annotation_path.name}")
            except Exception as e:
                print(f"⚠ Failed to delete annotation file: {e}")
    
    def on_slider_change(self, value):
        """Handle slider value changes"""
        
        if self.slider_updating or not self.image_files:
            return
        
        new_index = int(float(value))
        if new_index != self.current_image_index:
            self.current_image_index = new_index
            self.load_current_image()
            self.update_navigation_info()
    
    def jump_to_frame_entry(self, event=None):
        """Jump to frame number entered in entry widget"""
        
        if not self.image_files:
            return
        
        try:
            frame_num = int(self.frame_entry.get())
            # Convert from 1-based to 0-based indexing
            new_index = frame_num - 1
            
            if 0 <= new_index < len(self.image_files):
                self.current_image_index = new_index
                self.load_current_image()
                self.update_navigation_info()
            else:
                messagebox.showwarning("Invalid Frame", f"Frame number must be between 1 and {len(self.image_files)}")
                
        except ValueError:
            messagebox.showwarning("Invalid Input", "Please enter a valid frame number")
    
    def jump_to_first(self):
        """Jump to first frame"""
        
        if not self.image_files:
            return
        
        self.current_image_index = 0
        self.load_current_image()
        self.update_navigation_info()
    
    def jump_to_last(self):
        """Jump to last frame"""
        
        if not self.image_files:
            return
        
        self.current_image_index = len(self.image_files) - 1
        self.load_current_image()
        self.update_navigation_info()
    
    def jump_relative(self, offset):
        """Jump relative to current frame"""
        
        if not self.image_files:
            return
        
        new_index = self.current_image_index + offset
        new_index = max(0, min(new_index, len(self.image_files) - 1))
        
        if new_index != self.current_image_index:
            self.current_image_index = new_index
            self.load_current_image()
            self.update_navigation_info()
    
    def on_key_press(self, event):
        """Handle keyboard shortcuts"""
        
        key = event.keysym.lower()
        
        if key == 'f':
            self.mode_var.set("foreground")
            self.change_mode()
        elif key == 'b':
            self.mode_var.set("background")
            self.change_mode()
        elif key == 'c':
            self.clear_all_points()
        elif key == 's':
            self.save_annotations()
        elif key == 'left':
            self.previous_image()
        elif key == 'right' or key == 'space':
            self.next_image()
        elif key == 'delete':
            self.clear_current_annotations()
        elif key == 'home':
            self.jump_to_first()
        elif key == 'end':
            self.jump_to_last()
        elif key == 'page_up':
            self.jump_relative(-10)
        elif key == 'page_down':
            self.jump_relative(10)

def main():
    """Main function"""
    
    root = tk.Tk()
    app = PointAnnotationGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
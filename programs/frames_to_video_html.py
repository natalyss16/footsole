"""
This script provides a different visualisation with an interactive HTML player.This allow us to precisely select and compare individual frames.
This is particularly useful for inspecting and comparing sensor data across different time points.
This script compress the .png frames to a lower quality .jpg frames to sotre in the html folder.
Press 'Export HTML' button to export the HTML file and the compressed frames to the exported_html folder.

Argument:
    python frames_to_video_html.py
    please remember to customize the folder path in line 421

Usage:
    After running "viz_generate_frames.py" and generating all the frames, please use this file to create an animation
    Remember to customize the folder paths in lines 22 and 23
"""

import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button
import matplotlib.image as mpimg
import os
import numpy as np
from PIL import Image

class InteractiveFramePlayer:
    def __init__(self, frames_directory):
        self.frames_directory = frames_directory
        self.frames = []
        self.current_frame = 0
        # 提取文件夹名称用于title和文件名
        self.folder_name = os.path.basename(frames_directory)
        self.load_all_frames()
        
    def load_all_frames(self):
        """preload all PNG frames"""
        frame_files = sorted([f for f in os.listdir(self.frames_directory) if f.endswith('.png')])
        
        print(f"loading {len(frame_files)} frames...")
        for frame_file in frame_files:
            frame_path = os.path.join(self.frames_directory, frame_file)
            frame = mpimg.imread(frame_path)
            self.frames.append(frame)
        print("frames loaded!")
        
    def create_interactive_interface(self):
        """create interactive interface"""
        fig, ax = plt.subplots(figsize=(14, 8))
        self.fig = fig
        self.ax = ax
        
        # show first frame
        self.im = ax.imshow(self.frames[0])
        ax.axis('off')
        ax.set_title(f'Frame 0 / {len(self.frames)-1}')
        
        # create slider
        ax_slider = plt.axes([0.1, 0.02, 0.65, 0.03])
        self.slider = Slider(ax_slider, 'Frame', 0, len(self.frames)-1, 
                            valinit=0, valstep=1)
        
        # create play button
        ax_play = plt.axes([0.8, 0.02, 0.1, 0.03])
        self.play_button = Button(ax_play, 'Play')
        
        # create export HTML button
        ax_export = plt.axes([0.8, 0.06, 0.1, 0.03])
        self.export_button = Button(ax_export, 'Export HTML')
        
        # bind events
        self.slider.on_changed(self.on_slider_change)
        self.play_button.on_clicked(self.toggle_playback)
        self.export_button.on_clicked(self.export_to_html)
        
        # playback state
        self.is_playing = False
        self.play_timer = None
        
        plt.tight_layout()
        return fig
        
    def on_slider_change(self, val):
        """callback when slider changes"""
        frame_number = int(val)
        self.update_frame(frame_number)
        
    def update_frame(self, frame_number):
        """update frame display"""
        if 0 <= frame_number < len(self.frames):
            self.current_frame = frame_number
            self.im.set_array(self.frames[frame_number])
            self.ax.set_title(f'Frame {frame_number} / {len(self.frames)-1}')
            self.fig.canvas.draw_idle()
            
    def toggle_playback(self, event):
        """toggle playback/pause"""
        if self.is_playing:
            self.stop_playback()
        else:
            self.start_playback()
            
    def start_playback(self):
        """start playback"""
        self.is_playing = True
        self.play_button.label.set_text('Pause')
        self.play_next_frame()
        
    def stop_playback(self):
        """stop playback"""
        self.is_playing = False
        self.play_button.label.set_text('Play')
        
    def play_next_frame(self):
        """play next frame"""
        if self.is_playing:
            next_frame = (self.current_frame + 1) % len(self.frames)
            self.slider.set_val(next_frame)
            
            # set timer for next frame
            self.play_timer = self.fig.canvas.new_timer(interval=100)  # 10fps
            self.play_timer.add_callback(self.play_next_frame)
            self.play_timer.start()
    
    def export_to_html(self, event):
        """export to HTML file """
        output_dir = 'exported_html'
        images_dir = os.path.join(output_dir, f'{self.folder_name}')
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(images_dir, exist_ok=True)
        
        # generate HTML file name
        output_path = os.path.join(output_dir, f'interactive_player_{self.folder_name}.html')
        

        
        # smart compression strategy: different quality levels
        frame_files = []
        total_size = 0
        compression_stats = {'high': 0, 'medium': 0, 'low': 0}
        
        print(f"Total images: {len(self.frames)}")
        print(f"Compressing images to: {images_dir}")
        
        for i, frame in enumerate(self.frames):
            # smart choose compression level
            if i % 10 == 0:  # save 1 high quality frame every 10 frames
                quality = 80
                dpi = 100
                format_type = 'jpg'
                compression_stats['high'] += 1
                suffix = 'h'
            elif i % 5 == 0:  # save 1 medium quality frame every 5 frames
                quality = 60
                dpi = 80
                format_type = 'jpg'
                compression_stats['medium'] += 1
                suffix = 'm'
            else:  # use low quality for other frames
                quality = 30
                dpi = 60
                format_type = 'jpg'
                compression_stats['low'] += 1
                suffix = 'l'
            
            # save compressed frame
            frame_filename = f'frame_{i:04d}_{suffix}.{format_type}'
            frame_path = os.path.join(images_dir, frame_filename)
            
            # apply compression - using PIL library to support quality parameter
            if format_type == 'jpg':
                # convert matplotlib image to PIL image
                if frame.dtype != np.uint8:
                    frame_uint8 = (frame * 255).astype(np.uint8)
                else:
                    frame_uint8 = frame
                
                # process RGBA to RGB conversion
                if frame_uint8.shape[-1] == 4:  # RGBA模式
                    # create white background
                    white_background = np.ones_like(frame_uint8) * 255
                    # use transparent channel as alpha mixing
                    alpha = frame_uint8[:, :, 3:4] / 255.0
                    frame_rgb = frame_uint8[:, :, :3] * alpha + white_background[:, :, :3] * (1 - alpha)
                    frame_uint8 = frame_rgb.astype(np.uint8)
                elif frame_uint8.shape[-1] == 3:  # RGB mode
                    pass  # already RGB, no conversion needed
                else:  # grayscale image
                    frame_uint8 = frame_uint8[:, :, 0] if len(frame_uint8.shape) == 3 else frame_uint8
                
                # use PIL to save JPG, support quality parameter
                pil_image = Image.fromarray(frame_uint8)
                pil_image.save(frame_path, 'JPEG', quality=quality, optimize=True)
            else:
                # use matplotlib for other formats
                plt.imsave(frame_path, frame, format=format_type, dpi=dpi)
            
            # get file size
            file_size = os.path.getsize(frame_path)
            total_size += file_size
            
            frame_files.append(frame_filename)
            
            if i % 20 == 0:
                print(f"Compressing image {i+1}/{len(self.frames)}, current frame size: {file_size/1024:.1f}KB, quality: {quality}%")
        
        # generate HTML content (using external image links)
        html_content = self.generate_compressed_html_content(frame_files)
        
        # save HTML file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        html_size = os.path.getsize(output_path)
        
        # calculate compression statistics
        original_size = len(self.frames) * 2.4 * 1024 * 1024  # 假设原始每帧2.4MB
        compression_ratio = original_size / (total_size + html_size)
        
        print(f"\n=== finished ===")
        print(f"HTML_file: {output_path}")
        print(f"images_dir: {images_dir}")

    def generate_compressed_html_content(self, frame_files):
        """generate compressed version of HTML content"""
        html_template = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Foot Pressure Sensor Interactive Player - {self.folder_name}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .frame-display {{
            text-align: center;
            margin-bottom: 20px;
        }}
        .frame-image {{
            max-width: 100%;
            height: auto;
            border: 2px solid #ddd;
            border-radius: 5px;
        }}
        .controls {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 20px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        .slider-container {{
            flex: 1;
            min-width: 300px;
        }}
        .slider {{
            width: 100%;
            height: 6px;
            border-radius: 3px;
            background: #ddd;
            outline: none;
            -webkit-appearance: none;
        }}
        .slider::-webkit-slider-thumb {{
            -webkit-appearance: none;
            appearance: none;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: #4CAF50;
            cursor: pointer;
        }}
        .slider::-moz-range-thumb {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: #4CAF50;
            cursor: pointer;
            border: none;
        }}
        .button {{
            padding: 10px 20px;
            font-size: 16px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.3s;
        }}
        .play-button {{
            background-color: #4CAF50;
            color: white;
        }}
        .play-button:hover {{
            background-color: #45a049;
        }}
        .frame-info {{
            text-align: center;
            font-size: 18px;
            color: #666;
            margin-bottom: 20px;
        }}
        .instructions {{
            background-color: #e8f5e8;
            padding: 15px;
            border-radius: 5px;
            margin-top: 20px;
        }}
        .compression-info {{
            background-color: #fff3cd;
            padding: 15px;
            border-radius: 5px;
            margin-top: 20px;
            border-left: 4px solid #ffc107;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Foot Pressure Sensor Interactive Player - {self.folder_name}</h1>
        <div class="frame-info" id="frameInfo">Frame 0 / {len(frame_files)-1}</div>
        
        <div class="frame-display">
            <img id="frameImage" class="frame-image" src="{self.folder_name}/{frame_files[0]}" alt="Frame 0">
        </div>
        
        <div class="controls">
            <div class="slider-container">
                <input type="range" class="slider" id="frameSlider" min="0" max="{len(frame_files)-1}" value="0" step="1">
            </div>
            <button class="button play-button" id="playButton">Play</button>
        </div>

    </div>

    <script>
        const frameFiles = {frame_files};
        const frameImage = document.getElementById('frameImage');
        const frameSlider = document.getElementById('frameSlider');
        const frameInfo = document.getElementById('frameInfo');
        const playButton = document.getElementById('playButton');
        
        let currentFrame = 0;
        let isPlaying = false;
        let playInterval;
        
        // update frame display
        function updateFrame(frameNumber) {{
            if (frameNumber >= 0 && frameNumber < frameFiles.length) {{
                currentFrame = frameNumber;
                frameImage.src = `{self.folder_name}/${{frameFiles[frameNumber]}}`;
                frameInfo.textContent = `Frame ${{frameNumber}} / ${{frameFiles.length-1}}`;
                frameSlider.value = frameNumber;
            }}
        }}
        
        // slider event
        frameSlider.addEventListener('input', function() {{
            updateFrame(parseInt(this.value));
        }});
        
        // play button event
        playButton.addEventListener('click', function() {{
            if (isPlaying) {{
                stopPlayback();
            }} else {{
                startPlayback();
            }}
        }});
        
        // start playback
        function startPlayback() {{
            isPlaying = true;
            playButton.textContent = 'Pause';
            playInterval = setInterval(() => {{
                let nextFrame = (currentFrame + 1) % frameFiles.length;
                updateFrame(nextFrame);
            }}, 100); // 10fps
        }}
        
        // stop playback
        function stopPlayback() {{
            isPlaying = false;
            playButton.textContent = 'Play';
            clearInterval(playInterval);
        }}
        
        // keyboard shortcuts
        document.addEventListener('keydown', function(e) {{
            switch(e.key) {{
                case ' ':
                    e.preventDefault();
                    if (isPlaying) {{
                        stopPlayback();
                    }} else {{
                        startPlayback();
                    }}
                    break;
                case 'ArrowLeft':
                    e.preventDefault();
                    updateFrame(Math.max(0, currentFrame - 1));
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    updateFrame(Math.min(frameFiles.length - 1, currentFrame + 1));
                    break;
            }}
        }});
    </script>
</body>
</html>
        """
        return html_template

# usage
if __name__ == "__main__":
    import sys
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        # 从命令行参数获取H5文件路径
        h5_file_path = sys.argv[1]
        # 使用与viz_generate_frames.py相同的逻辑生成文件夹名
        h5_filename = os.path.splitext(os.path.basename(h5_file_path))[0]
        frames_dir = f'frames/{h5_filename}'
        
        if os.path.exists(frames_dir):
            print(f"Loading frames from: {frames_dir}")
            player = InteractiveFramePlayer(frames_dir)
            fig = player.create_interactive_interface()
            plt.show()
        else:
            print(f"Frames directory not found: {frames_dir}")
            print("Please run viz_generate_frames.py or viz_sensor_data_no_video.py first")
    else:
        # 如果没有参数，自动检测frames目录下的子文件夹
        frames_base_dir = 'frames'
        if os.path.exists(frames_base_dir):
            # 查找所有包含PNG文件的子文件夹
            subdirs = []
            for item in os.listdir(frames_base_dir):
                item_path = os.path.join(frames_base_dir, item)
                if os.path.isdir(item_path):
                    # 检查是否包含PNG文件
                    png_files = [f for f in os.listdir(item_path) if f.endswith('.png')]
                    if png_files:
                        subdirs.append(item)
            
            if subdirs:
                # 使用最新的文件夹（按修改时间排序）
                subdirs.sort(key=lambda x: os.path.getmtime(os.path.join(frames_base_dir, x)), reverse=True)
                selected_dir = subdirs[0]
                frames_dir = os.path.join(frames_base_dir, selected_dir)
                print(f"Auto-detected frames directory: {frames_dir}")
                player = InteractiveFramePlayer(frames_dir)
                fig = player.create_interactive_interface()
                plt.show()
            else:
                print("No frame directories found in 'frames' folder")
                print("Please run viz_generate_frames.py or viz_sensor_data_no_video.py first")
        else:
            print("'frames' directory not found")
            print("Please run viz_generate_frames.py or viz_sensor_data_no_video.py first")

import mss
from PIL import Image
import os
import datetime

class ScreenshotManager:
    """Utility class to handle screen capturing logic."""
    def __init__(self, output_dir="temp_screenshots"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def capture(self):
        """Captures the primary monitor and saves it to a temp file.
        Returns a dictionary with the image path and default caption.
        """
        with mss.mss() as sct:
            # Capture the primary monitor
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            
            # Convert to PIL Image for processing
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            
            # Generate a unique filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = os.path.join(self.output_dir, f"screenshot_{timestamp}.png")
            
            # Save the image
            img.save(filename)
            
            return {
                'type': 'image',
                'path': filename,
                'caption': ""
            }

    def cleanup_temp_files(self):
        """Removes all files in the temporary screenshot directory."""
        if os.path.exists(self.output_dir):
            for file in os.listdir(self.output_dir):
                file_path = os.path.join(self.output_dir, file)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                except Exception as e:
                    print(f"Error cleaning up {file_path}: {e}")

import os
import zipfile
import shutil
from typing import List

class ZipFileHandler:
    def __init__(self, zip_path: str):
        if not os.path.exists(zip_path):
            raise FileNotFoundError(f"Zip file not found: {zip_path}")
        self.zip_path = zip_path
        self.extracted_dir = self._extract_zip()

    def _extract_zip(self) -> str:
        """Extract the zip file to a temporary directory.

        Returns:
            str: Path to the extracted directory
        """
        timestamp = str(int(os.path.getmtime(self.zip_path)))
        extract_dir = f'extracted_files_{timestamp}'
        
        with zipfile.ZipFile(self.zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        return extract_dir
    
    def get_chat_file(self) -> str:
        """Find and return the path to the chat text file.

        Returns:
            str: Path to the chat file or None if not found
        """
        for file in os.listdir(self.extracted_dir):
            if file.endswith('.txt'):
                return os.path.join(self.extracted_dir, file)
        return None
    
    def get_images(self) -> List[str]:
        """Get all image files from the extracted directory.

        Returns:
            List[str]: List of paths to image files
        """
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        images = []
        
        for file in os.listdir(self.extracted_dir):
            if any(file.lower().endswith(ext) for ext in image_extensions):
                images.append(os.path.join(self.extracted_dir, file))
        return images
    
    def cleanup(self):
        """Remove the extracted directory and its contents."""
        if os.path.exists(self.extracted_dir):
            shutil.rmtree(self.extracted_dir)
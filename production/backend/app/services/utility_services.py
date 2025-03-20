import cv2
import numpy as np
import pyautogui
from PIL import Image
import os
import re
from pathlib import Path
from typing import List, Dict, Union, Optional
from fastapi import UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from ..utils.action_parser import ActionParser

class UtilityService:
    @staticmethod
    async def compare_images(image1: UploadFile, image2: UploadFile):
        # Read images
        img1 = Image.open(image1.file)
        img2 = Image.open(image2.file)
        
        # Convert to numpy arrays
        np_img1 = np.array(img1)
        np_img2 = np.array(img2)
        
        # Convert to grayscale
        gray1 = cv2.cvtColor(np_img1, cv2.COLOR_RGB2GRAY)
        gray2 = cv2.cvtColor(np_img2, cv2.COLOR_RGB2GRAY)
        
        # Calculate similarity using structural similarity index
        score = cv2.matchTemplate(gray1, gray2, cv2.TM_CCOEFF_NORMED)
        
        return {"similarity_score": float(score.max())}

    @staticmethod
    def parse_actions(file_content: str):
        return ActionParser.parse_action_chain(file_content)

    @staticmethod
    def control_window(window_title: str, action: str):
        try:
            # Find the window
            windows = pyautogui.getWindowsWithTitle(window_title)
            if not windows:
                return {"error": f"Window with title containing '{window_title}' not found"}
            
            window = windows[0]
            
            # Perform the requested action
            if action == "minimize":
                window.minimize()
            elif action == "maximize":
                window.maximize()
            elif action == "restore":
                window.restore()
            
            return {"success": True, "action": action}
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def read_file(file_name: str):
        try:
            # Ensure base directory is absolute and exists
            public_path = Path("public").resolve()
            if not public_path.exists() or not public_path.is_dir():
                raise HTTPException(status_code=404, detail="Public directory not found")

            # Sanitize file name and create full path
            safe_name = Path(file_name).name  # Get just the filename part
            file_path = public_path / safe_name

            # Ensure the resolved path is still within base directory
            if not str(file_path.resolve()).startswith(str(public_path)):
                raise HTTPException(status_code=400, detail="Invalid file path")

            # Check if file exists and is a file
            if not file_path.is_file():
                raise HTTPException(status_code=404, detail=f"File '{safe_name}' not found")

            # Read and return file content
            content = file_path.read_text(encoding='utf-8')
            return content

        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    def get_public_files() -> Dict[str, List[str]]:
        try:
            public_path = Path("public").resolve()
            if not public_path.exists() or not public_path.is_dir():
                raise HTTPException(status_code=404, detail="Public directory not found")

            # Get all files from public directory
            files = [f.name for f in public_path.iterdir() if f.is_file() and not f.name.startswith(".")]
            return {"files": files}

        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
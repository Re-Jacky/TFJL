import cv2
import numpy as np
import pyautogui
from PIL import Image
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Union, Optional
from fastapi import UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

class UtilityService:
    @staticmethod
    def get_public_path() -> Path:
        if getattr(sys, 'frozen', False):
            public_path = Path(sys.executable).parent.parent / "public"
        else:
            public_path = Path().resolve().parent / 'public'
        if not public_path.exists() or not public_path.is_dir():
            raise HTTPException(status_code=404, detail="Public directory not found: " + str(public_path))
        return public_path

    @staticmethod
    def read_file(file_name: str, file_type: str) -> Dict[str, str]:
        try:
            public_path = UtilityService.get_public_path()
            # Sanitize file name and create full path
            safe_name = Path(file_name).name  # Get just the filename part
            if file_type == 'collab':
                file_path = public_path / "合作脚本" / safe_name
            elif file_type == 'activity':
                file_path = public_path / "活动脚本" / safe_name

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
    def get_files(file_type: str) -> Dict[str, List[str]]:
        try:
            public_path = UtilityService.get_public_path()
            if file_type == 'collab':
                file_path = public_path / "合作脚本"
            elif file_type == 'activity':
                file_path = public_path / "活动脚本"
            # Get all files from public directory
            files = [f.name for f in file_path.iterdir() if f.is_file() and not f.name.startswith(".")]
            return {"files": files}

        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
            
    @staticmethod
    def parse_actions(content: str) -> Dict[str, Union[List[Dict], List[str]]]:
        """Parse the content of a script file into structured actions."""
        try:
            from app.utils.command_parser import CommandParser
            return CommandParser.parse_script(content)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error parsing actions: {str(e)}")
            
    @staticmethod
    def save_file(file_name: str, content: str, file_type: str) -> Dict[str, str]:
        """Save content to a file in the public directory."""
        try:
            public_path = UtilityService.get_public_path()
            # Sanitize file name and create full path
            safe_name = Path(file_name).name  # Get just the filename part
            if file_type == 'collab':
                file_path = public_path / "合作脚本" / safe_name
            elif file_type == 'activity':
                file_path = public_path / "活动脚本" / safe_name

            # Ensure the resolved path is still within public directory
            if not str(file_path.resolve()).startswith(str(public_path)):
                raise HTTPException(status_code=400, detail="Invalid file path")

            # Write content to file
            file_path.write_text(content, encoding='utf-8')
            return {"status": "success", "message": f"File '{safe_name}' saved successfully"}

        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    def delete_file(file_name: str, file_type: str) -> Dict[str, str]:
        """Delete a file from the public directory."""
        try:
            # Ensure base directory is absolute and exists
            public_path = UtilityService.get_public_path()

            # Sanitize file name and create full path
            safe_name = Path(file_name).name
            file_path = public_path / safe_name

            # Ensure the resolved path is still within public directory
            if not str(file_path.resolve()).startswith(str(public_path)):
                raise HTTPException(status_code=400, detail="Invalid file path")

            # Check if file exists
            if not file_path.is_file():
                raise HTTPException(status_code=404, detail=f"File '{safe_name}' not found")

            # Delete the file
            file_path.unlink()
            return {"status": "success", "message": f"File '{safe_name}' deleted successfully"}

        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
            
    @staticmethod
    def load_card_templates() -> Dict[str, List[np.ndarray]]:
        """Load card templates from the public/卡牌 directory.
        Each card has its own folder containing multiple image variations.
        
        Returns:
            Dict[str, List[np.ndarray]]: A dictionary mapping card names to their template images
        """
        try:
            public_path = UtilityService.get_public_path()
            cards_path = public_path / "卡牌"
            
            if not cards_path.exists() or not cards_path.is_dir():
                raise HTTPException(status_code=404, detail="Cards directory not found")
                
            templates = {}
            # Iterate through card folders
            for card_folder in cards_path.iterdir():
                if card_folder.is_dir():
                    card_name = card_folder.name
                    templates[card_name] = []
                    
                    # Process all image files in the card folder
                    for file_path in card_folder.glob("*"):
                        if file_path.is_file() and file_path.suffix.lower() in [".png", ".jpg", ".jpeg", ".tif"]:
                            try:
                                # Read the image using proper path handling
                                file_path_str = str(file_path.resolve())
                                template = cv2.imdecode(np.fromfile(file_path_str, dtype=np.uint8), cv2.IMREAD_COLOR)
                                if template is not None:
                                    # Convert to grayscale if image is in color
                                    if len(template.shape) == 3:
                                        template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                                    templates[card_name].append(template)
                            except Exception as e:
                                print(f"Error loading template {file_path_str}: {str(e)}")
                                continue
                    
                    # Remove card entry if no valid templates were loaded
                    if not templates[card_name]:
                        del templates[card_name]
                        
            if not templates:
                raise HTTPException(status_code=404, detail="No valid card templates found")
                
            return templates
            
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
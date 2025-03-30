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
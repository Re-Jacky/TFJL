import cv2
import numpy as np
import pyautogui
from PIL import Image
from fastapi import UploadFile, HTTPException
from pathlib import Path

class ImageService:
    @staticmethod
    def click_on_image(window_pid: int, image_file_name: str, confidence: float = 0.8):
        """
        Focus window by PID and click on location matching template image.

        Args:
            window_pid: The PID of the window to control
            image_file_name: The name of the template image file to match
            confidence: Minimum confidence threshold for matching (default: 0.8)

        Returns:
            Dict with click location and success status
        """
        # Focus the window by PID
        print(f"Attempting to focus window with PID: {window_pid}")
        for win in pyautogui.getAllWindows():
            if win._hWnd == window_pid:
                window = win
                print(f"Found window: {window.title}")
                break

        # Load template image from images folder
        print(f"Loading template image: {image_file_name}")
        image_path = Path("images").resolve() / (image_file_name.encode('utf-8').decode('utf-8') + ".jpg")
        if not image_path.exists():
            print(f"Error: Image file {image_path} not found")
            return {"error": f"Image file {image_file_name} not found"}
        template = np.array(Image.open(image_path))
        print(f"Successfully loaded template image: {image_file_name}")
        template_gray = cv2.cvtColor(template, cv2.COLOR_RGB2GRAY)

        # Get screenshot of window
        screenshot = pyautogui.screenshot(region=(
            window.left, window.top, window.width, window.height))
        screenshot_gray = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2GRAY)

        # Match template
        print("Performing template matching...")
        result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        print(f"Template match confidence: {max_val:.2f}")

        if max_val < confidence:
            print(f"Match confidence {max_val:.2f} below threshold {confidence}")
            return {"error": "Template match confidence below threshold"}

        # Calculate click position
        click_x = window.left + max_loc[0] + template.shape[1]//2
        click_y = window.top + max_loc[1] + template.shape[0]//2

        # Perform click
        print(f"Clicking at position: ({click_x}, {click_y})")
        pyautogui._pause = False
        pyautogui.mouseDown(click_x, click_y, _pause=False)
        pyautogui.mouseUp(click_x, click_y, _pause=False)
        print("Click successfully executed without mouse movement")

        return {
            "success": True,
            "click_position": {"x": click_x, "y": click_y},
            "confidence": float(max_val)
        }
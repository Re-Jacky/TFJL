import cv2
import numpy as np
from PIL import Image
from fastapi import HTTPException
from pathlib import Path
from app.services.window_control_services import WindowControlService
from app.services.utility_services import UtilityService
from app.utils.logger import logger

# Check if CUDA is available
USE_CUDA = cv2.cuda.getCudaEnabledDeviceCount() > 0

utility_service = UtilityService()

class ImageService:
    # Private class instance
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ImageService, cls).__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ImageService()
        return cls._instance

    @staticmethod
    def load_template(image_file_name: str) -> np.ndarray:
        """Load and process template image."""
        image_path = UtilityService.get_public_path() / "images"/ (image_file_name.encode('utf-8').decode('utf-8') + ".jpg")
        if not image_path.exists():
            raise HTTPException(status_code=404, detail=f"Image file {image_file_name} not found: {image_path}")
        template = np.array(Image.open(image_path))
        return cv2.cvtColor(template, cv2.COLOR_RGB2GRAY)

    def find_image(self, window_pid: int, image_file_name: str, confidence: float = 0.8):
        """
        Find the given template in the window's screenshot.

        Args:
            window_pid: The PID of the window to control
            image_file_name: The name of the template image file to match
            confidence: Minimum confidence threshold for matching (default: 0.8)

        Returns:
            Dict with found status, position, and confidence
        """
        window = WindowControlService.find_window(window_pid)
        template_gray = self.load_template(image_file_name)
        screenshot_gray = WindowControlService.capture_region(window, None)

        logger.info("Performing template matching...")
        result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        logger.info(f"Template {image_file_name} match confidence: {max_val:.2f}")

        if max_val < confidence:
            logger.warning(f"Match confidence {max_val:.2f} below threshold {confidence}")
            return {"found": False, "confidence": float(max_val)}

        # Calculate position relative to window
        center_x = max_loc[0] + template_gray.shape[1] // 2
        center_y = max_loc[1] + template_gray.shape[0] // 2
        return {
            "found": True,
            "position": {"x": center_x, "y": center_y},
            "confidence": float(max_val)
        }

    def click_on_image(self, window_pid: int, image_file_name: str, confidence: float = 0.8):
        """
        Focus window by PID and click on location matching template image.

        Args:
            window_pid: The PID of the window to control
            image_file_name: The name of the template image file to match
            confidence: Minimum confidence threshold for matching (default: 0.8)

        Returns:
            Dict with click location and success status
        """
        result = self.find_image(window_pid, image_file_name, confidence)
        if not result.get("found"):
            return {"error": "Template match confidence below threshold"}
        click_x = result["position"]["x"]
        click_y = result["position"]["y"]
        WindowControlService.click_at(window_pid, click_x, click_y)
        return {
            "success": True,
            "click_position": {"x": click_x, "y": click_y},
            "confidence": result["confidence"]
        }
import base64
from datetime import datetime
from pathlib import Path
from io import BytesIO
from PIL import Image
from fastapi import HTTPException
from app.services.window_control_services import WindowControlService
from app.services.utility_services import UtilityService
from app.utils.logger import logger
class ScreenshotService:
    @staticmethod
    def capture_screenshot(window_pid: int) -> dict:
        """
        Capture a screenshot of the specified window, save it to disk, and return base64.
        
        Args:
            window_pid: The PID of the target window
            
        Returns:
            dict: {"success": bool, "image": str, "file_path": str, "message": str}
        """
        try:
            # Use existing capture_region method to get the window content
            # This returns a grayscale numpy array (cv2 format)
            grayscale_array = WindowControlService.capture_region(window_pid, None)
            
            # Convert numpy array back to PIL Image
            # Since it's grayscale (single channel), mode is 'L'
            image = Image.fromarray(grayscale_array, mode='L')
            
            # Create screenshot directory if it doesn't exist
            # Path: production/screenshot/ (same level as public/)
            public_path = UtilityService.get_public_path()
            screenshot_dir = public_path.parent / "screenshot"
            screenshot_dir.mkdir(exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}_{window_pid}.png"
            file_path = screenshot_dir / filename
            
            # Save image to disk
            image.save(file_path, format="PNG")
            logger.info(f"Screenshot saved to: {file_path}")
            
            # Also encode to base64 for immediate display
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            return {
                "success": True,
                "image": f"data:image/png;base64,{img_str}",
                "file_path": str(file_path),
                "filename": filename,
                "message": "Screenshot captured and saved successfully"
            }
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Error capturing screenshot: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

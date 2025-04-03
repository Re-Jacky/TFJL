import win32api
import win32con
import win32gui
import pygetwindow
import win32ui
import numpy as np
import pyautogui
from ctypes import windll
from PIL import Image
from typing import Dict, List, Optional, Tuple, Union
import cv2


class WindowControlService:
    @staticmethod
    def click_at(window_pid: int, x: int, y: int):
        """
        Send a click event directly to the specified window coordinates using PostMessage.

        Args:
            window_pid: The PID of the target window
            x: The x coordinate relative to the window
            y: The y coordinate relative to the window
        """
        # Convert screen coordinates to window coordinates
        hwnd = window_pid
        point = win32api.MAKELONG(x, y)

        # Send mouse down and up messages
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, point)
        win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, None, point)

        return {"success": True, "message": f"Click sent to window {hwnd} at ({x}, {y})"}

    @staticmethod
    def scroll_to(window_pid: int, x: int, y: int, delta: int, direction: str = 'vertical'):
        """
        Send a scroll event to the specified window coordinates using PostMessage.

        Args:
            window_pid: The PID of the target window
            x: The x coordinate relative to the window
            y: The y coordinate relative to the window
            delta: The scroll amount (positive for up/right, negative for down/left)
            direction: The scroll direction ('vertical' or 'horizontal')
        """
        hwnd = window_pid
        point = win32api.MAKELONG(x, y)

        # Determine which message to send based on direction
        message = win32con.WM_MOUSEWHEEL if direction == 'vertical' else win32con.WM_MOUSEHWHEEL

        # Send mouse wheel message
        win32gui.PostMessage(hwnd, message, win32api.MAKELONG(0, delta), point)

        return {"success": True, "message": f"{direction.capitalize()} scroll sent to window {hwnd} at ({x}, {y}) with delta {delta}"}
        
    @staticmethod
    def locate_window(pid: int) -> dict:
        """
        Move and resize the specified window to top-left corner of screen.
        Args:
            pid: The PID of window to locate
        Returns:
            dict: Status message
        """
        try:
            for window in pygetwindow.getAllWindows():
                if window._hWnd == pid:
                    # Move to top-left corner (0,0) and resize to 800x600
                    window.moveTo(0, 0)
                    window.resizeTo(1056, 637)
                    return {"status": "success", "message": f"Window {pid} moved and resized"}
            
            return {"status": "error", "message": f"Window with pid {pid} not found"}
        except Exception as e:
            return {"status": "error", "message": f"Error locating window: {str(e)}"}
            
    @staticmethod
    def find_window(window_pid: int):
        """Find window by PID using win32gui."""
        hwnd = window_pid
        if not win32gui.IsWindow(hwnd):
            raise HTTPException(status_code=404, detail=f"Window with PID {window_pid} not found")
        return hwnd

    @staticmethod
    def capture_region(hwnd, region: Optional[Tuple[int, int, int, int]]) -> np.ndarray:
        """
        Capture and process a region of the window using win32gui and ctypes.
        region: Tuple of (x, y, width, height) defining the region to analyze
        """
        try:
            # Get window dimensions
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            
            # Adjust region if specified
            if region:
                x, y, w, h = region
                left += x
                top += y
                width = w
                height = h
            
            # Create device context
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            
            # Create bitmap
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)
            
            # Copy window contents to bitmap
            result = windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)
            
            # Convert to numpy array
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            
            # Clean up
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)
            
            if not result:
                raise Exception("Failed to capture window contents")
                
            screenshot = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1)
                
            screenshot_array = np.array(screenshot)
            return cv2.cvtColor(screenshot_array, cv2.COLOR_RGB2GRAY)
            
        except Exception as e:
            # Fallback to pyautogui if win32 capture fails
            if region:
                abs_x = left + (region[0] if region else 0)
                abs_y = top + (region[1] if region else 0)
                width = region[2] if region else width
                height = region[3] if region else height
                screenshot = pyautogui.screenshot(region=(abs_x, abs_y, width, height))
            else:
                screenshot = pyautogui.screenshot(region=(left, top, width, height))
            
            screenshot_array = np.array(screenshot)
            return cv2.cvtColor(screenshot_array, cv2.COLOR_RGB2GRAY)
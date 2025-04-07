import win32api
import win32con
import win32gui
import pygetwindow
import numpy as np
import pyautogui
from typing import  Optional, Tuple
import cv2
from app.utils.logger import logger
from fastapi import HTTPException

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
    def horizontal_scroll(window_pid: int, distance: int):
        """
        Perform horizontal scrolling by simulating mouse drag from right to left.
        Uses mouse down/move/up to avoid inertia effects.
        
        Args:
            window_pid: The PID of the target window
            distance: Positive distance to scroll (right to left)
        """
        hwnd = window_pid
        start_x = 1000
        y = 300
        chunk_size = 10  # Max distance per iteration to avoid inertia
        
        # Calculate number of iterations needed
        iterations = max(1, distance // chunk_size)
        
        for i in range(iterations):
            # Mouse down at start position
            point = win32api.MAKELONG(start_x, y)
            win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, point)
            
            # Mouse move left by chunk_size
            move_x = start_x - chunk_size
            point = win32api.MAKELONG(move_x, y)
            win32gui.PostMessage(hwnd, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON, point)
     
            # Mouse up at new position
            win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, None, point)
        
            
        return {"success": True, "message": f"Horizontal scroll completed for distance {distance}"}

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
        except Exception as e:
            logger.error(f"Error capturing window region: {str(e)}")
            return np.zeros((0, 0), dtype=np.uint8)

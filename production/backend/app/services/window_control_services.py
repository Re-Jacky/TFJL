import win32api
import win32con
import win32gui
import pygetwindow
import numpy as np
import pyautogui
import cv2
from app.utils.logger import logger
from fastapi import HTTPException
import win32ui
from ctypes import windll
from PIL import Image
from typing import Optional, Tuple
import time

class WindowControlService:
    def __init__(self):
        self.locked_windows = set()

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
    def bring_window_to_foreground(window_pid: int):
        hwnd = window_pid  # window_pid is the window handle (hwnd)
        # Validate window exists
        if not win32gui.IsWindow(hwnd):
            raise HTTPException(status_code=404, detail=f"Window with handle {hwnd} not found")
    
        # Restore window if minimized
        if win32gui.IsIconic(hwnd):  # Check if window is minimized (iconic)
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)  # Restore minimized window

        # Bring window to foreground
        try:
            win32gui.SendMessage(hwnd, win32con.WM_SYSCOMMAND, win32con.SC_RESTORE, 0)
            win32gui.SetForegroundWindow(hwnd)
        except Exception as e:
            return False
        time.sleep(0.1)  # Short delay to ensure window is active
        return {"success": True, "message": f"Window {hwnd} brought to foreground"}

    ## use pyautogui to click in window, it works for any window but can't work for overlapped windows
    @staticmethod
    def click_at_native(window_pid: int, x: int, y: int):
        # bring the window to the foreground
        WindowControlService.bring_window_to_foreground(window_pid)
         # Get window's screen coordinates
        left, top, _, _ = win32gui.GetWindowRect(window_pid)
        screen_x = left + x  # Convert window-relative x to screen x
        screen_y = top + y   # Convert window-relative y to screen y
        pyautogui.click(screen_x, screen_y)
        return {"success": True, "message": f"PyAutoGUI click at ({x}, {y}) in window {window_pid}"}
        
    @staticmethod
    def locate_game_window(pid: int, x, y) -> dict:
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
                    window.moveTo(x, y)
                    window.resizeTo(1056, 637)
                    return {"status": "success", "message": f"Window {pid} moved and resized"}
            
            return {"status": "error", "message": f"Window with pid {pid} not found"}
        except Exception as e:
            return {"status": "error", "message": f"Error locating window: {str(e)}"}
    
    @staticmethod
    def locate_tool_window(pid: int, x: int, y: int):
        try:
            for window in pygetwindow.getAllWindows():
                if window._hWnd == pid:
                    # Move to top-left corner (0,0) and resize to 800x600
                    window.moveTo(x, y)
                    window.resizeTo(821, 705)
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

    def lock_window(self, window_pid: int, lock: bool):
        """
        Lock/unlock the specified window.
        """
        if lock:
            if window_pid in self.locked_windows:
                raise HTTPException(status_code=400, detail=f"Window with PID {window_pid} is already locked")
            else:
                self.locked_windows.add(window_pid)
                return {"status": "success", "message": f"Window {window_pid} locked"}
        elif window_pid in self.locked_windows:
           self.locked_windows.remove(window_pid)
           return {"status": "success", "message": f"Window {window_pid} unlocked"}
        else:
            raise HTTPException(status_code=400, detail=f"Window with PID {window_pid} is not locked")

    @staticmethod
    def capture_region(hwnd, region: Optional[Tuple[int, int, int, int]]) -> np.ndarray:
        """
        Capture and process a region of the window using win32gui and ctypes.
        region: Tuple of (x, y, width, height) defining the region to analyze
        """
        try:
            # Get window dimensions
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            window_width = right - left
            window_height = bottom - top
            
            if region:
                x, y, width, height = region
            else:
                x, y = 0, 0
                width, height = window_width, window_height

            # Create device context
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            
            # Create bitmap
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, window_width, window_height)
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
            cropped_screenshot = screenshot.crop((x, y, x + width, y + height))
            screenshot_array = np.array(cropped_screenshot)
            return cv2.cvtColor(screenshot_array, cv2.COLOR_RGB2GRAY)
            
        except Exception as e:
            # Fallback to pyautogui if win32 capture fails
            logger.error(f"Error capturing window region: {str(e)}")
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

    @staticmethod
    def type_text(hwnd: int, text: str, delay: float = 0.1) -> dict:
        """
        Simulate typing text into a target window using WM_CHAR messages.
        
        Args:
            hwnd: Window handle of the target window
            text: Text string to type into the window
            delay: Delay in seconds between characters (default: 0.01s)
            
        Returns:
            dict: Success status and message
        """
        if not win32gui.IsWindow(hwnd):
            raise HTTPException(status_code=404, detail=f"Window with handle {hwnd} not found")
        
        try:
            for char in text:
                # Send WM_CHAR message with character's Unicode value
                win32gui.SendMessage(hwnd, win32con.WM_CHAR, ord(char), 0)
                time.sleep(delay)  # Add small delay between characters
                
            return {"success": True, "message": f"Typed '{text}' into window {hwnd}"}
        except Exception as e:
            return {"status": "error", "message": f"Error typing text: {str(e)}"}
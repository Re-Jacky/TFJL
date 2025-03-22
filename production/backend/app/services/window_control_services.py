import win32api
import win32con
import win32gui

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
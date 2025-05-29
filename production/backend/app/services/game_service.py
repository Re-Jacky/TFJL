from app.services.window_control_services import WindowControlService
from app.services.image_services import ImageService
from app.enums.game_positions import GamePositions
from app.enums.tool_positions import ToolPositions
from app.utils.logger import logger
import time
import cv2

image_service = ImageService()

class GameService:
    @staticmethod
    def click_in_window(pid, position):
        WindowControlService.click_at(pid, position[0], position[1])
        time.sleep(0.5)  # 等待点击动作完成 (可以根据实际情况调整时间)
        return True  # 假设点击成功返回True (根据实际情况修改返回值)
    
    @staticmethod
    def type_room_number(pid, room_number):
        GameService.click_in_window(pid, GamePositions.TEXT_AREA.value)
        WindowControlService.type_text(pid, room_number)
        GameService.click_in_window(pid, GamePositions.TEXT_AREA_CONFIRM.value)
        return True  # 假设输入成功返回True (根据实际情况修改返回值)
    
    @staticmethod
    def recognize_room_number(pid):
        import pytesseract
        import re
        
        # Define room number region (x, y, width, height)
        room_number_region = (490, 345, 80, 30)  # Adjust coordinates if needed
        
        # Capture grayscale screenshot of the region
        screenshot_gray = WindowControlService.capture_region(pid, room_number_region)
        
        # Preprocess image for better OCR results (thresholding)
        _, thresholded = cv2.threshold(screenshot_gray, 127, 255, cv2.THRESH_BINARY)
        
        # Use Tesseract to extract text (configure for digits only)
        custom_config = r'--oem 3 --psm 10 -c tessedit_char_whitelist=0123456789'
        ocr_text = pytesseract.image_to_string(thresholded, config=custom_config)
        
        # Extract 4-digit number using regex
        match = re.search(r'\b\d{4}\b', ocr_text)
        if match:
            return match.group()
        else:
            logger.error("Failed to recognize 4-digit room number")
            return None
        

    @staticmethod
    def is_home(pid):
        battle_region = (790, 515, 230, 100)  # 对战区域
        window = WindowControlService.find_window(pid)
        screenshot_gray = WindowControlService.capture_region(window, battle_region)
        template_gray = image_service.load_template('对战')
        result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        return max_val > 0.95

    @staticmethod
    def need_ads(pid):
        ads_region = (413, 394, 230, 85)  # 广告区域，用于检测广告是否出现
        window = WindowControlService.find_window(pid)
        screenshot_gray = WindowControlService.capture_region(window, ads_region)
        template_gray = image_service.load_template('广告')
        result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        return max_val > 0.9
        
    @staticmethod
    def back_to_home(pid):
        if GameService.is_home(pid):
            return True
        else:
            GameService.click_in_window(pid, GamePositions.BACK.value)
            return GameService.is_home(pid)
    
    @staticmethod
    def start_battle(pid):
        GameService.back_to_home(pid)
        GameService.click_in_window(pid, GamePositions.BATTLE.value)
        GameService.click_in_window(pid, GamePositions.QUICK_MATCH.value)
        return True

    @staticmethod
    def start_collab(main, sub):
        mainWndPid = main['game']
        subWndPid = sub['game']
        GameService.back_to_home(mainWndPid)
        GameService.back_to_home(subWndPid)

        # main game window starts
        GameService.click_in_window(mainWndPid, GamePositions.COLLAB.value)

        # detect ads
        watch_ads = GameService.need_ads(mainWndPid)
        print(f"watch_ads: {watch_ads}")
        if watch_ads:
            GameService.click_in_window(mainWndPid, GamePositions.ADS_REGION.value)
            time.sleep(2)

        # start room
        GameService.click_in_window(mainWndPid, GamePositions.PLAY_WITH_FRIEND.value)
        GameService.click_in_window(mainWndPid, GamePositions.START_ROOM.value)
        ## capture room number in pic
        room = GameService.recognize_room_number(mainWndPid)
        timeout = 3
        while room is None:
            time.sleep(1)
            timeout -= 1
            if timeout == 0:
                logger.error("Failed to recognize room number")
                return False
            room = GameService.recognize_room_number(mainWndPid)
        logger.info(f"Room number: {room}")

        # sub game window starts
        GameService.click_in_window(subWndPid, GamePositions.COLLAB.value)
        GameService.click_in_window(subWndPid, GamePositions.PLAY_WITH_FRIEND.value)
        GameService.click_in_window(subWndPid, GamePositions.JOIN_ROOM.value)
        time.sleep(0.5)  # 等待输入框出现
        GameService.type_room_number(subWndPid, room)
        GameService.click_in_window(subWndPid, GamePositions.ROOM_INPUT_CONFIRM.value)
        time.sleep(1)  # 等待进入房间
        GameService.stop_tool(main['tool'], sub['tool'])
        GameService.start_tool(main['tool'], sub['tool'])
        return True
    
    @staticmethod
    def start_ice_castle():
        return True

    @staticmethod
    def start_moon_island():
        return True

    @staticmethod
    def start_tool(main: str, sub: str):
        x, y = ToolPositions.GAME_START.value
        WindowControlService.click_at_native(main, x, y)
        time.sleep(1)
        WindowControlService.click_at_native(sub, x, y)
        return True
    
    @staticmethod
    def stop_tool(main: str, sub: str):
        x, y = ToolPositions.GAME_STOP.value
        WindowControlService.click_at_native(main, x, y)
        time.sleep(1)
        WindowControlService.click_at_native(sub, x, y)
        time.sleep(2)
        return True
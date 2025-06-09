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
    def ice_need_buy_round(pid):
        round_region = (320, 440, 155, 50)  # 回合区域，用于检测回合是否结束
        window = WindowControlService.find_window(pid)
        screenshot_gray = WindowControlService.capture_region(window, round_region)
        template_gray = image_service.load_template('寒冰助战')
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
    def start_auto_battle(main, sub):
        mainWndPid = main['game']
        subWndPid = sub['game']
        GameService.back_to_home(mainWndPid)
        GameService.back_to_home(subWndPid)

        ## switch tool window to main page
        GameService.switch_tool_page(main['tool'], sub['tool'], ToolPositions.MAIN_PAGE.value)

        x, y = ToolPositions.EXECUTE_BUTTON.value
        WindowControlService.click_at_native(main['tool'], x, y)
        time.sleep(1)
        WindowControlService.click_at_native(sub['tool'], x, y)
        return True

    @staticmethod
    def start_collab(main, sub):
        try:
            mainWndPid = main['game']
            subWndPid = sub['game']
            retry = 3
            while retry > 0 and (not GameService.is_home(mainWndPid) or not GameService.is_home(subWndPid)):
                retry -= 1
                time.sleep(5)
                logger.error(f"Detect home page, retry: {3-retry}...")
            if (not GameService.is_home(mainWndPid) or not GameService.is_home(subWndPid)):
                logger.error("Failed to start collab due to maximum retry waiting for the home page")
                return False
            GameService.back_to_home(mainWndPid)
            GameService.back_to_home(subWndPid)

            # main game window starts
            GameService.click_collab(mainWndPid)

            # start room
            GameService.start_room(mainWndPid)
            ## capture room number in pic
            room = GameService.recognize_room_number_with_retry(mainWndPid)

            # sub game window starts
            GameService.click_collab(subWndPid)
            GameService.join_room(subWndPid, room)
            GameService.switch_tool_page(main['tool'], sub['tool'], ToolPositions.COLLAB_PAGE.value)
            GameService.stop_tool(main['tool'], sub['tool'])
            GameService.start_tool(main['tool'], sub['tool'])
            return True
        except Exception as e:
            logger.error(f"[GameService] start collab error: {e}")
            return False
    
    @staticmethod
    def is_in_ice_castle(pid):
        region = (461, 72, 133, 61)  # 寒冰标题区域
        window = WindowControlService.find_window(pid)
        screenshot_gray = WindowControlService.capture_region(window, region)
        template_gray = image_service.load_template('寒冰堡')
        result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        logger.info(f"[GameService] is in ice castle confidence: {max_val}")
        return max_val > 0.95
    
    @staticmethod
    def start_ice_castle(main, sub, only_support):
        try:
            mainWndPid = main['game']
            subWndPid = sub['game']
            retry = 3
            while retry > 0 and (not GameService.is_in_ice_castle(mainWndPid) or not GameService.is_in_ice_castle(subWndPid)):
                retry -= 1
                time.sleep(8)
                logger.error(f"Detect ice castle page, retry: {3-retry}...")
            if (not GameService.is_in_ice_castle(mainWndPid) or not GameService.is_in_ice_castle(subWndPid)):
                logger.error("Failed to start ice castle due to maximum retry waiting for the ice castle page")
                return False
            # close support first
            GameService.click_in_window(mainWndPid, GamePositions.CLOSE_SUPPORT.value)
            time.sleep(1)
            # main game window starts
            GameService.click_ice_castle(mainWndPid, False)
            # start room
            GameService.start_room(mainWndPid)
            ## capture room number in pic
            room = GameService.recognize_room_number_with_retry(mainWndPid)

            # sub game window starts
            GameService.click_in_window(subWndPid, GamePositions.CLOSE_SUPPORT.value)
            time.sleep(1)
            GameService.click_ice_castle(subWndPid, only_support)
            GameService.join_room(subWndPid, room)
            GameService.switch_tool_page(main['tool'], sub['tool'], ToolPositions.COLLAB_PAGE.value)
            GameService.stop_tool(main['tool'], sub['tool'])
            GameService.start_tool(main['tool'], sub['tool'])
            return True
        except Exception as e:
            logger.error(f"[GameService] start ice castle error: {e}")
            return False

    @staticmethod
    def is_in_moon_island(pid):
        region = (475, 71, 124, 54)  # 暗月标题区域
        window = WindowControlService.find_window(pid)
        screenshot_gray = WindowControlService.capture_region(window, region)
        template_gray = image_service.load_template('暗月岛')
        result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(result)
        logger.info(f"[GameService] is in moon island confidence: {max_val}")
        return max_val > 0.95

    @staticmethod
    def start_moon_island(main, sub):
        try:
            mainWndPid = main['game']
            subWndPid = sub['game']
            retry = 3
            while retry > 0 and (not GameService.is_in_moon_island(mainWndPid) or not GameService.is_in_moon_island(subWndPid)):
                retry -= 1
                time.sleep(8)
                logger.error(f"Detect moon island page, retry: {3-retry}...")
            if (not GameService.is_in_moon_island(mainWndPid) or not GameService.is_in_moon_island(subWndPid)):
                logger.error("Failed to start moon island due to maximum retry waiting for the moon island page")
                return False
            # close support first
            GameService.click_in_window(mainWndPid, GamePositions.CLOSE_SUPPORT.value)
            time.sleep(1)
            # main game window starts
            GameService.click_moon_island(mainWndPid)
            # start room
            GameService.start_room(mainWndPid)
            ## capture room number in pic
            room = GameService.recognize_room_number_with_retry(mainWndPid)

            # close support first
            GameService.click_in_window(subWndPid, GamePositions.CLOSE_SUPPORT.value)
            time.sleep(1)
            # sub game window starts
            GameService.click_moon_island(subWndPid)
            GameService.join_room(subWndPid, room)
            GameService.switch_tool_page(main['tool'], sub['tool'], ToolPositions.COLLAB_PAGE.value)
            GameService.stop_tool(main['tool'], sub['tool'])
            GameService.start_tool(main['tool'], sub['tool'])
            return True
        except Exception as e:
            logger.error(f"[GameService] start moon island error: {e}")
            return False

    @staticmethod
    def start_tool(main: str, sub: str):
        x, y = ToolPositions.GAME_START.value
        WindowControlService.click_at_native(main, x, y)
        time.sleep(1)
        WindowControlService.click_at_native(sub, x, y)
        return True
    
    @staticmethod
    def switch_tool_page(main: str, sub: str, position):
        x, y = position
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

    @staticmethod
    def click_collab(pid):
        GameService.click_in_window(pid, GamePositions.COLLAB.value)
        # detect ads
        watch_ads = GameService.need_ads(pid)
        if watch_ads:
            GameService.click_in_window(pid, GamePositions.ADS_REGION.value)
            time.sleep(1)
            GameService.click_in_window(pid, GamePositions.COLLAB.value)
        return True
    
    @staticmethod
    def click_ice_castle(pid, only_support):
        GameService.click_in_window(pid, GamePositions.ICE_CASTLE.value)
        # detect buy rounds
        need_buy_round = GameService.ice_need_buy_round(pid)
        if need_buy_round:
            if only_support:
                GameService.click_in_window(pid, GamePositions.ICE_SUPPORT.value)
            else:
                GameService.click_in_window(pid, GamePositions.ICE_BUY_ROUND.value)
            time.sleep(1)
            GameService.click_in_window(pid, GamePositions.ICE_CASTLE.value)
        return True
    
    @staticmethod
    def click_moon_island(pid):
        GameService.click_in_window(pid, GamePositions.MOON_ISLAND.value)
        return True
    
    @staticmethod
    def recognize_room_number_with_retry(pid):
        ## capture room number in pic
        room = GameService.recognize_room_number(pid)
        timeout = 3
        while room is None:
            time.sleep(1)
            timeout -= 1
            if timeout == 0:
                logger.error("Failed to recognize room number")
                raise Exception("Failed to recognize room number")
            room = GameService.recognize_room_number(pid)
        logger.info(f"Room number: {room}")
        return room
    
    @staticmethod
    def start_room(pid):
         # start room
        GameService.click_in_window(pid, GamePositions.PLAY_WITH_FRIEND.value)
        GameService.click_in_window(pid, GamePositions.START_ROOM.value)

    @staticmethod
    def join_room(pid, room):
        GameService.click_in_window(pid, GamePositions.PLAY_WITH_FRIEND.value)
        GameService.click_in_window(pid, GamePositions.JOIN_ROOM.value)
        time.sleep(0.5)  # 等待输入框出现
        GameService.type_room_number(pid, room)
        GameService.click_in_window(pid, GamePositions.ROOM_INPUT_CONFIRM.value)
        time.sleep(1)  # 等待进入房间
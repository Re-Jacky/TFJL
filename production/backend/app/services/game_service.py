from app.services.window_control_services import WindowControlService
from app.services.image_services import ImageService
from app.enums.game_positions import GamePositions
import time
import cv2

image_service = ImageService()

class GameService:
    @staticmethod
    def click_in_game(pid, position):
        WindowControlService.click_at(pid, position[0], position[1])
        time.sleep(0.5)  # 等待点击动作完成 (可以根据实际情况调整时间)
        return True  # 假设点击成功返回True (根据实际情况修改返回值)

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
    def back_to_home(pid):
        if GameService.is_home(pid):
            return True
        else:
            GameService.click_in_game(pid, GamePositions.BACK.value)
            return GameService.is_home(pid)
    
    @staticmethod
    def start_battle(pid):
        GameService.back_to_home(pid)
        GameService.click_in_game(pid, GamePositions.BATTLE.value)
        GameService.click_in_game(pid, GamePositions.BATTLE_START.value)
        return True

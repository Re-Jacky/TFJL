import cv2
import numpy as np
from PIL import Image
from fastapi import HTTPException
from pathlib import Path
import time
import os
from typing import Dict, List, Optional, Tuple, Union
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from app.services.window_control_services import WindowControlService
from app.services.utility_services import UtilityService
from app.utils.logger import logger

# Check if CUDA is available
USE_CUDA = cv2.cuda.getCudaEnabledDeviceCount() > 0

utility_service = UtilityService()

class ImageService:
    # Private class instance
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ImageService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._card_templates: Dict[str, List[np.ndarray]] = {}
            self._gpu_templates: Dict[str, List[cv2.cuda_GpuMat]] = {} if USE_CUDA else None
            cpu_count = os.cpu_count() or 1
            self._max_workers = max(1, int(cpu_count * 0.75))  # Default to 75% of CPU cores
            self._initialized = True
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ImageService()
        return cls._instance
    
    def set_max_workers(self, max_workers: int) -> None:
        """Set the maximum number of worker processes for parallel processing.
        
        Args:
            max_workers: The maximum number of worker processes to use
        """
        self._max_workers = max(1, min(max_workers, os.cpu_count() or 1))
    
    def initialize_card_templates(self) -> None:
        """Initialize the card templates from the public directory and pre-process them for optimization."""
        raw_templates = utility_service.load_card_templates()
        self._card_templates = {}
        if USE_CUDA:
            self._gpu_templates = {}
        
        for card_name, templates in raw_templates.items():
            self._card_templates[card_name] = []
            if USE_CUDA:
                self._gpu_templates[card_name] = []
            
            for template in templates:
                # Create image pyramid for multi-scale matching
                pyramid = np.array([template])
                current_image = template
                
                # Calculate optimal pyramid levels based on template size
                min_dimension = min(template.shape[0], template.shape[1])
                max_levels = max(1, int(np.log2(min_dimension / 32)))  # Stop when smallest dimension is ~32px
                
                for _ in range(max_levels - 1):
                    current_image = cv2.pyrDown(current_image)
                    pyramid = np.append(pyramid, [current_image], axis=0)
                
                self._card_templates[card_name].append(pyramid)
                
                # Pre-upload templates to GPU if CUDA is available
                if USE_CUDA:
                    gpu_pyramid = []
                    for img in pyramid:
                        gpu_mat = cv2.cuda_GpuMat()
                        gpu_mat.upload(img)
                        gpu_pyramid.append(gpu_mat)
                    self._gpu_templates[card_name].append(gpu_pyramid)
    


    def _match_template(self, template_data, screenshot_gray, confidence):
        """Worker function for parallel template matching using image pyramids with GPU acceleration when available."""
        card_name, template_pyramid = template_data
        matches = []
        
        # Start with smallest template (highest pyramid level)
        for level, template in enumerate(reversed(template_pyramid)):
            scale = 2 ** (len(template_pyramid) - level - 1)
            scaled_screenshot = cv2.pyrDown(screenshot_gray) if level < len(template_pyramid) - 1 else screenshot_gray
            
            if template.shape[0] > scaled_screenshot.shape[0] or \
               template.shape[1] > scaled_screenshot.shape[1]:
                continue
                
            # Use lower confidence threshold for initial pyramid levels
            level_confidence = confidence * 0.8 if level < len(template_pyramid) - 1 else confidence
            
            if USE_CUDA:
                # Use pre-uploaded GPU template and upload screenshot once
                gpu_screenshot = cv2.cuda_GpuMat()
                gpu_screenshot.upload(scaled_screenshot)
                
                # Get pre-uploaded GPU template
                gpu_template = self._gpu_templates[card_name][0][level]
                
                # Perform template matching on GPU
                gpu_result = cv2.cuda.matchTemplate(gpu_screenshot, gpu_template, cv2.TM_CCOEFF_NORMED)
                result = gpu_result.download()
                
                # Clean up GPU memory
                gpu_screenshot.release()
            else:
                result = cv2.matchTemplate(scaled_screenshot, template, cv2.TM_CCOEFF_NORMED)
            
            # Early stopping if we find high-confidence matches
            locations = np.where(result >= level_confidence)
            if len(locations[0]) > 0:
                for pt in zip(*locations[::-1]):
                    # Scale back the coordinates
                    orig_x = pt[0] * scale
                    orig_y = pt[1] * scale
                    center_x = orig_x + (template.shape[1] * scale) // 2
                    center_y = orig_y + (template.shape[0] * scale) // 2
                    
                    # Verify match at original scale if not at final level
                    if level < len(template_pyramid) - 1:
                        roi = screenshot_gray[max(0, orig_y-5):min(screenshot_gray.shape[0], orig_y + template_pyramid[0].shape[0] + 5),
                                             max(0, orig_x-5):min(screenshot_gray.shape[1], orig_x + template_pyramid[0].shape[1] + 5)]
                        if roi.size > 0:
                            if USE_CUDA:
                                gpu_roi = cv2.cuda_GpuMat()
                                gpu_template_orig = cv2.cuda_GpuMat()
                                gpu_roi.upload(roi)
                                gpu_template_orig.upload(template_pyramid[0])
                                gpu_fine_result = cv2.cuda.matchTemplate(gpu_roi, gpu_template_orig, cv2.TM_CCOEFF_NORMED)
                                fine_result = gpu_fine_result.download()
                            else:
                                fine_result = cv2.matchTemplate(roi, template_pyramid[0], cv2.TM_CCOEFF_NORMED)
                                
                            if fine_result.max() >= confidence:
                                matches.append({
                                    'card_name': card_name,
                                    'confidence': float(fine_result.max()),
                                    'position': int(orig_x),
                                    'center': {'x': int(center_x), 'y': int(center_y)}
                                })
                    else:
                        matches.append({
                            'card_name': card_name,
                            'confidence': float(result[pt[1]][pt[0]]),
                            'position': int(orig_x),
                            'center': {'x': int(center_x), 'y': int(center_y)}
                        })
                
                # Early stopping if we found good matches
                if matches and level == len(template_pyramid) - 1:
                    break
                    
        return matches

    def analyze_cards(self, window_pid: int, region: Tuple[int, int, int, int]= (380, 500, 300, 120), confidence: float = 0.5) -> List[Dict[str, Union[str, Dict[str, int]]]]:
        """Analyze a specific region of the game window to identify cards using parallel template matching.

        Args:
            window_pid: The PID of the window to analyze
            region: Tuple of (x, y, width, height) defining the region to analyze
            confidence: Minimum confidence threshold for matching (default: 0.9)

        Returns:
            List of dictionaries containing card names and their center coordinates
            Each dictionary has format: {'card_name': str, 'center': {'x': int, 'y': int}}
        """
        """
        Analyze a specific region of the game window to identify cards using templates.

        Args:
            window_pid: The PID of the window to analyze
            region: Tuple of (x, y, width, height) defining the region to analyze
            confidence: Minimum confidence threshold for matching (default: 0.9)

        Returns:
            List of dictionaries containing card names and their center coordinates
            Each dictionary has format: {'card_name': str, 'center': {'x': int, 'y': int}}
        """
        import time
        start_time = time.time()
        logger.info(f"[Card Analysis] Starting analysis for window PID: {window_pid}, region: {region}")
        
        if not region:
            region = (380, 500, 300, 120)
            logger.info(f"[Card Analysis] Using default region: {region}")
            
        try:
            logger.info("[Card Analysis] Locating window...")
            window = WindowControlService.find_window(window_pid)
            logger.info("[Card Analysis] Capturing region...")
            screenshot_gray = WindowControlService.capture_region(window, region)

            # Prepare template data for parallel processing
            template_data = []
            logger.info(f"[Card Analysis] Preparing {len(self._card_templates)} card templates...")
            for card_name, templates in self._card_templates.items():
                for template in templates:
                    template_data.append((card_name, template))
            logger.info(f"[Card Analysis] Prepared {len(template_data)} template variations for matching")

            # Use ProcessPoolExecutor for parallel template matching
            matches = []
            logger.info(f"[Card Analysis] Starting parallel matching with {self._max_workers} workers...")
            with ProcessPoolExecutor(max_workers=self._max_workers) as executor:
                match_func = partial(ImageService._match_template, self, screenshot_gray=screenshot_gray, confidence=confidence)
                results = executor.map(match_func, template_data)
                
                # Aggregate results from all processes
                for result in results:
                    matches.extend(result)
            
            logger.info(f"[Card Analysis] Found {len(matches)} potential matches before filtering")
            
            # Sort matches by x-coordinate to maintain left-to-right order
            matches.sort(key=lambda x: x['position'])

            # Remove duplicates (keep highest confidence match for each position)
            filtered_matches = []
            used_positions = set()

            for match in matches:
                # Check if this match is too close to any existing match
                is_duplicate = False
                for pos in used_positions:
                    if abs(match['position'] - pos) < 20:  # Adjust threshold as needed
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    filtered_matches.append(match)
                    used_positions.add(match['position'])
            
            elapsed_time = time.time() - start_time
            logger.info(f"[Card Analysis] Found {len(filtered_matches)} unique matches after filtering")
            logger.info(f"[Card Analysis] Analysis completed in {elapsed_time:.2f} seconds")
            
            # Return card names and their center coordinates in order
            return [{'card_name': match['card_name'], 'center': match['center']} for match in filtered_matches]
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"[Card Analysis] Error during analysis: {str(e)}")
            logger.error(f"[Card Analysis] Analysis failed after {elapsed_time:.2f} seconds")
            raise

    @staticmethod
    def load_template(image_file_name: str) -> np.ndarray:
        """Load and process template image."""
        image_path = Path("images").resolve() / (image_file_name.encode('utf-8').decode('utf-8') + ".jpg")
        if not image_path.exists():
            raise HTTPException(status_code=404, detail=f"Image file {image_file_name} not found")
        template = np.array(Image.open(image_path))
        return cv2.cvtColor(template, cv2.COLOR_RGB2GRAY)

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
        window = WindowControlService.find_window(window_pid)
        template_gray = self.load_template(image_file_name)
        screenshot_gray = WindowControlService.capture_region(window, None)

        # Match template
        logger.info("Performing template matching...")
        result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        logger.info(f"Template match confidence: {max_val:.2f}")

        if max_val < confidence:
            logger.warning(f"Match confidence {max_val:.2f} below threshold {confidence}")
            return {"error": "Template match confidence below threshold"}

        # Calculate click position relative to window
        click_x = max_loc[0] + template_gray.shape[1]//2
        click_y = max_loc[1] + template_gray.shape[0]//2

        # Perform click
        WindowControlService.click_at(window_pid, click_x, click_y)

        return {
            "success": True,
            "click_position": {"x": click_x, "y": click_y},
            "confidence": float(max_val)
        }

    def monitor_cards(self, window_pid: int, region: Tuple[int, int, int, int], 
                     frequency: float = 0.1, confidence: float = 0.9,
                     timeout: float = 5.0, min_matches: int = 1) -> List[Dict[str, Union[str, Dict[str, int]]]]:
        """Continuously monitor a window region for cards until confident matches are found or timeout is reached.

        Args:
            window_pid: The PID of the window to analyze
            region: Tuple of (x, y, width, height) defining the region to analyze
            frequency: How often to analyze the region in seconds (default: 0.1)
            confidence: Minimum confidence threshold for matching (default: 0.9)
            timeout: Maximum time to monitor in seconds (default: 5.0)
            min_matches: Minimum number of cards to find before returning (default: 1)

        Returns:
            List of dictionaries containing card names and their center coordinates
            Each dictionary has format: {'card_name': str, 'center': {'x': int, 'y': int}}

        Raises:
            HTTPException: If window not found or timeout reached without matches
        """
        start_time = time.time()
        best_matches = []
        best_confidence = 0.0

        while (time.time() - start_time) < timeout:
            try:
                matches = self.analyze_cards(window_pid, region, confidence)
                
                # If we found enough matches with good confidence, return immediately
                if len(matches) >= min_matches:
                    # Calculate average confidence only from matches that have confidence values
                    confidences = [float(match.get('confidence', 0.0)) for match in matches if match.get('confidence') is not None]
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
                    if avg_confidence > best_confidence:
                        best_matches = matches
                        best_confidence = avg_confidence
                        if avg_confidence >= confidence:
                            return matches
                
                # Wait before next analysis
                time.sleep(frequency)
                
            except Exception as e:
                logger.error(f"Error during card monitoring: {str(e)}")
                time.sleep(frequency)
                continue

        # If we reach here, we timed out. Return best matches if any, otherwise raise exception
        if best_matches:
            return best_matches
        raise HTTPException(
            status_code=408,
            detail=f"Timeout reached ({timeout}s) without finding {min_matches} cards with confidence {confidence}"
        )

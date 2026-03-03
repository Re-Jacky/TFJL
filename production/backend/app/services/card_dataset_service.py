import cv2
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from fastapi import HTTPException
from app.utils.logger import logger
from app.services.utility_services import UtilityService
import base64


class CardDatasetService:
    """Dataset management + JSONL logging."""
    
    BASE_DIR: Optional[Path] = None
    _unlabeled_metadata: Dict[str, Dict] = {}  # In-memory metadata: crop_id -> {slot_idx, top_guesses, timestamp}
    
    @staticmethod
    def initialize():
        """Create folder structure: dataset/unlabeled, dataset/labeled, labels/, models/"""
        try:
            if CardDatasetService.BASE_DIR is None:
                public_path = UtilityService.get_public_path()
                CardDatasetService.BASE_DIR = public_path.parent / "card_recognition"
            
            # Create directories
            (CardDatasetService.BASE_DIR / "dataset" / "unlabeled").mkdir(parents=True, exist_ok=True)
            (CardDatasetService.BASE_DIR / "dataset" / "labeled").mkdir(parents=True, exist_ok=True)
            (CardDatasetService.BASE_DIR / "labels").mkdir(parents=True, exist_ok=True)
            (CardDatasetService.BASE_DIR / "models").mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Initialized card recognition dataset at {CardDatasetService.BASE_DIR}")
            
        except Exception as e:
            logger.error(f"Error initializing dataset: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @staticmethod
    def save_unlabeled_crop(crop: np.ndarray, slot_idx: int, window_pid: int, top_guesses: List[str]) -> str:
        """
        Save crop to dataset/unlabeled/ as PNG.
        Filename: crop_{timestamp}_{slot_idx}_{pid}.png
        Store metadata in memory (crop_id -> {slot_idx, top_guesses, timestamp})
        Return crop_id
        """
        try:
            if CardDatasetService.BASE_DIR is None:
                CardDatasetService.initialize()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            crop_id = f"crop_{timestamp}_{slot_idx}_{window_pid}"
            
            # Save PNG
            unlabeled_dir = CardDatasetService.BASE_DIR / "dataset" / "unlabeled"
            crop_path = unlabeled_dir / f"{crop_id}.png"
            cv2.imwrite(str(crop_path), crop)
            
            # Store metadata in memory
            CardDatasetService._unlabeled_metadata[crop_id] = {
                "slot_idx": slot_idx,
                "top_guesses": top_guesses,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Saved unlabeled crop: {crop_id}")
            return crop_id
            
        except Exception as e:
            logger.error(f"Error saving unlabeled crop: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @staticmethod
    def apply_label(crop_id: str, card_name: str, crop_margins: Optional[Dict] = None) -> Dict:
        """
        Move crop from unlabeled/ to labeled/{card_name}/
        If crop_margins provided: {top, bottom, left, right}, apply cropping first
        Append to labels/annotations.jsonl: {"id": crop_id, "image_path": "...", "label": card_name, "slot_idx": int, "bbox": [0,0,70,90], "timestamp": ISO8601}
        Extract features and trigger CardModelService.train_incremental(card_name, features)
        Return {success, message, new_model_version}
        """
        try:
            if CardDatasetService.BASE_DIR is None:
                CardDatasetService.initialize()
            
            # Import here to avoid circular dependency
            from app.services.card_model_service import CardModelService
            from app.services.card_recognition_service import CardRecognitionService
            
            unlabeled_dir = CardDatasetService.BASE_DIR / "dataset" / "unlabeled"
            crop_path = unlabeled_dir / f"{crop_id}.png"
            
            if not crop_path.exists():
                raise HTTPException(status_code=404, detail=f"Crop {crop_id} not found")
            
            # Create labeled card directory
            labeled_card_dir = CardDatasetService.BASE_DIR / "dataset" / "labeled" / card_name
            labeled_card_dir.mkdir(parents=True, exist_ok=True)
            
            # Move crop to labeled directory
            new_path = labeled_card_dir / f"{crop_id}.png"
            crop_path.rename(new_path)
            
            # Load crop image
            crop_img = cv2.imread(str(new_path), cv2.IMREAD_GRAYSCALE)
            if crop_img is None:
                raise HTTPException(status_code=500, detail="Failed to load crop image")
            
            # Apply crop margins if provided
            if crop_margins:
                top = crop_margins.get('top', 0)
                bottom = crop_margins.get('bottom', 0)
                left = crop_margins.get('left', 0)
                right = crop_margins.get('right', 0)
                
                h, w = crop_img.shape
                # Apply inset cropping
                crop_img = crop_img[top:h-bottom, left:w-right]
                
                # Save cropped version
                cv2.imwrite(str(new_path), crop_img)
                logger.info(f"Applied crop margins to {crop_id}: top={top}, bottom={bottom}, left={left}, right={right}")
            
            # Preprocess for feature extraction (resize to 64x64)
            crop_eq = cv2.equalizeHist(crop_img)
            crop_resized = cv2.resize(crop_eq, (64, 64), interpolation=cv2.INTER_AREA)
            
            # Extract features
            features = CardRecognitionService.extract_features(crop_resized)
            
            # Trigger incremental training
            train_result = CardModelService.train_incremental(card_name, features)
            
            # Remove from unlabeled metadata
            if crop_id in CardDatasetService._unlabeled_metadata:
                del CardDatasetService._unlabeled_metadata[crop_id]
            
            logger.info(f"Applied label '{card_name}' to crop {crop_id}")
            
            return {
                "success": True,
                "message": f"Successfully labeled as '{card_name}'",
                "new_model_version": train_result["model_version"]
            }
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Error applying label: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @staticmethod
    def get_unlabeled_crops(limit: int = 10) -> List[Dict]:
        """
        List PNG files in dataset/unlabeled/, load metadata.
        Return [{crop_id, image_base64, slot_idx, top_guesses}, ...]
        """
        try:
            if CardDatasetService.BASE_DIR is None:
                CardDatasetService.initialize()
            
            unlabeled_dir = CardDatasetService.BASE_DIR / "dataset" / "unlabeled"
            png_files = sorted(unlabeled_dir.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
            
            crops = []
            for png_path in png_files:
                crop_id = png_path.stem
                
                # Load image and encode to base64
                img = cv2.imread(str(png_path))
                _, buffer = cv2.imencode('.png', img)
                image_base64 = base64.b64encode(buffer).decode('utf-8')
                
                # Get metadata
                metadata = CardDatasetService._unlabeled_metadata.get(crop_id, {})
                
                crops.append({
                    "crop_id": crop_id,
                    "image_base64": image_base64,
                    "slot_idx": metadata.get("slot_idx", 0),
                    "top_guesses": metadata.get("top_guesses", [])
                })
            
            return crops
            
        except Exception as e:
            logger.error(f"Error getting unlabeled crops: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @staticmethod
    def get_dataset_stats() -> Dict:
        """
        Count files in unlabeled/ and labeled/*/
        Return {labeled_count, unlabeled_count, per_card_counts: {card: count}}
        """
        try:
            if CardDatasetService.BASE_DIR is None:
                CardDatasetService.initialize()
            
            unlabeled_dir = CardDatasetService.BASE_DIR / "dataset" / "unlabeled"
            labeled_dir = CardDatasetService.BASE_DIR / "dataset" / "labeled"
            
            # Count unlabeled
            unlabeled_count = len(list(unlabeled_dir.glob("*.png")))
            
            # Count labeled per card
            per_card_counts = {}
            labeled_count = 0
            
            if labeled_dir.exists():
                for card_dir in labeled_dir.iterdir():
                    if card_dir.is_dir():
                        count = len(list(card_dir.glob("*.png")))
                        per_card_counts[card_dir.name] = count
                        labeled_count += count
            
            return {
                "labeled_count": labeled_count,
                "unlabeled_count": unlabeled_count,
                "per_card_counts": per_card_counts
            }
            
        except Exception as e:
            logger.error(f"Error getting dataset stats: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    def _detect_card_region(img: np.ndarray) -> Optional[dict]:
        """
        Auto-detect card bar region in screenshot.
        Returns dict with adjusted card slot positions or None if detection fails.
        
        Strategy:
        1. Look for bottom horizontal region with high edge density (card bar)
        2. Find 3 card-like rectangles in that region
        3. Calculate slot positions relative to detected region
        """
        try:
            height, width = img.shape
            
            # Search in bottom 30% of image (card bar is typically at bottom)
            search_start_y = int(height * 0.7)
            bottom_region = img[search_start_y:, :]
            
            # Edge detection to find card boundaries
            edges = cv2.Canny(bottom_region, 50, 150)
            
            # Find horizontal lines (card bar background)
            kernel_horizontal = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
            detected_lines = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel_horizontal)
            
            # Find contours (potential card slots)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter contours by aspect ratio (cards are ~70:90 = 0.78)
            card_candidates = []
            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                if h == 0:
                    continue
                aspect_ratio = w / h
                area = w * h
                
                # Card-like properties: aspect ratio ~0.6-1.0, reasonable size
                if 0.5 < aspect_ratio < 1.2 and 1000 < area < 50000:
                    # Adjust y to full image coordinates
                    adjusted_y = y + search_start_y
                    card_candidates.append({"x": x, "y": adjusted_y, "w": w, "h": h})
            
            # Sort by x position (left to right)
            card_candidates.sort(key=lambda c: c["x"])
            
            # Expect 3 cards in a row (with similar y positions)
            if len(card_candidates) >= 3:
                # Group by y position (cards should be on same horizontal line)
                y_tolerance = 20
                for i in range(len(card_candidates) - 2):
                    slot1, slot2, slot3 = card_candidates[i:i+3]
                    if (abs(slot1["y"] - slot2["y"]) < y_tolerance and
                        abs(slot2["y"] - slot3["y"]) < y_tolerance):
                        # Found 3 aligned cards
                        return {
                            "detected": True,
                            "slots": [slot1, slot2, slot3]
                        }
            
            # Detection failed
            return None
            
        except Exception as e:
            logger.debug(f"Card region detection failed: {str(e)}")
            return None

    @staticmethod
    def batch_train_from_screenshots() -> Dict:
        """
        Read all PNG files from screenshot folder,
        detect cards in each image, extract crops, and train incrementally.
        Return {processed_count, cards_extracted, new_model_version}
        """
        try:
            if CardDatasetService.BASE_DIR is None:
                CardDatasetService.initialize()
            
            # Import dependencies
            from app.services.card_recognition_service import CardRecognitionService
            from app.services.card_model_service import CardModelService
            from app.services.utility_services import UtilityService
            import cv2
            
            # Get screenshot directory
            public_path = UtilityService.get_public_path()
            screenshot_dir = public_path.parent / "screenshot"
            
            if not screenshot_dir.exists():
                return {
                    "processed_count": 0,
                    "cards_extracted": 0,
                    "message": "Screenshot folder not found"
                }
            
            # Get all PNG files
            png_files = sorted(screenshot_dir.glob("*.png"))
            
            if not png_files:
                return {
                    "processed_count": 0,
                    "cards_extracted": 0,
                    "message": "No screenshots found"
                }
            
            processed_count = 0
            cards_extracted = 0

            
            # Process each screenshot
            for png_path in png_files:
                try:
                    # Load image (convert to grayscale if needed)
                    img = cv2.imread(str(png_path), cv2.IMREAD_GRAYSCALE)
                    if img is None:
                        logger.warning(f"Could not load image: {png_path}")
                        continue
                    
                    # Auto-detect card region
                    detected_region = CardDatasetService._detect_card_region(img)
                    
                    if detected_region and detected_region["detected"]:
                        # Use detected positions
                        CARD_SLOTS = detected_region["slots"]
                        logger.info(f"Auto-detected card slots in {png_path.name}")
                    else:
                        # Fallback to fixed positions (for 1056×637 images)
                        if img.shape[0] < 637 or img.shape[1] < 680:
                            logger.warning(f"Image too small and auto-detection failed: {png_path.name} ({img.shape})")
                            continue
                        # Use fixed positions
                        CARD_SLOTS = [
                            {"x": 440, "y": 560, "w": 70, "h": 90},
                            {"x": 525, "y": 560, "w": 70, "h": 90},
                            {"x": 610, "y": 560, "w": 70, "h": 90}
                        ]
                        logger.debug(f"Using fixed card positions for {png_path.name}")
                    
                    # Extract card crops from each slot
                    for slot_idx, slot in enumerate(CARD_SLOTS):
                        x, y, w, h = slot["x"], slot["y"], slot["w"], slot["h"]
                        
                        # Ensure even dimensions for DCT (OpenCV requirement)
                        if w % 2 != 0:
                            w = w - 1  # Make even
                        if h % 2 != 0:
                            h = h - 1  # Make even
                        
                        # Check if slot position is within image bounds
                        if y + h > img.shape[0] or x + w > img.shape[1]:
                            continue
                        
                        # Extract crop
                        crop = img[y:y+h, x:x+w]
                        
                        # Ensure crop has even dimensions (double check after extraction)
                        if crop.shape[0] % 2 != 0:
                            crop = crop[:-1, :]  # Remove last row
                        if crop.shape[1] % 2 != 0:
                            crop = crop[:, :-1]  # Remove last column
                        
                        # Preprocess
                        crop_eq = cv2.equalizeHist(crop)
                        crop_resized = cv2.resize(crop_eq, (64, 64), interpolation=cv2.INTER_AREA)
                        
                        # Extract features
                        features = CardRecognitionService.extract_features(crop_resized)
                        
                        # Check if crop appears to contain a card (not empty)
                        # Simple heuristic: check if crop has significant variance
                        if np.std(crop) < 10:
                            continue  # Likely empty/blank
                        
                        # Save to unlabeled for manual labeling
                        # Use filename as identifier
                        crop_id = f"batch_{png_path.stem}_slot{slot_idx}"
                        
                        # Save to unlabeled directory
                        unlabeled_dir = CardDatasetService.BASE_DIR / "dataset" / "unlabeled"
                        crop_path = unlabeled_dir / f"{crop_id}.png"
                        cv2.imwrite(str(crop_path), crop)
                        
                        # Store metadata
                        CardDatasetService._unlabeled_metadata[crop_id] = {
                            "slot_idx": slot_idx,
                            "top_guesses": [],
                            "timestamp": datetime.now().isoformat(),
                            "source": str(png_path.name)
                        }
                        
                        cards_extracted += 1
                    
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing {png_path.name}: {str(e)}")
                    continue
            
            # Get current model version
            model_info = CardModelService.get_model_info()
            
            logger.info(f"Batch training completed: {processed_count} screenshots, {cards_extracted} cards extracted")
            
            return {
                "processed_count": processed_count,
                "cards_extracted": cards_extracted,
                "new_model_version": model_info.get("model_version", "none"),
                "message": f"Extracted {cards_extracted} cards from {processed_count} screenshots. Ready for labeling."
            }
            
        except Exception as e:
            logger.error(f"Error in batch training: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

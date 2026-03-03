import cv2
import numpy as np
from typing import Dict, List, Optional
from fastapi import HTTPException
from app.utils.logger import logger
from app.services.window_control_services import WindowControlService
from app.services.card_model_service import CardModelService
from app.services.card_dataset_service import CardDatasetService


class CardRecognitionService:
    """Feature extraction + classification for card recognition."""
    
    # Fixed card slot positions (relative to 1056x637 window)
    CARD_SLOTS = [
        {"x": 440, "y": 560, "w": 70, "h": 90, "idx": 0},
        {"x": 525, "y": 560, "w": 70, "h": 90, "idx": 1},
        {"x": 610, "y": 560, "w": 70, "h": 90, "idx": 2},
    ]
    
    @staticmethod
    def detect_cards(window_pid: int) -> Dict:
        """
        Detect cards in 3 slots. Returns {slots: [...], model_version: str}
        
        Steps:
        1. Capture bottom region (y=500 to bottom) via WindowControlService.capture_region
        2. For each CARD_SLOT, crop patch and adjust y coordinate (subtract 500)
        3. Preprocess: cv2.equalizeHist + cv2.resize to (64, 64)
        4. Extract features via extract_features()
        5. Load model via CardModelService.load_model()
        6. If model exists: classify via classify_patch()
        7. If no model or low confidence (<0.3): save to unlabeled via CardDatasetService.save_unlabeled_crop()
        8. Return slot results with card names, confidences, crop_ids
        """
        try:
            hwnd = WindowControlService.find_window(window_pid)
            
            # Capture bottom region (y=500 to bottom)
            # Assuming standard window size 1056x637, bottom region is ~137px tall
            bottom_region = WindowControlService.capture_region(hwnd, (0, 500, 1056, 137))
            
            if bottom_region is None:
                raise HTTPException(status_code=500, detail="Failed to capture window region")
            
            # Load model
            model_data = CardModelService.load_model()
            
            slots = []
            for slot_config in CardRecognitionService.CARD_SLOTS:
                slot_idx = slot_config["idx"]
                x = slot_config["x"]
                y = slot_config["y"] - 500  # Adjust y coordinate since we captured from y=500
                w = slot_config["w"]
                h = slot_config["h"]
                
                # Crop patch from bottom region
                if y < 0 or y + h > bottom_region.shape[0] or x + w > bottom_region.shape[1]:
                    logger.warning(f"Slot {slot_idx} out of bounds, skipping")
                    slots.append({
                        "slot_idx": slot_idx,
                        "card": "unknown",
                        "confidence": 0,
                        "bbox": [x, slot_config["y"], w, h],
                        "top_k_guesses": []
                    })
                    continue
                
                patch = bottom_region[y:y+h, x:x+w]
                
                # Preprocess: equalize histogram + resize to 64x64
                patch_eq = cv2.equalizeHist(patch)
                patch_resized = cv2.resize(patch_eq, (64, 64))
                
                # Extract features
                features = CardRecognitionService.extract_features(patch_resized)
                
                # Classify
                if model_data is not None:
                    classification = CardRecognitionService.classify_patch(
                        features, 
                        model_data["centroids"], 
                        model_data["card_names"]
                    )
                    
                    if classification["card"] == "unknown" or classification["confidence"] < 0.3:
                        # Save to unlabeled
                        crop_id = CardDatasetService.save_unlabeled_crop(
                            patch_resized, 
                            slot_idx, 
                            window_pid, 
                            classification.get("top_k_guesses", [])
                        )
                        
                        slots.append({
                            "slot_idx": slot_idx,
                            "card": "unknown",
                            "confidence": 0,
                            "bbox": [x, slot_config["y"], w, h],
                            "crop_id": crop_id,
                            "top_k_guesses": classification.get("top_k_guesses", [])
                        })
                    else:
                        slots.append({
                            "slot_idx": slot_idx,
                            "card": classification["card"],
                            "confidence": classification["confidence"],
                            "bbox": [x, slot_config["y"], w, h],
                            "top_k": classification.get("top_k", [])
                        })
                else:
                    # No model yet, save to unlabeled
                    crop_id = CardDatasetService.save_unlabeled_crop(
                        patch_resized, 
                        slot_idx, 
                        window_pid, 
                        []
                    )
                    
                    slots.append({
                        "slot_idx": slot_idx,
                        "card": "unknown",
                        "confidence": 0,
                        "bbox": [x, slot_config["y"], w, h],
                        "crop_id": crop_id,
                        "top_k_guesses": []
                    })
            
            model_version = model_data["version"] if model_data else None
            
            return {
                "success": True,
                "slots": slots,
                "model_version": model_version
            }
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Error detecting cards: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @staticmethod
    def extract_features(patch: np.ndarray) -> np.ndarray:
        """
        Convert 64x64 grayscale patch to feature vector.
        Use cv2.dct() on float32 patch, extract top-left 8x8 DCT coefficients, flatten to 64-dim vector.
        """
        try:
            # Convert to float32 for DCT
            patch_float = np.float32(patch) / 255.0
            
            # Compute DCT
            dct_full = cv2.dct(patch_float)
            
            # Extract top-left 8x8 coefficients (low-frequency components)
            dct_features = dct_full[:8, :8]
            
            # Flatten to 64-dim vector
            features = dct_features.flatten()
            
            return features
            
        except Exception as e:
            logger.error(f"Error extracting features: {str(e)}")
            raise
    
    @staticmethod
    def classify_patch(features: np.ndarray, centroids: np.ndarray, card_names: List[str], threshold: float = 0.3) -> Dict:
        """
        Nearest-centroid classification.
        
        - Compute L2 distances to all centroids
        - Get top-5 nearest
        - If closest distance < threshold: return {card: card_names[idx], confidence: 1/(1+dist), top_k: [...]}
        - Else: return {card: "unknown", confidence: 0, top_k_guesses: top-5 card names}
        """
        try:
            # Compute L2 distances to all centroids
            distances = np.linalg.norm(centroids - features, axis=1)
            
            # Get indices sorted by distance (closest first)
            sorted_indices = np.argsort(distances)
            
            # Get top-5 nearest
            top_k_indices = sorted_indices[:5]
            top_k_distances = distances[top_k_indices]
            top_k_names = [card_names[i] for i in top_k_indices]
            
            # Check if closest distance is below threshold
            closest_distance = top_k_distances[0]
            
            if closest_distance < threshold:
                confidence = 1.0 / (1.0 + closest_distance)
                return {
                    "card": top_k_names[0],
                    "confidence": confidence,
                    "top_k": top_k_names
                }
            else:
                return {
                    "card": "unknown",
                    "confidence": 0,
                    "top_k_guesses": top_k_names
                }
                
        except Exception as e:
            logger.error(f"Error classifying patch: {str(e)}")
            raise

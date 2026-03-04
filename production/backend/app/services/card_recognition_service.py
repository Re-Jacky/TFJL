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
    
    # Configuration: Feature extraction method
    FEATURE_TYPE = "dct"  # Options: "dct", "hog", "hybrid"
    
    # Configuration: Classifier method
    CLASSIFIER_TYPE = "centroid"  # Options: "centroid", "knn"
    
    # Configuration: k-NN parameters
    KNN_K = 5
    
    # Configuration: Classification threshold
    THRESHOLD = 0.3
    
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
                
                # Preprocess: CLAHE (Contrast Limited Adaptive Histogram Equalization) + resize to 64x64
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                patch_clahe = clahe.apply(patch)
                patch_resized = cv2.resize(patch_clahe, (64, 64))
                
                # Extract features based on configuration
                feature_type = CardRecognitionService.FEATURE_TYPE
                if feature_type == "hog":
                    features = CardRecognitionService.extract_hog_features(patch_resized)
                elif feature_type == "hybrid":
                    # For hybrid, need color patch - convert grayscale back to BGR for consistency
                    patch_rgb = cv2.cvtColor(patch, cv2.COLOR_GRAY2BGR)
                    patch_rgb_resized = cv2.resize(patch_rgb, (64, 64))
                    features = CardRecognitionService.extract_hybrid_features(patch_rgb_resized, patch_resized)
                else:  # dct (default)
                    features = CardRecognitionService.extract_features(patch_resized)
                
                # Classify based on configuration
                classifier_type = CardRecognitionService.CLASSIFIER_TYPE
                
                if classifier_type == "knn":
                    # k-NN requires all training samples, not just centroids
                    # For now, fall back to centroid if using k-NN (needs model structure update)
                    logger.warning("k-NN classifier requires model with training_features/training_labels. Falling back to centroid.")
                    classification = CardRecognitionService.classify_patch(
                        features, 
                        model_data["centroids"], 
                        model_data["card_names"],
                        threshold=CardRecognitionService.THRESHOLD
                    )
                else:  # centroid (default)
                    classification = CardRecognitionService.classify_patch(
                        features, 
                        model_data["centroids"], 
                        model_data["card_names"],
                        threshold=CardRecognitionService.THRESHOLD
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
    def detect_cards_from_file(filename: str) -> Dict:
        """
        Detect cards from a saved screenshot file instead of active window.
        
        Args:
            filename: Screenshot filename in production/screenshot/ folder
        
        Returns:
            Same format as detect_cards() - {success, slots, model_version}
        """
        try:
            import os
            from pathlib import Path
            
            # Construct file path
            screenshot_dir = Path(__file__).parent.parent.parent / "screenshot"
            file_path = screenshot_dir / filename
            
            if not file_path.exists():
                raise HTTPException(status_code=404, detail=f"Screenshot file not found: {filename}")
            
            # Read screenshot as grayscale
            screenshot = cv2.imread(str(file_path), cv2.IMREAD_GRAYSCALE)
            if screenshot is None:
                raise HTTPException(status_code=500, detail=f"Failed to read screenshot: {filename}")
            
            # Load model
            model_data = CardModelService.load_model()
            
            slots = []
            for slot_config in CardRecognitionService.CARD_SLOTS:
                slot_idx = slot_config["idx"]
                x = slot_config["x"]
                y = slot_config["y"]
                w = slot_config["w"]
                h = slot_config["h"]
                
                # Crop patch from screenshot
                if y < 0 or y + h > screenshot.shape[0] or x + w > screenshot.shape[1]:
                    logger.warning(f"Slot {slot_idx} out of bounds, skipping")
                    slots.append({
                        "slot_idx": slot_idx,
                        "card": "unknown",
                        "confidence": 0,
                        "bbox": [x, y, w, h],
                        "top_k_guesses": []
                    })
                    continue
                
                patch = screenshot[y:y+h, x:x+w]
                
                # Preprocess: CLAHE + resize to 64x64
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                patch_clahe = clahe.apply(patch)
                patch_resized = cv2.resize(patch_clahe, (64, 64))
                
                # Extract features based on configuration
                feature_type = CardRecognitionService.FEATURE_TYPE
                if feature_type == "hog":
                    features = CardRecognitionService.extract_hog_features(patch_resized)
                elif feature_type == "hybrid":
                    patch_rgb = cv2.cvtColor(patch, cv2.COLOR_GRAY2BGR)
                    patch_rgb_resized = cv2.resize(patch_rgb, (64, 64))
                    features = CardRecognitionService.extract_hybrid_features(patch_rgb_resized, patch_resized)
                else:  # dct (default)
                    features = CardRecognitionService.extract_features(patch_resized)
                
                # Classify based on configuration
                classifier_type = CardRecognitionService.CLASSIFIER_TYPE
                
                if classifier_type == "knn":
                    logger.warning("k-NN classifier requires model with training_features/training_labels. Falling back to centroid.")
                    classification = CardRecognitionService.classify_patch(
                        features, 
                        model_data["centroids"], 
                        model_data["card_names"],
                        threshold=CardRecognitionService.THRESHOLD
                    )
                else:  # centroid (default)
                    classification = CardRecognitionService.classify_patch(
                        features, 
                        model_data["centroids"], 
                        model_data["card_names"],
                        threshold=CardRecognitionService.THRESHOLD
                    )
                
                # If confidence < threshold, save as unlabeled
                if classification["confidence"] < CardRecognitionService.THRESHOLD:
                    crop_id = CardDatasetService.save_unlabeled_crop(
                        patch, 
                        filename, 
                        slot_idx,
                        top_guesses=classification.get("top_k", [])
                    )
                    slots.append({
                        "slot_idx": slot_idx,
                        "card": "unknown",
                        "confidence": classification["confidence"],
                        "bbox": [x, y, w, h],
                        "crop_id": crop_id,
                        "top_k_guesses": classification.get("top_k", [])
                    })
                else:
                    slots.append({
                        "slot_idx": slot_idx,
                        "card": classification["card"],
                        "confidence": classification["confidence"],
                        "bbox": [x, y, w, h],
                        "top_k": classification.get("top_k", [])
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
            logger.error(f"Error detecting cards from file: {str(e)}")
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
    def extract_hog_features(patch: np.ndarray) -> np.ndarray:
        """
        Extract HOG (Histogram of Oriented Gradients) features.
        Better than DCT for capturing card borders, symbols, and text.
        
        Args:
            patch: 64x64 grayscale patch
        
        Returns:
            HOG feature vector (144-dim for 64x64 with these params)
        """
        try:
            from skimage.feature import hog
            
            hog_features = hog(
                patch,
                orientations=9,           # 9 gradient directions
                pixels_per_cell=(8, 8),   # 64x64 ÷ 8 = 8 cells per dimension
                cells_per_block=(2, 2),   # Local normalization blocks
                block_norm='L2-Hys',      # Robust to lighting changes
                feature_vector=True
            )
            return hog_features
            
        except Exception as e:
            logger.error(f"Error extracting HOG features: {str(e)}")
            raise
    
    @staticmethod
    def extract_hybrid_features(patch_rgb: np.ndarray, patch_gray: np.ndarray) -> np.ndarray:
        """
        Hybrid HOG (structure) + HSV Color Histogram (appearance).
        Use when cards have distinct colors.
        
        Args:
            patch_rgb: 64x64 color patch (BGR format from OpenCV)
            patch_gray: 64x64 grayscale patch
        
        Returns:
            Concatenated feature vector (HOG + H-channel + S-channel histograms)
        """
        try:
            from skimage.feature import hog
            
            # 1. HOG for structure (144-dim)
            hog_feat = hog(
                patch_gray,
                orientations=9,
                pixels_per_cell=(8, 8),
                cells_per_block=(2, 2),
                block_norm='L2-Hys',
                feature_vector=True
            )
            
            # 2. Color histograms (HSV space better than RGB for UI)
            hsv = cv2.cvtColor(patch_rgb, cv2.COLOR_BGR2HSV)
            
            # Hue histogram (16 bins)
            hist_h = cv2.calcHist([hsv], [0], None, [16], [0, 180])
            hist_h = cv2.normalize(hist_h, hist_h).flatten()
            
            # Saturation histogram (16 bins)
            hist_s = cv2.calcHist([hsv], [1], None, [16], [0, 256])
            hist_s = cv2.normalize(hist_s, hist_s).flatten()
            
            # Concatenate: 144 (HOG) + 16 (H) + 16 (S) = 176-dim
            return np.concatenate([hog_feat, hist_h, hist_s])
            
        except Exception as e:
            logger.error(f"Error extracting hybrid features: {str(e)}")
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
    
    @staticmethod
    def classify_knn(features: np.ndarray, 
                     training_features: np.ndarray,
                     training_labels: List[str],
                     k: int = 5,
                     threshold: float = 0.3) -> Dict:
        """
        k-Nearest Neighbors classification with distance weighting.
        
        Args:
            features: Query feature vector
            training_features: (N, feature_dim) array of all training samples
            training_labels: List of N card names corresponding to training_features
            k: Number of neighbors to consider
            threshold: Distance threshold for unknown classification
        
        Returns:
            {card: str, confidence: float, top_k: List[str]}
        """
        try:
            from collections import defaultdict
            
            # Compute distances to all training samples
            distances = np.linalg.norm(training_features - features, axis=1)
            
            # Get k nearest neighbors
            k_indices = np.argsort(distances)[:k]
            k_distances = distances[k_indices]
            k_labels = [training_labels[i] for i in k_indices]
            
            # Distance-weighted voting (closer neighbors have more influence)
            weights = 1.0 / (1.0 + k_distances)
            
            # Count weighted votes per label
            vote_scores = defaultdict(float)
            for label, weight in zip(k_labels, weights):
                vote_scores[label] += weight
            
            # Get winner
            winner_label = max(vote_scores, key=vote_scores.get)
            winner_score = vote_scores[winner_label]
            
            # Normalize confidence
            total_weight = sum(weights)
            confidence = winner_score / total_weight
            
            # Check threshold on closest distance
            closest_distance = k_distances[0]
            
            if closest_distance < threshold:
                return {
                    "card": winner_label,
                    "confidence": confidence,
                    "top_k": k_labels
                }
            else:
                return {
                    "card": "unknown",
                    "confidence": 0,
                    "top_k_guesses": k_labels
                }
                
        except Exception as e:
            logger.error(f"Error in k-NN classification: {str(e)}")
            raise

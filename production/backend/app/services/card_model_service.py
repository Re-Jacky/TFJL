import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from fastapi import HTTPException
from app.utils.logger import logger
from app.services.utility_services import UtilityService
import cv2


class CardModelService:
    """Model training + versioning."""
    
    _cached_model: Optional[Dict] = None  # In-memory cache: {centroids, card_names, metadata, version}
    
    @staticmethod
    def load_model() -> Optional[Dict]:
        """
        Load from models/latest.json (contains version pointer).
        If exists: load models/{version}/centroids.npy, card_names.json, metadata.json
        Cache in _cached_model.
        Return {centroids: np.ndarray, card_names: list, metadata: dict, version: str} or None if no model
        """
        try:
            # Return cached model if available
            if CardModelService._cached_model is not None:
                return CardModelService._cached_model
            
            # Initialize dataset if needed
            from app.services.card_dataset_service import CardDatasetService
            if CardDatasetService.BASE_DIR is None:
                CardDatasetService.initialize()
            
            base_dir = CardDatasetService.BASE_DIR
            latest_path = base_dir / "models" / "latest.json"
            
            if not latest_path.exists():
                logger.info("No model found")
                return None
            
            # Load version pointer
            with latest_path.open("r", encoding="utf-8") as f:
                latest_data = json.load(f)
                version = latest_data.get("version")
            
            if not version:
                return None
            
            # Load model files
            model_dir = base_dir / "models" / version
            centroids_path = model_dir / "centroids.npy"
            card_names_path = model_dir / "card_names.json"
            metadata_path = model_dir / "metadata.json"
            
            if not all([centroids_path.exists(), card_names_path.exists(), metadata_path.exists()]):
                logger.warning(f"Model version {version} incomplete")
                return None
            
            centroids = np.load(str(centroids_path))
            
            with card_names_path.open("r", encoding="utf-8") as f:
                card_names = json.load(f)
            
            with metadata_path.open("r", encoding="utf-8") as f:
                metadata = json.load(f)
            
            # Cache model
            CardModelService._cached_model = {
                "centroids": centroids,
                "card_names": card_names,
                "metadata": metadata,
                "version": version
            }
            
            logger.info(f"Loaded model version {version}")
            return CardModelService._cached_model
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return None
    
    @staticmethod
    def train_incremental(card_name: str, features: np.ndarray) -> Dict:
        """
        Online centroid update:
        1. Load current model (or initialize empty)
        2. If card_name new: add to card_names, initialize centroid = features
        3. Else: update centroid = old_centroid + (features - old_centroid) / (count + 1)
        4. Increment metadata["train_samples"][card_name]
        5. Save new model snapshot with timestamp version
        6. Update models/latest.json
        7. Clear _cached_model
        Return {success, model_version, train_count}
        """
        try:
            # Load current model or initialize empty
            model_data = CardModelService.load_model()
            
            if model_data is None:
                # Initialize new model
                centroids = features.reshape(1, -1)
                card_names = [card_name]
                metadata = {
                    "train_samples": {card_name: 1},
                    "last_updated": datetime.now().isoformat(),
                    "training_method": "incremental"
                }
            else:
                centroids = model_data["centroids"]
                card_names = model_data["card_names"]
                metadata = model_data["metadata"]
                
                if card_name in card_names:
                    # Update existing centroid (online mean update)
                    idx = card_names.index(card_name)
                    old_count = metadata["train_samples"].get(card_name, 1)
                    new_count = old_count + 1
                    
                    old_centroid = centroids[idx]
                    new_centroid = old_centroid + (features - old_centroid) / new_count
                    centroids[idx] = new_centroid
                    
                    metadata["train_samples"][card_name] = new_count
                else:
                    # Add new card
                    centroids = np.vstack([centroids, features.reshape(1, -1)])
                    card_names.append(card_name)
                    metadata["train_samples"][card_name] = 1
                
                metadata["last_updated"] = datetime.now().isoformat()
            
            # Save new model snapshot
            version = CardModelService.save_model_snapshot(centroids, card_names, metadata)
            
            # Clear cache
            CardModelService._cached_model = None
            
            train_count = metadata["train_samples"][card_name]
            
            logger.info(f"Incremental training: {card_name}, count={train_count}, version={version}")
            
            return {
                "success": True,
                "model_version": version,
                "train_count": train_count
            }
            
        except Exception as e:
            logger.error(f"Error in incremental training: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @staticmethod
    def train_full_rebuild() -> Dict:
        """
        Batch rebuild from all labeled data:
        1. Scan dataset/labeled/*/ for all PNGs
        2. For each card: load all crops, extract features, compute mean centroid
        3. Save new model snapshot
        4. Update models/latest.json
        5. Clear _cached_model
        Return {success, model_version, accuracy: None (no validation yet), train_samples}
        """
        try:
            from app.services.card_dataset_service import CardDatasetService
            from app.services.card_recognition_service import CardRecognitionService
            
            if CardDatasetService.BASE_DIR is None:
                CardDatasetService.initialize()
            
            base_dir = CardDatasetService.BASE_DIR
            labeled_dir = base_dir / "dataset" / "labeled"
            
            if not labeled_dir.exists():
                raise HTTPException(status_code=404, detail="No labeled data found")
            
            all_centroids = []
            all_card_names = []
            train_samples = {}
            
            # Scan each card directory
            for card_dir in sorted(labeled_dir.iterdir()):
                if not card_dir.is_dir():
                    continue
                
                card_name = card_dir.name
                png_files = list(card_dir.glob("*.png"))
                
                if len(png_files) == 0:
                    continue
                
                # Extract features from all crops
                features_list = []
                for png_path in png_files:
                    crop = cv2.imread(str(png_path), cv2.IMREAD_GRAYSCALE)
                    if crop is None:
                        logger.warning(f"Failed to load {png_path}")
                        continue
                    
                    features = CardRecognitionService.extract_features(crop)
                    features_list.append(features)
                
                if len(features_list) == 0:
                    continue
                
                # Compute mean centroid
                features_array = np.array(features_list)
                centroid = np.mean(features_array, axis=0)
                
                all_centroids.append(centroid)
                all_card_names.append(card_name)
                train_samples[card_name] = len(features_list)
            
            if len(all_centroids) == 0:
                raise HTTPException(status_code=400, detail="No valid training data found")
            
            # Create centroids array
            centroids = np.array(all_centroids)
            
            # Create metadata
            metadata = {
                "train_samples": train_samples,
                "last_updated": datetime.now().isoformat(),
                "training_method": "full_rebuild",
                "total_samples": sum(train_samples.values())
            }
            
            # Save model snapshot
            version = CardModelService.save_model_snapshot(centroids, all_card_names, metadata)
            
            # Clear cache
            CardModelService._cached_model = None
            
            logger.info(f"Full rebuild complete: {len(all_card_names)} cards, {metadata['total_samples']} samples, version={version}")
            
            return {
                "success": True,
                "model_version": version,
                "accuracy": None,
                "train_samples": metadata["total_samples"]
            }
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Error in full rebuild: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @staticmethod
    def get_model_info() -> Dict:
        """
        Load model, return metadata + version.
        {model_version, trained_cards: list, total_samples, last_updated}
        """
        try:
            model_data = CardModelService.load_model()
            
            if model_data is None:
                return {
                    "model_version": None,
                    "trained_cards": [],
                    "total_samples": 0,
                    "last_updated": None
                }
            
            metadata = model_data["metadata"]
            
            return {
                "model_version": model_data["version"],
                "trained_cards": model_data["card_names"],
                "total_samples": sum(metadata.get("train_samples", {}).values()),
                "last_updated": metadata.get("last_updated")
            }
            
        except Exception as e:
            logger.error(f"Error getting model info: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @staticmethod
    def save_model_snapshot(centroids: np.ndarray, card_names: List[str], metadata: Dict) -> str:
        """
        Helper: Save to models/v{timestamp}/ as centroids.npy, card_names.json, metadata.json
        Return version string
        """
        try:
            from app.services.card_dataset_service import CardDatasetService
            
            if CardDatasetService.BASE_DIR is None:
                CardDatasetService.initialize()
            
            base_dir = CardDatasetService.BASE_DIR
            
            # Create version string
            version = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            model_dir = base_dir / "models" / version
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # Save centroids
            np.save(str(model_dir / "centroids.npy"), centroids)
            
            # Save card names
            with (model_dir / "card_names.json").open("w", encoding="utf-8") as f:
                json.dump(card_names, f, ensure_ascii=False, indent=2)
            
            # Save metadata
            with (model_dir / "metadata.json").open("w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            # Update latest.json pointer
            latest_path = base_dir / "models" / "latest.json"
            with latest_path.open("w", encoding="utf-8") as f:
                json.dump({"version": version}, f, indent=2)
            
            logger.info(f"Saved model snapshot: {version}")
            return version
            
        except Exception as e:
            logger.error(f"Error saving model snapshot: {str(e)}")
            raise

    @staticmethod
    def export_model(export_path: str) -> Dict:
        """
        Export trained model to specified path as ZIP archive.
        Includes: centroids.npy, card_names.json, metadata.json
        Return {success, export_path, model_version}
        """
        try:
            import zipfile
            
            model_data = CardModelService.load_model()
            
            if model_data is None:
                raise HTTPException(status_code=404, detail="No trained model found")
            
            from app.services.card_dataset_service import CardDatasetService
            if CardDatasetService.BASE_DIR is None:
                CardDatasetService.initialize()
            
            base_dir = CardDatasetService.BASE_DIR
            version = model_data["version"]
            model_dir = base_dir / "models" / version
            
            # Create export path
            export_file = Path(export_path)
            export_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Create ZIP archive
            with zipfile.ZipFile(export_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(model_dir / "centroids.npy", "centroids.npy")
                zipf.write(model_dir / "card_names.json", "card_names.json")
                zipf.write(model_dir / "metadata.json", "metadata.json")
            
            logger.info(f"Exported model {version} to {export_file}")
            
            return {
                "success": True,
                "export_path": str(export_file),
                "model_version": version
            }
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Error exporting model: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    def import_model(import_path: str) -> Dict:
        """
        Import trained model from ZIP archive.
        Extracts to models/v{timestamp}_imported/
        Updates latest.json pointer.
        Return {success, model_version, trained_cards}
        """
        try:
            import zipfile
            
            import_file = Path(import_path)
            
            if not import_file.exists():
                raise HTTPException(status_code=404, detail=f"Import file not found: {import_path}")
            
            from app.services.card_dataset_service import CardDatasetService
            if CardDatasetService.BASE_DIR is None:
                CardDatasetService.initialize()
            
            base_dir = CardDatasetService.BASE_DIR
            
            # Create import version directory
            version = f"v{datetime.now().strftime('%Y%m%d_%H%M%S')}_imported"
            model_dir = base_dir / "models" / version
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract ZIP archive
            with zipfile.ZipFile(import_file, 'r') as zipf:
                # Validate ZIP contents
                required_files = ["centroids.npy", "card_names.json", "metadata.json"]
                zip_files = zipf.namelist()
                
                for required in required_files:
                    if required not in zip_files:
                        raise HTTPException(status_code=400, detail=f"Invalid model archive: missing {required}")
                
                # Extract files
                zipf.extractall(model_dir)
            
            # Validate extracted files
            try:
                centroids = np.load(str(model_dir / "centroids.npy"))
                with (model_dir / "card_names.json").open("r", encoding="utf-8") as f:
                    card_names = json.load(f)
                with (model_dir / "metadata.json").open("r", encoding="utf-8") as f:
                    metadata = json.load(f)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid model data: {str(e)}")
            
            # Update latest.json pointer
            latest_path = base_dir / "models" / "latest.json"
            with latest_path.open("w", encoding="utf-8") as f:
                json.dump({"version": version}, f, indent=2)
            
            # Clear cache
            CardModelService._cached_model = None
            
            logger.info(f"Imported model as {version} with {len(card_names)} cards")
            
            return {
                "success": True,
                "model_version": version,
                "trained_cards": card_names,
                "total_samples": sum(metadata.get("train_samples", {}).values())
            }
            
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Error importing model: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

#!/usr/bin/env python3
"""
Validation script for card recognition algorithm improvements.
Tests different feature extraction and preprocessing methods on sample images.
"""

import cv2
import numpy as np
from pathlib import Path
import sys
import os

# Add app to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.services.card_recognition_service import CardRecognitionService


def load_samples(sample_dir: Path):
    """Load all sample screenshots."""
    samples = []
    for png_file in sorted(sample_dir.glob("*.png")):
        img = cv2.imread(str(png_file))
        if img is not None:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            samples.append({
                "filename": png_file.name,
                "image": img,
                "gray": gray
            })
    return samples


def extract_card_patches(sample):
    """Extract 3 card patches from a sample screenshot."""
    CARD_SLOTS = [
        {"x": 440, "y": 560, "w": 70, "h": 90, "idx": 0},
        {"x": 525, "y": 560, "w": 70, "h": 90, "idx": 1},
        {"x": 610, "y": 560, "w": 70, "h": 90, "idx": 2},
    ]
    
    patches = []
    gray = sample["gray"]
    img = sample["image"]
    
    for slot in CARD_SLOTS:
        x, y, w, h = slot["x"], slot["y"], slot["w"], slot["h"]
        
        # Extract grayscale patch
        patch = gray[y:y+h, x:x+w]
        
        # Apply CLAHE preprocessing
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        patch_clahe = clahe.apply(patch)
        patch_resized = cv2.resize(patch_clahe, (64, 64))
        
        # Extract color patch for hybrid features
        patch_rgb = img[y:y+h, x:x+w]
        patch_rgb_resized = cv2.resize(patch_rgb, (64, 64))
        
        patches.append({
            "slot_idx": slot["idx"],
            "patch_gray": patch_resized,
            "patch_rgb": patch_rgb_resized,
            "original": patch
        })
    
    return patches


def compare_feature_methods(patches):
    """Compare DCT, HOG, and Hybrid feature extraction."""
    print("\n" + "="*70)
    print("Feature Extraction Comparison")
    print("="*70)
    
    for i, patch_data in enumerate(patches[:3]):  # Test first 3 patches
        patch_gray = patch_data["patch_gray"]
        patch_rgb = patch_data["patch_rgb"]
        
        # DCT features (original)
        dct_features = CardRecognitionService.extract_features(patch_gray)
        
        # HOG features (new)
        hog_features = CardRecognitionService.extract_hog_features(patch_gray)
        
        # Hybrid features (new)
        hybrid_features = CardRecognitionService.extract_hybrid_features(patch_rgb, patch_gray)
        
        print(f"\nPatch {i}:")
        print(f"  DCT:    {len(dct_features):3d}-dim, std={dct_features.std():.3f}, range=[{dct_features.min():6.2f}, {dct_features.max():6.2f}]")
        print(f"  HOG:    {len(hog_features):3d}-dim, std={hog_features.std():.3f}, range=[{hog_features.min():6.2f}, {hog_features.max():6.2f}]")
        print(f"  Hybrid: {len(hybrid_features):3d}-dim, std={hybrid_features.std():.3f}, range=[{hybrid_features.min():6.2f}, {hybrid_features.max():6.2f}]")


def compare_preprocessing(patches):
    """Compare histogram equalization vs CLAHE."""
    print("\n" + "="*70)
    print("Preprocessing Comparison")
    print("="*70)
    
    for i, patch_data in enumerate(patches[:3]):
        original = patch_data["original"]
        
        # Old method: Histogram Equalization
        patch_eq = cv2.equalizeHist(original)
        patch_eq_resized = cv2.resize(patch_eq, (64, 64))
        
        # New method: CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        patch_clahe = clahe.apply(original)
        patch_clahe_resized = cv2.resize(patch_clahe, (64, 64))
        
        print(f"\nPatch {i}:")
        print(f"  Original:     mean={original.mean():.1f}, std={original.std():.1f}")
        print(f"  equalizeHist: mean={patch_eq_resized.mean():.1f}, std={patch_eq_resized.std():.1f}")
        print(f"  CLAHE:        mean={patch_clahe_resized.mean():.1f}, std={patch_clahe_resized.std():.1f}")


def compute_discriminability(patches):
    """Compute pairwise distances to measure discriminability."""
    print("\n" + "="*70)
    print("Feature Discriminability (Pairwise L2 Distances)")
    print("="*70)
    
    feature_types = ["DCT", "HOG", "Hybrid"]
    
    for feature_name in feature_types:
        print(f"\n{feature_name} Features:")
        
        feature_vectors = []
        for patch_data in patches[:6]:  # Use first 6 patches
            patch_gray = patch_data["patch_gray"]
            patch_rgb = patch_data["patch_rgb"]
            
            if feature_name == "DCT":
                features = CardRecognitionService.extract_features(patch_gray)
            elif feature_name == "HOG":
                features = CardRecognitionService.extract_hog_features(patch_gray)
            else:  # Hybrid
                features = CardRecognitionService.extract_hybrid_features(patch_rgb, patch_gray)
            
            feature_vectors.append(features)
        
        # Compute pairwise distances
        distances = []
        for i in range(len(feature_vectors)):
            for j in range(i+1, len(feature_vectors)):
                dist = np.linalg.norm(feature_vectors[i] - feature_vectors[j])
                distances.append(dist)
        
        distances = np.array(distances)
        print(f"  Mean distance: {distances.mean():.3f}")
        print(f"  Std distance:  {distances.std():.3f}")
        print(f"  Min distance:  {distances.min():.3f}")
        print(f"  Max distance:  {distances.max():.3f}")
        print(f"  Range:         {distances.max() - distances.min():.3f}")


def main():
    print("="*70)
    print("Card Recognition Algorithm Validation")
    print("="*70)
    
    # Load sample images
    sample_dir = Path(__file__).parent.parent / "public" / "sample"
    
    if not sample_dir.exists():
        print(f"Error: Sample directory not found: {sample_dir}")
        return
    
    samples = load_samples(sample_dir)
    print(f"\nLoaded {len(samples)} sample screenshots from {sample_dir}")
    
    # Extract all card patches
    all_patches = []
    for sample in samples:
        patches = extract_card_patches(sample)
        all_patches.extend(patches)
        print(f"  {sample['filename']}: {len(patches)} card patches extracted")
    
    print(f"\nTotal patches: {len(all_patches)}")
    
    # Run comparisons
    compare_preprocessing(all_patches)
    compare_feature_methods(all_patches)
    compute_discriminability(all_patches)
    
    # Summary
    print("\n" + "="*70)
    print("Summary of Improvements")
    print("="*70)
    print("\n✓ Phase 1: CLAHE preprocessing implemented")
    print("  - Reduces noise over-enhancement compared to histogram equalization")
    print("  - Better local contrast adaptation for game UI elements")
    
    print("\n✓ Phase 2: HOG feature extraction implemented")
    print("  - Captures edge orientation patterns (better for card borders/symbols)")
    print("  - 144-dimensional features (vs 64-dim DCT)")
    
    print("\n✓ Phase 3: Hybrid HOG+Color features implemented")
    print("  - Combines structural (HOG) and appearance (color histogram) features")
    print("  - 176-dimensional features (144 HOG + 32 color)")
    
    print("\n✓ Phase 4: k-NN classifier implemented")
    print("  - Distance-weighted voting for better handling of intra-class variation")
    print("  - More robust than single-centroid approach")
    
    print("\n✓ Phase 5: Configuration system implemented")
    print("  - FEATURE_TYPE: 'dct', 'hog', 'hybrid'")
    print("  - CLASSIFIER_TYPE: 'centroid', 'knn'")
    print("  - Tunable parameters: KNN_K, THRESHOLD")
    
    print("\n" + "="*70)
    print("Next Steps:")
    print("="*70)
    print("1. Collect labeled ground truth for sample images")
    print("2. Train model with new features: CardModelService.train_full_rebuild()")
    print("3. A/B test: Compare DCT vs HOG vs Hybrid on real game cards")
    print("4. Tune THRESHOLD parameter based on precision/recall tradeoff")
    print("5. Update model storage to support k-NN (store all training samples)")
    print("\nConfiguration to test HOG features:")
    print("  CardRecognitionService.FEATURE_TYPE = 'hog'")
    print("\nConfiguration to test Hybrid features:")
    print("  CardRecognitionService.FEATURE_TYPE = 'hybrid'")
    print("="*70)


if __name__ == "__main__":
    main()

# Screenshot Folder Preview & Manual Card Cropping - Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable users to browse saved screenshots from folder, manually crop 3 card regions via draggable boxes, and batch label them for training.

**Architecture:** Two-phase UI (browse → crop → label) in React frontend, 4 new REST endpoints in FastAPI backend. No external dependencies needed (pure React drag/drop, existing Ant Design components).

**Tech Stack:** 
- Backend: FastAPI, Python Pathlib, OpenCV, PIL
- Frontend: React 18, TypeScript, Ant Design 5, CSS Modules
- State: React useState (no Redux needed for local UI state)

**Design Reference:** `production/docs/plans/2026-03-04-screenshot-folder-preview-manual-cropping-design.md`

---

## Phase 1: Backend API Endpoints

### Task 1: List Screenshots Endpoint

**Files:**
- Modify: `production/backend/main.py` (add endpoint after line 432)
- Test manually: `curl http://localhost:8000/screenshots/list`

**Step 1: Add GET /screenshots/list endpoint**

Add after the existing `/screenshot` POST endpoint (around line 450):

```python
@app.get("/screenshots/list")
def list_screenshots():
    """List all PNG files in production/screenshot/ folder"""
    try:
        screenshot_dir = Path("production/screenshot")
        if not screenshot_dir.exists():
            return {"success": True, "files": [], "count": 0}
        
        files = sorted(
            [f.name for f in screenshot_dir.glob("*.png") if f.is_file()],
            reverse=True  # Newest first (timestamp in filename)
        )
        return {"success": True, "files": files, "count": len(files)}
    except Exception as e:
        logger.error(f"Error listing screenshots: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 2: Test endpoint manually**

```bash
# Start backend if not running
cd production/backend
python -m uvicorn main:app --reload

# In another terminal
curl http://localhost:8000/screenshots/list
```

Expected output:
```json
{
  "success": true,
  "files": ["screenshot_20260303_222948_656852.png", ...],
  "count": 6
}
```

**Step 3: Commit**

```bash
git add production/backend/main.py
git commit -m "feat(backend): add GET /screenshots/list endpoint"
```

---

### Task 2: Get Screenshot File Endpoint

**Files:**
- Modify: `production/backend/main.py` (add after `/screenshots/list`)

**Step 1: Add GET /screenshots/file/{filename} endpoint**

```python
@app.get("/screenshots/file/{filename}")
def get_screenshot_file(filename: str):
    """Return base64-encoded image for a specific screenshot file"""
    try:
        screenshot_dir = Path("production/screenshot")
        file_path = screenshot_dir / filename
        
        # Security: prevent directory traversal
        if not file_path.resolve().is_relative_to(screenshot_dir.resolve()):
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")
        
        # Load image and encode to base64
        img = Image.open(file_path)
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        return {
            "success": True,
            "image": f"data:image/png;base64,{img_str}",
            "filename": filename,
            "size": {"width": img.width, "height": img.height}
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading screenshot file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 2: Test endpoint manually**

```bash
curl http://localhost:8000/screenshots/file/screenshot_20260303_222948_656852.png | jq '.success'
# Expected: true

# Test invalid filename (should fail)
curl http://localhost:8000/screenshots/file/../backend/main.py
# Expected: 400 Bad Request
```

**Step 3: Commit**

```bash
git add production/backend/main.py
git commit -m "feat(backend): add GET /screenshots/file/{filename} endpoint with security"
```

---

### Task 3: Extract Crops Endpoint

**Files:**
- Modify: `production/backend/main.py` (add after `/screenshots/file`)

**Step 1: Add POST /screenshots/extract-crops endpoint**

```python
@app.post("/screenshots/extract-crops")
def extract_crops_from_screenshot(request: dict):
    """Extract 3 crop regions from screenshot based on box positions"""
    try:
        filename = request.get("filename")
        crops = request.get("crops")  # List of {x, y, w, h}
        
        if not filename or not crops:
            raise HTTPException(status_code=400, detail="Missing filename or crops")
        
        screenshot_dir = Path("production/screenshot")
        file_path = screenshot_dir / filename
        
        # Security check
        if not file_path.resolve().is_relative_to(screenshot_dir.resolve()):
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")
        
        # Load image as grayscale (matching card recognition workflow)
        img = cv2.imread(str(file_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise HTTPException(status_code=500, detail="Failed to load image")
        
        crop_images = []
        for idx, crop in enumerate(crops):
            x = int(crop.get("x", 0))
            y = int(crop.get("y", 0))
            w = int(crop.get("w", 70))
            h = int(crop.get("h", 90))
            
            # Validate bounds
            if x < 0 or y < 0 or x + w > img.shape[1] or y + h > img.shape[0]:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Crop {idx} out of bounds: x={x}, y={y}, w={w}, h={h}, image_size={img.shape}"
                )
            
            # Extract crop
            crop_array = img[y:y+h, x:x+w]
            
            # Encode to PNG base64
            _, buffer = cv2.imencode('.png', crop_array)
            crop_base64 = base64.b64encode(buffer).decode('utf-8')
            crop_images.append(f"data:image/png;base64,{crop_base64}")
        
        return {"success": True, "crops": crop_images}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting crops: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 2: Test endpoint manually**

```bash
# Test with valid crop positions
curl -X POST http://localhost:8000/screenshots/extract-crops \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "screenshot_20260303_222948_656852.png",
    "crops": [
      {"x": 440, "y": 560, "w": 70, "h": 90},
      {"x": 525, "y": 560, "w": 70, "h": 90},
      {"x": 610, "y": 560, "w": 70, "h": 90}
    ]
  }' | jq '.crops | length'
# Expected: 3

# Test with out-of-bounds crop (should fail)
curl -X POST http://localhost:8000/screenshots/extract-crops \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "screenshot_20260303_222948_656852.png",
    "crops": [{"x": 9999, "y": 9999, "w": 70, "h": 90}]
  }'
# Expected: 400 Bad Request with "out of bounds" message
```

**Step 3: Commit**

```bash
git add production/backend/main.py
git commit -m "feat(backend): add POST /screenshots/extract-crops endpoint with validation"
```

---

### Task 4: Save Labeled Crops Endpoint

**Files:**
- Modify: `production/backend/main.py` (add after `/screenshots/extract-crops`)

**Step 1: Add POST /screenshots/save-labeled-crops endpoint**

```python
@app.post("/screenshots/save-labeled-crops")
def save_labeled_crops_from_screenshot(request: dict):
    """Save labeled crops from screenshot to dataset and trigger training"""
    try:
        from app.services.card_dataset_service import CardDatasetService
        from app.services.card_model_service import CardModelService
        
        filename = request.get("filename")
        crops = request.get("crops")  # List of {x, y, w, h, label}
        
        if not filename or not crops:
            raise HTTPException(status_code=400, detail="Missing filename or crops")
        
        screenshot_dir = Path("production/screenshot")
        file_path = screenshot_dir / filename
        
        # Security check
        if not file_path.resolve().is_relative_to(screenshot_dir.resolve()):
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")
        
        # Load image as grayscale
        img = cv2.imread(str(file_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise HTTPException(status_code=500, detail="Failed to load image")
        
        # Initialize dataset service
        CardDatasetService.initialize()
        
        saved_cards = []
        for idx, crop_data in enumerate(crops):
            x = int(crop_data.get("x", 0))
            y = int(crop_data.get("y", 0))
            w = int(crop_data.get("w", 70))
            h = int(crop_data.get("h", 90))
            label = crop_data.get("label", "").strip()
            
            if not label:
                raise HTTPException(status_code=400, detail=f"Crop {idx} missing label")
            
            # Validate bounds
            if x < 0 or y < 0 or x + w > img.shape[1] or y + h > img.shape[0]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Crop {idx} out of bounds"
                )
            
            # Extract crop
            crop_array = img[y:y+h, x:x+w]
            
            # Generate unique crop_id
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            crop_id = f"crop_{timestamp}_{idx}_screenshot"
            
            # Save to unlabeled first (mimicking detection workflow)
            unlabeled_dir = CardDatasetService.BASE_DIR / "dataset" / "unlabeled"
            crop_path = unlabeled_dir / f"{crop_id}.png"
            cv2.imwrite(str(crop_path), crop_array)
            
            # Apply label (moves to labeled/ and trains)
            result = CardDatasetService.apply_label(crop_id, label, crop_margins=None)
            saved_cards.append(label)
        
        # Get final model status
        model_status = CardModelService.get_model_status()
        
        return {
            "success": True,
            "message": f"已保存{len(saved_cards)}个标注样本",
            "trained_cards": saved_cards,
            "total_samples": model_status.get("total_samples", 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving labeled crops: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 2: Test endpoint manually**

```bash
# Test with valid crops and labels
curl -X POST http://localhost:8000/screenshots/save-labeled-crops \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "screenshot_20260303_222948_656852.png",
    "crops": [
      {"x": 440, "y": 560, "w": 70, "h": 90, "label": "火灵"},
      {"x": 525, "y": 560, "w": 70, "h": 90, "label": "蛇女"},
      {"x": 610, "y": 560, "w": 70, "h": 90, "label": "冰女"}
    ]
  }' | jq '.message'
# Expected: "已保存3个标注样本"

# Test with missing label (should fail)
curl -X POST http://localhost:8000/screenshots/save-labeled-crops \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "screenshot_20260303_222948_656852.png",
    "crops": [{"x": 440, "y": 560, "w": 70, "h": 90, "label": ""}]
  }'
# Expected: 400 Bad Request "missing label"
```

**Step 3: Run backend type checks**

```bash
cd production/backend
python -m py_compile main.py
# Expected: No output (success)
```

**Step 4: Commit**

```bash
git add production/backend/main.py
git commit -m "feat(backend): add POST /screenshots/save-labeled-crops endpoint"
```

---

## Phase 2: Frontend API Client

### Task 5: Add API Client Methods

**Files:**
- Modify: `production/frontend/src/services/api.ts` (add new methods after line 196)
- Modify: `production/frontend/src/services/api.ts` (update API interface after line 78)

**Step 1: Add TypeScript interfaces**

Add after existing imports (around line 13):

```typescript
// Screenshot folder types
export interface ListScreenshotsResponse {
  success: boolean;
  files: string[];
  count: number;
}

export interface GetScreenshotFileResponse {
  success: boolean;
  image: string;  // Base64 data URL
  filename: string;
  size: { width: number; height: number };
}

export interface CropBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface ExtractCropsResponse {
  success: boolean;
  crops: string[];  // Array of base64 data URLs
}

export interface SaveLabeledCropsRequest {
  filename: string;
  crops: Array<CropBox & { label: string }>;
}

export interface SaveLabeledCropsResponse {
  success: boolean;
  message: string;
  trained_cards: string[];
  total_samples: number;
}
```

**Step 2: Add methods to API interface**

Add to the `API` interface (after `getCardNames` around line 77):

```typescript
export interface API {
  // ... existing methods ...
  getCardNames: () => Promise<{ cards: string[]; count: number }>;
  
  // Screenshot folder methods
  listScreenshots: () => Promise<ListScreenshotsResponse>;
  getScreenshotFile: (filename: string) => Promise<GetScreenshotFileResponse>;
  extractCrops: (filename: string, crops: CropBox[]) => Promise<ExtractCropsResponse>;
  saveLabeledCrops: (request: SaveLabeledCropsRequest) => Promise<SaveLabeledCropsResponse>;
}
```

**Step 3: Implement methods in api object**

Add after existing method implementations (after line 196):

```typescript
  // Screenshot folder methods
  listScreenshots: async () => {
    return await proxy.get('screenshots/list');
  },
  
  getScreenshotFile: async (filename: string) => {
    return await proxy.get(`screenshots/file/${encodeURIComponent(filename)}`);
  },
  
  extractCrops: async (filename: string, crops: CropBox[]) => {
    return await proxy.post('screenshots/extract-crops', { filename, crops });
  },
  
  saveLabeledCrops: async (request: SaveLabeledCropsRequest) => {
    return await proxy.post('screenshots/save-labeled-crops', request);
  },
```

**Step 4: Run frontend type check**

```bash
cd production/frontend
npm run lint
# Expected: No errors (or only pre-existing warnings)
```

**Step 5: Commit**

```bash
git add production/frontend/src/services/api.ts
git commit -m "feat(frontend): add screenshot folder API client methods"
```

---

## Phase 3: Frontend UI Components

### Task 6: Create ImageBrowser Component

**Files:**
- Create: `production/frontend/src/components/content/screenshot/components/ImageBrowser.tsx`
- Create: `production/frontend/src/components/content/screenshot/components/ImageBrowser.module.scss`

**Step 1: Create ImageBrowser component file**

```typescript
import React from 'react';
import { Select, Button, Space } from 'antd';
import { LeftOutlined, RightOutlined } from '@ant-design/icons';
import styles from './ImageBrowser.module.scss';

interface ImageBrowserProps {
  files: string[];
  selectedIndex: number;
  onSelectFile: (index: number) => void;
  onPrevious: () => void;
  onNext: () => void;
  disabled?: boolean;
}

const ImageBrowser: React.FC<ImageBrowserProps> = ({
  files,
  selectedIndex,
  onSelectFile,
  onPrevious,
  onNext,
  disabled = false
}) => {
  const handleDropdownChange = (value: string) => {
    const index = files.indexOf(value);
    if (index !== -1) {
      onSelectFile(index);
    }
  };

  return (
    <div className={styles.imageBrowser}>
      <Space direction='vertical' size='small' style={{ width: '100%' }}>
        <Select
          value={files[selectedIndex]}
          onChange={handleDropdownChange}
          style={{ width: '100%' }}
          placeholder='选择截图'
          disabled={disabled || files.length === 0}
          showSearch
          filterOption={(input, option) =>
            (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
          }
          options={files.map(file => ({ label: file, value: file }))}
        />
        <Space>
          <Button
            icon={<LeftOutlined />}
            onClick={onPrevious}
            disabled={disabled || selectedIndex === 0}
            size='small'
          >
            上一张
          </Button>
          <span className={styles.counter}>
            {files.length > 0 ? `${selectedIndex + 1} / ${files.length}` : '0 / 0'}
          </span>
          <Button
            icon={<RightOutlined />}
            onClick={onNext}
            disabled={disabled || selectedIndex >= files.length - 1}
            size='small'
          >
            下一张
          </Button>
        </Space>
      </Space>
    </div>
  );
};

export default ImageBrowser;
```

**Step 2: Create ImageBrowser styles**

```scss
.imageBrowser {
  padding: 12px 0;
  
  .counter {
    display: inline-block;
    min-width: 60px;
    text-align: center;
    color: #666;
    font-size: 14px;
  }
}
```

**Step 3: Run linter**

```bash
cd production/frontend
npm run lint
# Expected: No errors
```

**Step 4: Commit**

```bash
git add production/frontend/src/components/content/screenshot/components/
git commit -m "feat(frontend): add ImageBrowser component for screenshot navigation"
```

---

### Task 7: Create CropEditor Component

**Files:**
- Create: `production/frontend/src/components/content/screenshot/components/CropEditor.tsx`
- Create: `production/frontend/src/components/content/screenshot/components/CropEditor.module.scss`

**Step 1: Create CropEditor component file**

```typescript
import React, { useState, useRef, useEffect } from 'react';
import styles from './CropEditor.module.scss';

export interface CropBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

interface CropEditorProps {
  imageUrl: string;
  imageSize: { width: number; height: number };
  boxes: CropBox[];
  onBoxesChange: (boxes: CropBox[]) => void;
}

type DragHandle = 'body' | 'top' | 'bottom' | 'left' | 'right' | 'tl' | 'tr' | 'bl' | 'br';

const CropEditor: React.FC<CropEditorProps> = ({
  imageUrl,
  imageSize,
  boxes,
  onBoxesChange
}) => {
  const [dragging, setDragging] = useState<{ boxIndex: number; handle: DragHandle } | null>(null);
  const [dragStart, setDragStart] = useState<{ x: number; y: number; boxState: CropBox } | null>(null);
  const [scale, setScale] = useState({ scaleX: 1, scaleY: 1 });
  const containerRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  // Calculate scale when image loads
  useEffect(() => {
    if (imgRef.current) {
      const displayWidth = imgRef.current.clientWidth;
      const displayHeight = imgRef.current.clientHeight;
      setScale({
        scaleX: imageSize.width / displayWidth,
        scaleY: imageSize.height / displayHeight
      });
    }
  }, [imageUrl, imageSize]);

  const handleMouseDown = (boxIndex: number, handle: DragHandle, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragging({ boxIndex, handle });
    setDragStart({
      x: e.clientX,
      y: e.clientY,
      boxState: { ...boxes[boxIndex] }
    });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!dragging || !dragStart) return;

    const deltaX = (e.clientX - dragStart.x) * scale.scaleX;
    const deltaY = (e.clientY - dragStart.y) * scale.scaleY;

    const newBox = { ...dragStart.boxState };
    const { handle } = dragging;

    if (handle === 'body') {
      // Move entire box
      newBox.x = Math.max(0, Math.min(imageSize.width - newBox.w, dragStart.boxState.x + deltaX));
      newBox.y = Math.max(0, Math.min(imageSize.height - newBox.h, dragStart.boxState.y + deltaY));
    } else if (handle === 'top') {
      const newY = Math.max(0, dragStart.boxState.y + deltaY);
      newBox.h = Math.max(10, dragStart.boxState.h + (dragStart.boxState.y - newY));
      newBox.y = newY;
    } else if (handle === 'bottom') {
      newBox.h = Math.max(10, Math.min(imageSize.height - newBox.y, dragStart.boxState.h + deltaY));
    } else if (handle === 'left') {
      const newX = Math.max(0, dragStart.boxState.x + deltaX);
      newBox.w = Math.max(10, dragStart.boxState.w + (dragStart.boxState.x - newX));
      newBox.x = newX;
    } else if (handle === 'right') {
      newBox.w = Math.max(10, Math.min(imageSize.width - newBox.x, dragStart.boxState.w + deltaX));
    } else if (handle === 'tl') {
      const newX = Math.max(0, dragStart.boxState.x + deltaX);
      const newY = Math.max(0, dragStart.boxState.y + deltaY);
      newBox.w = Math.max(10, dragStart.boxState.w + (dragStart.boxState.x - newX));
      newBox.h = Math.max(10, dragStart.boxState.h + (dragStart.boxState.y - newY));
      newBox.x = newX;
      newBox.y = newY;
    } else if (handle === 'tr') {
      const newY = Math.max(0, dragStart.boxState.y + deltaY);
      newBox.w = Math.max(10, Math.min(imageSize.width - newBox.x, dragStart.boxState.w + deltaX));
      newBox.h = Math.max(10, dragStart.boxState.h + (dragStart.boxState.y - newY));
      newBox.y = newY;
    } else if (handle === 'bl') {
      const newX = Math.max(0, dragStart.boxState.x + deltaX);
      newBox.w = Math.max(10, dragStart.boxState.w + (dragStart.boxState.x - newX));
      newBox.h = Math.max(10, Math.min(imageSize.height - newBox.y, dragStart.boxState.h + deltaY));
      newBox.x = newX;
    } else if (handle === 'br') {
      newBox.w = Math.max(10, Math.min(imageSize.width - newBox.x, dragStart.boxState.w + deltaX));
      newBox.h = Math.max(10, Math.min(imageSize.height - newBox.y, dragStart.boxState.h + deltaY));
    }

    const newBoxes = [...boxes];
    newBoxes[dragging.boxIndex] = newBox;
    onBoxesChange(newBoxes);
  };

  const handleMouseUp = () => {
    setDragging(null);
    setDragStart(null);
  };

  const renderBox = (box: CropBox, index: number) => {
    const displayX = box.x / scale.scaleX;
    const displayY = box.y / scale.scaleY;
    const displayW = box.w / scale.scaleX;
    const displayH = box.h / scale.scaleY;

    return (
      <div key={index} className={styles.cropBox}>
        {/* Main box */}
        <div
          className={styles.boxBorder}
          style={{
            left: `${displayX}px`,
            top: `${displayY}px`,
            width: `${displayW}px`,
            height: `${displayH}px`
          }}
          onMouseDown={(e) => handleMouseDown(index, 'body', e)}
        >
          {/* Box number label */}
          <div className={styles.boxLabel}>{index + 1}</div>
          
          {/* Dimension tooltip */}
          <div className={styles.boxDimensions}>
            {Math.round(box.w)} × {Math.round(box.h)}
          </div>

          {/* Resize handles */}
          <div className={`${styles.handle} ${styles.handleTL}`} onMouseDown={(e) => handleMouseDown(index, 'tl', e)} />
          <div className={`${styles.handle} ${styles.handleTR}`} onMouseDown={(e) => handleMouseDown(index, 'tr', e)} />
          <div className={`${styles.handle} ${styles.handleBL}`} onMouseDown={(e) => handleMouseDown(index, 'bl', e)} />
          <div className={`${styles.handle} ${styles.handleBR}`} onMouseDown={(e) => handleMouseDown(index, 'br', e)} />
          <div className={`${styles.handle} ${styles.handleT}`} onMouseDown={(e) => handleMouseDown(index, 'top', e)} />
          <div className={`${styles.handle} ${styles.handleB}`} onMouseDown={(e) => handleMouseDown(index, 'bottom', e)} />
          <div className={`${styles.handle} ${styles.handleL}`} onMouseDown={(e) => handleMouseDown(index, 'left', e)} />
          <div className={`${styles.handle} ${styles.handleR}`} onMouseDown={(e) => handleMouseDown(index, 'right', e)} />
        </div>
      </div>
    );
  };

  return (
    <div
      ref={containerRef}
      className={styles.cropEditor}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {/* Dimmed background image */}
      <img
        ref={imgRef}
        src={imageUrl}
        alt='Screenshot'
        className={styles.backgroundImage}
        draggable={false}
      />

      {/* Overlay container for boxes */}
      <div className={styles.overlayContainer}>
        {boxes.map((box, index) => renderBox(box, index))}
      </div>
    </div>
  );
};

export default CropEditor;
```

**Step 2: Create CropEditor styles**

```scss
.cropEditor {
  position: relative;
  display: inline-block;
  user-select: none;
  cursor: default;

  .backgroundImage {
    display: block;
    max-width: 100%;
    max-height: 600px;
    opacity: 0.4;
    pointer-events: none;
  }

  .overlayContainer {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
  }

  .cropBox {
    position: absolute;
    pointer-events: auto;
  }

  .boxBorder {
    position: absolute;
    border: 3px solid #ff4d4f;
    box-sizing: border-box;
    cursor: move;

    .boxLabel {
      position: absolute;
      top: -24px;
      left: 0;
      background: #ff4d4f;
      color: white;
      padding: 2px 8px;
      font-size: 12px;
      font-weight: bold;
      border-radius: 4px 4px 0 0;
    }

    .boxDimensions {
      position: absolute;
      bottom: -24px;
      left: 0;
      background: rgba(0, 0, 0, 0.7);
      color: white;
      padding: 2px 8px;
      font-size: 11px;
      border-radius: 0 0 4px 4px;
      white-space: nowrap;
    }
  }

  .handle {
    position: absolute;
    background: #ff4d4f;
    border: 2px solid white;
    box-sizing: border-box;
  }

  .handleTL {
    top: -5px;
    left: -5px;
    width: 10px;
    height: 10px;
    cursor: nwse-resize;
  }

  .handleTR {
    top: -5px;
    right: -5px;
    width: 10px;
    height: 10px;
    cursor: nesw-resize;
  }

  .handleBL {
    bottom: -5px;
    left: -5px;
    width: 10px;
    height: 10px;
    cursor: nesw-resize;
  }

  .handleBR {
    bottom: -5px;
    right: -5px;
    width: 10px;
    height: 10px;
    cursor: nwse-resize;
  }

  .handleT {
    top: -5px;
    left: 50%;
    transform: translateX(-50%);
    width: 10px;
    height: 10px;
    cursor: ns-resize;
  }

  .handleB {
    bottom: -5px;
    left: 50%;
    transform: translateX(-50%);
    width: 10px;
    height: 10px;
    cursor: ns-resize;
  }

  .handleL {
    left: -5px;
    top: 50%;
    transform: translateY(-50%);
    width: 10px;
    height: 10px;
    cursor: ew-resize;
  }

  .handleR {
    right: -5px;
    top: 50%;
    transform: translateY(-50%);
    width: 10px;
    height: 10px;
    cursor: ew-resize;
  }
}
```

**Step 3: Run linter**

```bash
cd production/frontend
npm run lint
# Expected: No errors
```

**Step 4: Commit**

```bash
git add production/frontend/src/components/content/screenshot/components/
git commit -m "feat(frontend): add CropEditor component with draggable boxes"
```

---

### Task 8: Create CropLabeler Component

**Files:**
- Create: `production/frontend/src/components/content/screenshot/components/CropLabeler.tsx`
- Create: `production/frontend/src/components/content/screenshot/components/CropLabeler.module.scss`

**Step 1: Create CropLabeler component file**

```typescript
import React from 'react';
import { Select, Button, Space } from 'antd';
import styles from './CropLabeler.module.scss';

interface CropLabelerProps {
  crops: string[];  // Base64 image URLs
  labels: string[];  // Card names for each crop
  cardNames: string[];  // Available card names
  onLabelsChange: (labels: string[]) => void;
  onSave: () => void;
  onCancel: () => void;
  saving?: boolean;
}

const CropLabeler: React.FC<CropLabelerProps> = ({
  crops,
  labels,
  cardNames,
  onLabelsChange,
  onSave,
  onCancel,
  saving = false
}) => {
  const handleLabelChange = (index: number, value: string) => {
    const newLabels = [...labels];
    newLabels[index] = value;
    onLabelsChange(newLabels);
  };

  const allLabeled = labels.every(label => label.trim() !== '');

  return (
    <div className={styles.cropLabeler}>
      <div className={styles.header}>
        <h4>批量标注 ({crops.length} 张卡牌)</h4>
        <p className={styles.hint}>为每张卡牌选择名称后保存</p>
      </div>

      <div className={styles.cropsGrid}>
        {crops.map((cropUrl, index) => (
          <div key={index} className={styles.cropItem}>
            <div className={styles.cropImageContainer}>
              <img src={cropUrl} alt={`Crop ${index + 1}`} className={styles.cropImage} />
              <div className={styles.cropNumber}>{index + 1}</div>
            </div>
            <Select
              value={labels[index] || undefined}
              onChange={(value) => handleLabelChange(index, value)}
              style={{ width: '100%' }}
              placeholder='选择卡牌'
              showSearch
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
              options={cardNames.map(name => ({ label: name, value: name }))}
              status={labels[index] ? undefined : 'warning'}
            />
          </div>
        ))}
      </div>

      <div className={styles.actions}>
        <Space>
          <Button onClick={onCancel} disabled={saving}>
            取消
          </Button>
          <Button
            type='primary'
            onClick={onSave}
            disabled={!allLabeled || saving}
            loading={saving}
          >
            保存标注
          </Button>
        </Space>
        {!allLabeled && (
          <span className={styles.warning}>请为所有卡牌选择标签</span>
        )}
      </div>
    </div>
  );
};

export default CropLabeler;
```

**Step 2: Create CropLabeler styles**

```scss
.cropLabeler {
  padding: 16px;
  background: #f5f5f5;
  border-radius: 8px;
  margin-top: 16px;

  .header {
    margin-bottom: 16px;

    h4 {
      margin: 0 0 4px 0;
      font-size: 16px;
      font-weight: 600;
    }

    .hint {
      margin: 0;
      font-size: 13px;
      color: #666;
    }
  }

  .cropsGrid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin-bottom: 16px;

    .cropItem {
      display: flex;
      flex-direction: column;
      gap: 8px;

      .cropImageContainer {
        position: relative;
        background: white;
        border: 2px solid #d9d9d9;
        border-radius: 4px;
        padding: 8px;
        display: flex;
        justify-content: center;
        align-items: center;

        .cropImage {
          max-width: 100%;
          height: auto;
          display: block;
        }

        .cropNumber {
          position: absolute;
          top: 4px;
          left: 4px;
          background: #1890ff;
          color: white;
          width: 20px;
          height: 20px;
          border-radius: 50%;
          display: flex;
          justify-content: center;
          align-items: center;
          font-size: 12px;
          font-weight: bold;
        }
      }
    }
  }

  .actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 12px;
    border-top: 1px solid #d9d9d9;

    .warning {
      font-size: 13px;
      color: #faad14;
    }
  }
}
```

**Step 3: Run linter**

```bash
cd production/frontend
npm run lint
# Expected: No errors
```

**Step 4: Commit**

```bash
git add production/frontend/src/components/content/screenshot/components/
git commit -m "feat(frontend): add CropLabeler component for batch labeling"
```

---

## Phase 4: Integration with ScreenshotContent

### Task 9: Refactor ScreenshotContent - Part 1 (State & Effects)

**Files:**
- Modify: `production/frontend/src/components/content/screenshot/ScreenshotContent.tsx`

**Step 1: Add imports for new components**

Add after existing imports (around line 6):

```typescript
import ImageBrowser from './components/ImageBrowser';
import CropEditor from './components/CropEditor';
import CropLabeler from './components/CropLabeler';
import type { CropBox } from '@src/services/api';
```

**Step 2: Add new state variables**

Add after existing state declarations (around line 27):

```typescript
  // Screenshot folder browsing
  const [screenshotFiles, setScreenshotFiles] = useState<string[]>([]);
  const [selectedFileIndex, setSelectedFileIndex] = useState<number>(0);
  const [currentImageUrl, setCurrentImageUrl] = useState<string | null>(null);
  const [imageSize, setImageSize] = useState<{ width: number; height: number } | null>(null);

  // Cropping workflow
  const [cropMode, setCropMode] = useState<'browse' | 'cropping' | 'labeling'>('browse');
  const [cropBoxes, setCropBoxes] = useState<CropBox[]>([
    { x: 440, y: 560, w: 70, h: 90 },
    { x: 525, y: 560, w: 70, h: 90 },
    { x: 610, y: 560, w: 70, h: 90 }
  ]);
  const [extractedCrops, setExtractedCrops] = useState<string[]>([]);
  const [cropLabels, setCropLabels] = useState<string[]>(['', '', '']);
  const [savingLabels, setSavingLabels] = useState(false);
```

**Step 3: Add effect to load screenshot files on mount**

Add after existing `useEffect` hooks (around line 54):

```typescript
  // Load screenshot files on mount
  useEffect(() => {
    loadScreenshotFiles();
  }, []);

  const loadScreenshotFiles = async () => {
    try {
      const result = await api.listScreenshots();
      setScreenshotFiles(result.files);
      if (result.files.length > 0) {
        setSelectedFileIndex(0);
        await loadScreenshotImage(result.files[0]);
      }
    } catch (error) {
      console.error('Failed to load screenshot files:', error);
      message.error('加载截图列表失败');
    }
  };

  const loadScreenshotImage = async (filename: string) => {
    try {
      setLoading(true);
      const result = await api.getScreenshotFile(filename);
      setCurrentImageUrl(result.image);
      setImageSize(result.size);
    } catch (error) {
      console.error('Failed to load screenshot:', error);
      message.error('加载截图失败: ' + error);
    } finally {
      setLoading(false);
    }
  };
```

**Step 4: Run type check**

```bash
cd production/frontend
npm run lint
# Expected: No errors (incomplete implementation warnings OK)
```

**Step 5: Commit**

```bash
git add production/frontend/src/components/content/screenshot/ScreenshotContent.tsx
git commit -m "feat(frontend): add screenshot folder state and loading logic"
```

---

### Task 10: Refactor ScreenshotContent - Part 2 (Handlers)

**Files:**
- Modify: `production/frontend/src/components/content/screenshot/ScreenshotContent.tsx`

**Step 1: Add navigation handlers**

Add after `loadScreenshotImage` function (around line 90):

```typescript
  const handleSelectFile = async (index: number) => {
    setSelectedFileIndex(index);
    await loadScreenshotImage(screenshotFiles[index]);
    // Reset crop mode when switching images
    setCropMode('browse');
    setExtractedCrops([]);
    setCropLabels(['', '', '']);
  };

  const handlePrevious = () => {
    if (selectedFileIndex > 0) {
      handleSelectFile(selectedFileIndex - 1);
    }
  };

  const handleNext = () => {
    if (selectedFileIndex < screenshotFiles.length - 1) {
      handleSelectFile(selectedFileIndex + 1);
    }
  };
```

**Step 2: Add cropping workflow handlers**

Add after navigation handlers:

```typescript
  const handleStartLabeling = () => {
    setCropMode('cropping');
    // Reset boxes to default positions
    setCropBoxes([
      { x: 440, y: 560, w: 70, h: 90 },
      { x: 525, y: 560, w: 70, h: 90 },
      { x: 610, y: 560, w: 70, h: 90 }
    ]);
  };

  const handleFinishCropping = async () => {
    if (!screenshotFiles[selectedFileIndex]) {
      message.error('未选择截图');
      return;
    }

    try {
      setLoading(true);
      const result = await api.extractCrops(screenshotFiles[selectedFileIndex], cropBoxes);
      setExtractedCrops(result.crops);
      setCropLabels(['', '', '']);
      setCropMode('labeling');
      message.success('裁切完成，请标注卡牌');
    } catch (error) {
      console.error('Failed to extract crops:', error);
      message.error('裁切失败: ' + error);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveLabels = async () => {
    if (!screenshotFiles[selectedFileIndex]) {
      message.error('未选择截图');
      return;
    }

    if (cropLabels.some(label => !label.trim())) {
      message.warning('请为所有卡牌选择标签');
      return;
    }

    try {
      setSavingLabels(true);
      const cropsWithLabels = cropBoxes.map((box, idx) => ({
        ...box,
        label: cropLabels[idx]
      }));

      const result = await api.saveLabeledCrops({
        filename: screenshotFiles[selectedFileIndex],
        crops: cropsWithLabels
      });

      message.success(result.message);

      // Refresh model status
      const status = await api.getModelStatus();
      setModelStatus(status);

      // Reset to browse mode
      setCropMode('browse');
      setExtractedCrops([]);
      setCropLabels(['', '', '']);
    } catch (error) {
      console.error('Failed to save labels:', error);
      message.error('保存标注失败: ' + error);
    } finally {
      setSavingLabels(false);
    }
  };

  const handleCancelLabeling = () => {
    setCropMode('browse');
    setExtractedCrops([]);
    setCropLabels(['', '', '']);
  };

  const handleRecrop = () => {
    setCropMode('cropping');
    setExtractedCrops([]);
  };
```

**Step 3: Modify existing handleCapture to reload file list**

Find the existing `handleCapture` function (around line 56) and modify it:

```typescript
  const handleCapture = async () => {
    if (!activeWindow) {
      message.error('请先选择一个游戏窗口');
      return;
    }

    setLoading(true);
    try {
      const pid = parseInt(activeWindow, 10);
      const result = await api.captureScreenshot(pid);
      if (result.success) {
        message.success('截图已保存到文件夹');

        // Reload file list
        await loadScreenshotFiles();

        // Auto-select the newly captured file
        const newIndex = screenshotFiles.findIndex(f => f === result.filename);
        if (newIndex !== -1) {
          await handleSelectFile(newIndex);
        } else {
          // If not found, it's the newest (index 0)
          await handleSelectFile(0);
        }
      } else {
        message.error(result.message || '截图失败');
      }
    } catch (error) {
      console.error('Screenshot error:', error);
      message.error('截图发生错误');
    } finally {
      setLoading(false);
    }
  };
```

**Step 4: Run type check**

```bash
cd production/frontend
npm run lint
# Expected: No errors
```

**Step 5: Commit**

```bash
git add production/frontend/src/components/content/screenshot/ScreenshotContent.tsx
git commit -m "feat(frontend): add screenshot cropping and labeling handlers"
```

---

### Task 11: Refactor ScreenshotContent - Part 3 (JSX)

**Files:**
- Modify: `production/frontend/src/components/content/screenshot/ScreenshotContent.tsx`

**Step 1: Replace image preview section JSX**

Find the existing `imagePreview` div (around line 310) and replace with:

```tsx
        <div className={styles.imagePreview}>
          {/* Screenshot file browser */}
          <ImageBrowser
            files={screenshotFiles}
            selectedIndex={selectedFileIndex}
            onSelectFile={handleSelectFile}
            onPrevious={handlePrevious}
            onNext={handleNext}
            disabled={loading || cropMode !== 'browse'}
          />

          {/* Image preview with optional crop editor */}
          <div className={styles.previewContainer}>
            {loading ? (
              <Spin tip='正在加载...' />
            ) : currentImageUrl && imageSize ? (
              <>
                {cropMode === 'cropping' ? (
                  <CropEditor
                    imageUrl={currentImageUrl}
                    imageSize={imageSize}
                    boxes={cropBoxes}
                    onBoxesChange={setCropBoxes}
                  />
                ) : (
                  <Image
                    src={currentImageUrl}
                    alt='Screenshot'
                    style={{ maxWidth: '100%', maxHeight: '600px', objectFit: 'contain' }}
                  />
                )}
              </>
            ) : (
              <Empty description='暂无截图，请先捕获截图' />
            )}
          </div>

          {/* Crop mode actions */}
          {currentImageUrl && cropMode === 'browse' && (
            <div style={{ marginTop: '12px', textAlign: 'center' }}>
              <Button type='primary' onClick={handleStartLabeling}>
                开始标注
              </Button>
            </div>
          )}
          {cropMode === 'cropping' && (
            <div style={{ marginTop: '12px', textAlign: 'center' }}>
              <Button type='primary' onClick={handleFinishCropping} loading={loading}>
                完成裁切
              </Button>
            </div>
          )}

          {/* Crop labeling section */}
          {cropMode === 'labeling' && extractedCrops.length > 0 && (
            <CropLabeler
              crops={extractedCrops}
              labels={cropLabels}
              cardNames={cardNames}
              onLabelsChange={setCropLabels}
              onSave={handleSaveLabels}
              onCancel={handleCancelLabeling}
              saving={savingLabels}
            />
          )}
        </div>
```

**Step 2: Add previewContainer style to SCSS**

Open `ScreenshotContent.module.scss` and add:

```scss
  .previewContainer {
    margin: 12px 0;
    text-align: center;
    min-height: 400px;
    display: flex;
    justify-content: center;
    align-items: center;
  }
```

**Step 3: Run frontend build to test**

```bash
cd production/frontend
npm run build
# Expected: Build succeeds with no errors
```

**Step 4: Commit**

```bash
git add production/frontend/src/components/content/screenshot/
git commit -m "feat(frontend): integrate new components into ScreenshotContent"
```

---

## Phase 5: Testing & Refinement

### Task 12: Manual Integration Testing

**Files:**
- No code changes, testing only

**Step 1: Start backend and frontend**

```bash
# Terminal 1: Backend
cd production/backend
source venv/Scripts/activate  # or venv/bin/activate on Linux/Mac
python -m uvicorn main:app --reload

# Terminal 2: Frontend
cd production/frontend
npm run dev
```

**Step 2: Test screenshot folder loading**

1. Open http://localhost:5173 (or your dev server URL)
2. Navigate to Screenshot tab
3. Verify dropdown shows existing screenshots
4. Verify "0 / 6" counter if 6 files exist
5. Use Previous/Next buttons → verify image changes
6. Use dropdown → verify image changes

**Step 3: Test live capture integration**

1. Select a game window
2. Click "捕获截图"
3. Verify success message
4. Verify dropdown updates with new file
5. Verify new file is auto-selected and displayed

**Step 4: Test crop mode**

1. Click "开始标注"
2. Verify 3 red boxes appear
3. Drag a box → verify movement
4. Resize a box via handle → verify resizing
5. Verify boxes stay within image bounds
6. Click "完成裁切"
7. Verify 3 crops appear below

**Step 5: Test labeling**

1. Select card name for each crop
2. Verify "保存标注" stays disabled until all 3 labeled
3. Label all 3 crops
4. Click "保存标注"
5. Verify success message
6. Verify returns to browse mode

**Step 6: Test error cases**

1. Empty screenshot folder → verify empty state
2. Navigate to different file during crop mode → verify mode resets
3. Try to crop with boxes out of bounds → verify error message

**Step 7: Document any bugs found**

Create a file `TESTING_NOTES.md`:

```markdown
# Screenshot Folder Testing Notes

## Bugs Found
- [List any bugs discovered]

## Edge Cases
- [List edge cases tested]

## Browser Compatibility
- Chrome: [Pass/Fail]
- Firefox: [Pass/Fail]
- Edge: [Pass/Fail]
```

**Step 8: Commit testing notes if any issues found**

```bash
git add TESTING_NOTES.md
git commit -m "test: document screenshot folder feature testing results"
```

---

### Task 13: Fix Keyboard Navigation (Optional Enhancement)

**Files:**
- Modify: `production/frontend/src/components/content/screenshot/ScreenshotContent.tsx`

**Step 1: Add keyboard event listener**

Add after existing `useEffect` hooks:

```typescript
  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only handle if in browse mode and not typing in input
      if (cropMode !== 'browse') return;
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        handlePrevious();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        handleNext();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [cropMode, selectedFileIndex, screenshotFiles]);
```

**Step 2: Test keyboard navigation**

1. Navigate to Screenshot tab
2. Press Left Arrow → verify goes to previous image
3. Press Right Arrow → verify goes to next image
4. Enter crop mode → verify arrows don't navigate (as expected)

**Step 3: Commit**

```bash
git add production/frontend/src/components/content/screenshot/ScreenshotContent.tsx
git commit -m "feat(frontend): add keyboard navigation for screenshot browsing"
```

---

### Task 14: Update Documentation

**Files:**
- Modify: `production/frontend/src/components/content/AGENTS.md`
- Modify: `production/backend/app/services/AGENTS.md`

**Step 1: Update frontend AGENTS.md**

Add to the "Component Pattern" section:

```markdown
## Screenshot Folder Feature

New sub-components in `screenshot/components/`:

- `ImageBrowser.tsx` - Dropdown + prev/next navigation for screenshot files
- `CropEditor.tsx` - Interactive draggable/resizable boxes for manual cropping
- `CropLabeler.tsx` - Batch labeling UI for extracted crops

**Workflow:**
1. Browse screenshots from folder (dropdown or arrows)
2. Click "开始标注" → enter crop mode with 3 draggable boxes
3. Adjust boxes to fit actual card positions
4. Click "完成裁切" → extract 3 crops
5. Select card name for each crop → save labels → triggers training

**State Management:**
Local component state only (no Redux) - workflow is transient UI state.
```

**Step 2: Update backend AGENTS.md**

Add to the "Files" table:

```markdown
| `screenshot_service.py` | Screenshot capture, folder browsing, crop extraction |
```

Add to "Key Integrations":

```markdown
- `screenshot_service` → `card_dataset_service` (crop extraction + labeling)
```

**Step 3: Commit**

```bash
git add production/frontend/src/components/content/AGENTS.md production/backend/app/services/AGENTS.md
git commit -m "docs: update AGENTS.md with screenshot folder feature"
```

---

### Task 15: Final Verification & Cleanup

**Files:**
- Various (final checks)

**Step 1: Run full linter on frontend**

```bash
cd production/frontend
npm run lint
npm run format
# Expected: No errors, auto-formatted
```

**Step 2: Run type check on backend**

```bash
cd production/backend
python -m py_compile main.py
python -m py_compile app/services/screenshot_service.py
# Expected: No errors
```

**Step 3: Check for console warnings**

1. Open browser DevTools
2. Navigate through Screenshot tab workflow
3. Verify no console errors or warnings

**Step 4: Run production build test**

```bash
cd production/frontend
npm run build
# Expected: Build succeeds, no errors
```

**Step 5: Final commit**

```bash
git add -A
git commit -m "chore: final cleanup and formatting for screenshot folder feature"
```

---

## Completion Checklist

- [ ] All 4 backend API endpoints implemented and tested
- [ ] All 3 frontend components created (ImageBrowser, CropEditor, CropLabeler)
- [ ] ScreenshotContent refactored and integrated
- [ ] Manual testing completed for all workflows
- [ ] Documentation updated (AGENTS.md)
- [ ] No linter errors in frontend
- [ ] No type errors in backend
- [ ] Keyboard navigation working (optional)
- [ ] Production build succeeds

---

## Rollback Plan

If issues arise:

```bash
# Revert all changes
git log --oneline  # Find commit before "feat(backend): add GET /screenshots/list"
git reset --hard <commit-hash>

# Or revert specific commits
git revert <commit-hash>
```

Disable feature flag (if added):

```python
# In main.py
ENABLE_SCREENSHOT_FOLDER = False

@app.get("/screenshots/list")
def list_screenshots():
    if not ENABLE_SCREENSHOT_FOLDER:
        raise HTTPException(status_code=501, detail="Feature disabled")
    # ... rest of implementation
```

---

## Next Steps After Completion

1. **User feedback** - Gather feedback on cropping accuracy and workflow speed
2. **Performance optimization** - Profile large screenshot folders (100+ files)
3. **Batch operations** - Allow labeling multiple screenshots in one session
4. **Auto-detection preview** - Show detected positions as overlay to assist manual adjustment
5. **Crop history** - Save crop positions per screenshot in localStorage for repeat visits

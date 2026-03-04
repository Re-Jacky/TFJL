# Screenshot Folder Preview & Manual Card Cropping - Design Document

**Date:** 2026-03-04  
**Author:** AI Assistant (Claude Sonnet 4.5)  
**Status:** Approved  

## Problem Statement

Current card recognition workflow has two issues:

1. **No screenshot folder browsing** - Can only capture live windows, cannot review/label previously saved screenshots in `production/screenshot/`
2. **Inaccurate auto-detection** - Fixed card positions (y=560, x=[440, 525, 610]) don't match actual card locations, leading to poor recognition accuracy

## Requirements

Based on user feedback:

- Load and preview existing images from `production/screenshot/` folder
- Support both dropdown selector AND previous/next navigation for browsing screenshots
- Directly crop 3 card regions by dragging/resizing boxes on the preview image
- Batch label all 3 crops after positioning (not inline during cropping)
- Live capture should save to folder first, then user selects from folder to crop/label

## Solution Design

### Approach: Two-Phase UI

**Phase 1 - Capture & Browse:**
- Live capture button → saves to `production/screenshot/` → auto-loads that image
- Dropdown selector shows all screenshot filenames (sorted newest first)
- Previous/Next arrow buttons navigate between screenshots
- Full-size preview of selected screenshot

**Phase 2 - Crop & Label:**
- Click "开始标注" (Start Labeling) → enters crop mode
- 3 draggable/resizable red boxes overlay the preview at smart default positions
- User adjusts boxes to fit actual card locations
- Click "完成裁切" (Finish Cropping) → shows 3 crops side-by-side
- Dropdown selector under each crop for card name
- Click "保存标注" (Save Labels) → saves to dataset and triggers training

---

## UI Layout

```
┌─────────────────────────────────────────────────────────┐
│ [捕获截图] Button (saves to folder)                      │
├─────────────────────────────────────────────────────────┤
│ Image Selection:                                        │
│ [Dropdown: screenshot_20260303_222120_198568.png ▼]    │
│ [◀ 上一张] [下一张 ▶]                                    │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────┐   │
│ │                                                 │   │
│ │          Image Preview Area                     │   │
│ │      (shows selected screenshot)                │   │
│ │                                                 │   │
│ │  [When in crop mode: 3 draggable red boxes]    │   │
│ │                                                 │   │
│ └─────────────────────────────────────────────────┘   │
│                                                         │
│ [开始标注] or [完成裁切] or [重新裁切] (state-dependent)   │
├─────────────────────────────────────────────────────────┤
│ Crop Preview Section (appears after cropping):          │
│ ┌────────┐  ┌────────┐  ┌────────┐                    │
│ │ Crop 1 │  │ Crop 2 │  │ Crop 3 │                    │
│ └────────┘  └────────┘  └────────┘                    │
│ [Dropdown]  [Dropdown]  [Dropdown]                     │
│           [保存标注] Button                              │
└─────────────────────────────────────────────────────────┘
```

---

## Component State

### New State Variables

```typescript
// Screenshot folder browsing
const [screenshotFiles, setScreenshotFiles] = useState<string[]>([]);
const [selectedFileIndex, setSelectedFileIndex] = useState<number>(0);
const [currentImageUrl, setCurrentImageUrl] = useState<string | null>(null);

// Cropping workflow
const [cropMode, setCropMode] = useState<'browse' | 'cropping' | 'labeling'>('browse');
const [cropBoxes, setCropBoxes] = useState<Array<{x: number, y: number, w: number, h: number}>>([
  {x: 440, y: 560, w: 70, h: 90},  // Default slot 1
  {x: 525, y: 560, w: 70, h: 90},  // Default slot 2
  {x: 610, y: 560, w: 70, h: 90}   // Default slot 3
]);
const [extractedCrops, setExtractedCrops] = useState<Array<{image: string, label: string}> | null>(null);

// Drag state for box interaction
const [dragging, setDragging] = useState<{boxIndex: number, handle: string | 'body'} | null>(null);
const [dragStart, setDragStart] = useState<{x: number, y: number, boxState: any} | null>(null);

// Image scale (for coordinate conversion)
const [imageScale, setImageScale] = useState<{scaleX: number, scaleY: number}>({scaleX: 1, scaleY: 1});
```

### State Transitions

```
browse → cropping (click "开始标注")
cropping → labeling (click "完成裁切")
labeling → browse (click "保存标注" or "取消")
labeling → cropping (click "重新裁切")
```

---

## Backend API

### New Endpoints

#### 1. GET /screenshots/list

Returns all screenshot filenames from `production/screenshot/` folder.

**Response:**
```json
{
  "success": true,
  "files": [
    "screenshot_20260303_222948_656852.png",
    "screenshot_20260303_222858_656852.png",
    "screenshot_20260303_222850_656852.png"
  ],
  "count": 3
}
```

**Implementation:**
```python
@app.get("/screenshots/list")
def list_screenshots():
    screenshot_dir = Path("production/screenshot")
    files = sorted(
        [f.name for f in screenshot_dir.glob("*.png")],
        reverse=True  # Newest first
    )
    return {"success": True, "files": files, "count": len(files)}
```

---

#### 2. GET /screenshots/file/{filename}

Returns base64-encoded image data for a specific screenshot file.

**Response:**
```json
{
  "success": true,
  "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "filename": "screenshot_20260303_222948_656852.png",
  "size": {"width": 1056, "height": 637}
}
```

**Implementation:**
```python
@app.get("/screenshots/file/{filename}")
def get_screenshot_file(filename: str):
    screenshot_dir = Path("production/screenshot")
    file_path = screenshot_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
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
```

---

#### 3. POST /screenshots/extract-crops

Receives filename + 3 crop boxes, returns 3 base64-encoded crop images.

**Request:**
```json
{
  "filename": "screenshot_20260303_222948_656852.png",
  "crops": [
    {"x": 445, "y": 562, "w": 68, "h": 88},
    {"x": 528, "y": 561, "w": 70, "h": 90},
    {"x": 612, "y": 560, "w": 69, "h": 89}
  ]
}
```

**Response:**
```json
{
  "success": true,
  "crops": [
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
  ]
}
```

**Implementation:**
```python
@app.post("/screenshots/extract-crops")
def extract_crops_from_screenshot(request: dict):
    filename = request["filename"]
    crops = request["crops"]
    
    screenshot_dir = Path("production/screenshot")
    file_path = screenshot_dir / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Load image as grayscale (matching card recognition workflow)
    img = cv2.imread(str(file_path), cv2.IMREAD_GRAYSCALE)
    
    crop_images = []
    for crop in crops:
        x, y, w, h = crop["x"], crop["y"], crop["w"], crop["h"]
        
        # Extract crop
        crop_array = img[y:y+h, x:x+w]
        
        # Convert to PNG base64
        _, buffer = cv2.imencode('.png', crop_array)
        crop_base64 = base64.b64encode(buffer).decode('utf-8')
        crop_images.append(f"data:image/png;base64,{crop_base64}")
    
    return {"success": True, "crops": crop_images}
```

---

#### 4. POST /screenshots/save-labeled-crops

Saves crops to dataset and triggers training (alternative to using existing `/cards/label-crop`).

**Request:**
```json
{
  "filename": "screenshot_20260303_222948_656852.png",
  "crops": [
    {"x": 445, "y": 562, "w": 68, "h": 88, "label": "火灵"},
    {"x": 528, "y": 561, "w": 70, "h": 90, "label": "蛇女"},
    {"x": 612, "y": 560, "w": 69, "h": 89, "label": "冰女"}
  ]
}
```

**Response:**
```json
{
  "success": true,
  "message": "已保存3个标注样本",
  "trained_cards": ["火灵", "蛇女", "冰女"],
  "total_samples": 156
}
```

**Implementation:**
Uses `CardDatasetService.apply_label()` internally for each crop.

---

#### 5. Modify POST /screenshot

Ensure existing capture endpoint returns filename so frontend can auto-select it.

**Current Response:**
```json
{
  "success": true,
  "image": "data:image/png;base64,...",
  "file_path": "/path/to/screenshot_20260303_222948_656852.png",
  "filename": "screenshot_20260303_222948_656852.png",
  "message": "Screenshot captured and saved successfully"
}
```

**No changes needed** - already returns `filename`.

---

## Frontend Implementation

### File Structure

```
screenshot/
├── ScreenshotContent.tsx          # Main component (refactor existing)
├── ScreenshotContent.module.scss  # Styles
├── components/
│   ├── ImageBrowser.tsx           # Dropdown + Prev/Next navigation
│   ├── CropEditor.tsx             # Draggable boxes overlay
│   └── CropLabeler.tsx            # Batch labeling UI (3 crops + dropdowns)
└── types.ts                       # TypeScript interfaces
```

### Component Breakdown

#### ImageBrowser.tsx

**Props:**
```typescript
interface ImageBrowserProps {
  files: string[];
  selectedIndex: number;
  currentImage: string | null;
  onSelectFile: (index: number) => void;
  onPrevious: () => void;
  onNext: () => void;
}
```

**UI:**
- Dropdown selector (Ant Design `Select`)
- Previous/Next buttons (Ant Design `Button` with icons)
- File count indicator: "图片 3/6"

---

#### CropEditor.tsx

**Props:**
```typescript
interface CropEditorProps {
  imageUrl: string;
  imageSize: {width: number, height: number};
  boxes: Array<{x: number, y: number, w: number, h: number}>;
  onBoxesChange: (boxes: Array<{x: number, y: number, w: number, h: number}>) => void;
}
```

**UI:**
- Image with semi-transparent overlay (opacity: 0.3)
- 3 draggable/resizable boxes (red border, 3px width)
- Each box has 8 resize handles (corners + midpoints)
- Tooltip showing current dimensions while dragging
- Boxes bounded to image dimensions

**Interaction:**
- Mouse down on box body → drag to move
- Mouse down on handle → drag to resize
- Calculate scale factor from displayed size vs actual size
- Convert mouse coordinates to image coordinates

---

#### CropLabeler.tsx

**Props:**
```typescript
interface CropLabelerProps {
  crops: string[];  // Base64 image URLs
  cardNames: string[];
  onLabelsChange: (labels: string[]) => void;
  onSave: () => void;
  onCancel: () => void;
}
```

**UI:**
- Grid layout: 3 columns
- Each column: crop image + dropdown selector
- "保存标注" button (enabled only when all 3 labels selected)
- "取消" or "重新裁切" button

---

### Main Component Logic (ScreenshotContent.tsx)

#### On Mount

```typescript
useEffect(() => {
  loadScreenshotFiles();
  loadCardNames();
}, []);

const loadScreenshotFiles = async () => {
  const result = await api.listScreenshots();
  setScreenshotFiles(result.files);
  if (result.files.length > 0) {
    setSelectedFileIndex(0);
    loadScreenshotImage(result.files[0]);
  }
};

const loadScreenshotImage = async (filename: string) => {
  const result = await api.getScreenshotFile(filename);
  setCurrentImageUrl(result.image);
  setImageScale({
    scaleX: result.size.width / displayedWidth,
    scaleY: result.size.height / displayedHeight
  });
};
```

---

#### Workflow Handlers

```typescript
// Enter crop mode
const handleStartLabeling = () => {
  setCropMode('cropping');
  // Reset boxes to default positions
  setCropBoxes([
    {x: 440, y: 560, w: 70, h: 90},
    {x: 525, y: 560, w: 70, h: 90},
    {x: 610, y: 560, w: 70, h: 90}
  ]);
};

// Finish cropping, extract crops
const handleFinishCropping = async () => {
  const result = await api.extractCrops(
    screenshotFiles[selectedFileIndex],
    cropBoxes
  );
  setExtractedCrops(result.crops.map(img => ({image: img, label: ''})));
  setCropMode('labeling');
};

// Save labels to dataset
const handleSaveLabels = async () => {
  const filename = screenshotFiles[selectedFileIndex];
  const cropsWithLabels = extractedCrops.map((crop, idx) => ({
    ...cropBoxes[idx],
    label: crop.label
  }));
  
  await api.saveLabeledCrops(filename, cropsWithLabels);
  message.success('已保存标注并触发训练');
  
  // Reset to browse mode
  setCropMode('browse');
  setExtractedCrops(null);
};

// Cancel labeling
const handleCancelLabeling = () => {
  setCropMode('browse');
  setExtractedCrops(null);
};

// Re-crop from labeling mode
const handleRecrop = () => {
  setCropMode('cropping');
  setExtractedCrops(null);
};
```

---

#### Navigation Handlers

```typescript
const handleSelectFile = (index: number) => {
  setSelectedFileIndex(index);
  loadScreenshotImage(screenshotFiles[index]);
  // Reset crop mode when switching images
  setCropMode('browse');
  setExtractedCrops(null);
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

---

#### Modified Capture Handler

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
        handleSelectFile(newIndex);
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

---

## Cropping Interaction Details

### Box Rendering

Each box rendered as absolutely-positioned `div` with:
- Border: 3px solid #ff4d4f (Ant Design red-5)
- Background: transparent
- Position calculated from image scale: `left = (box.x / imageScale.scaleX)px`

### Resize Handles

8 handles per box at:
- Corners: top-left, top-right, bottom-left, bottom-right
- Midpoints: top, bottom, left, right

Each handle:
- 10×10px square
- Background: #ff4d4f
- Border: 2px solid white (for contrast)
- Cursor: `nwse-resize`, `nesw-resize`, `ns-resize`, `ew-resize`

### Drag Logic

```typescript
const handleBoxMouseDown = (boxIndex: number, handle: string | 'body', e: React.MouseEvent) => {
  e.preventDefault();
  setDragging({boxIndex, handle});
  setDragStart({
    x: e.clientX,
    y: e.clientY,
    boxState: {...cropBoxes[boxIndex]}
  });
};

const handleMouseMove = (e: React.MouseEvent) => {
  if (!dragging || !dragStart) return;

  const deltaX = (e.clientX - dragStart.x) * imageScale.scaleX;
  const deltaY = (e.clientY - dragStart.y) * imageScale.scaleY;

  const newBox = {...dragStart.boxState};

  if (dragging.handle === 'body') {
    // Move entire box
    newBox.x = Math.max(0, Math.min(imageSize.width - newBox.w, dragStart.boxState.x + deltaX));
    newBox.y = Math.max(0, Math.min(imageSize.height - newBox.h, dragStart.boxState.y + deltaY));
  } else if (dragging.handle === 'top') {
    // Resize from top edge
    const newY = Math.max(0, dragStart.boxState.y + deltaY);
    newBox.h = dragStart.boxState.h + (dragStart.boxState.y - newY);
    newBox.y = newY;
  } else if (dragging.handle === 'bottom') {
    // Resize from bottom edge
    newBox.h = Math.min(imageSize.height - newBox.y, dragStart.boxState.h + deltaY);
  }
  // ... similar for left, right, corners

  // Update box in state
  const newBoxes = [...cropBoxes];
  newBoxes[dragging.boxIndex] = newBox;
  setCropBoxes(newBoxes);
};

const handleMouseUp = () => {
  setDragging(null);
  setDragStart(null);
};
```

---

## Data Flow

### Capture → Label Flow

```
1. User clicks "捕获截图"
   ↓
2. POST /screenshot → saves to production/screenshot/
   ↓
3. Frontend reloads file list via GET /screenshots/list
   ↓
4. Auto-selects new file, loads via GET /screenshots/file/{filename}
   ↓
5. User clicks "开始标注" → enters crop mode
   ↓
6. User adjusts 3 boxes to fit cards
   ↓
7. User clicks "完成裁切"
   ↓
8. POST /screenshots/extract-crops → returns 3 base64 crops
   ↓
9. Frontend shows 3 crops with dropdown selectors
   ↓
10. User selects card name for each crop
    ↓
11. User clicks "保存标注"
    ↓
12. POST /screenshots/save-labeled-crops → saves to dataset, triggers training
    ↓
13. Success message, returns to browse mode
```

### Browse → Label Flow

```
1. User selects screenshot from dropdown or uses Prev/Next
   ↓
2. GET /screenshots/file/{filename} → loads image
   ↓
3. User clicks "开始标注" → same as step 5 above
```

---

## Edge Cases & Error Handling

### No Screenshots in Folder

- Show empty state: "暂无截图，请先捕获截图"
- Disable dropdown, Prev/Next buttons, "开始标注" button

### Image Load Failure

- Show error message: "加载图片失败: {filename}"
- Keep previous image displayed
- Allow user to navigate to different file

### Crop Extraction Failure

- Show error modal: "裁切失败，请检查裁切区域是否在图片范围内"
- Stay in crop mode, allow user to adjust boxes

### Label Save Failure

- Show error message with reason
- Stay in labeling mode, preserve labels
- Allow user to retry or cancel

### Box Out of Bounds

- Prevent dragging/resizing beyond image boundaries
- Clamp box positions/sizes during drag

### Incomplete Labels

- Disable "保存标注" button until all 3 dropdowns have selections
- Show tooltip: "请为所有卡牌选择标签"

---

## Testing Plan

### Manual Testing

1. **Capture Flow**
   - Capture screenshot → verify saved to folder
   - Verify auto-selection of new file
   - Verify image displays correctly

2. **Browse Flow**
   - Use dropdown to select different screenshots → verify image loads
   - Use Prev/Next buttons → verify navigation works
   - Try navigating at list boundaries (first/last) → buttons disabled

3. **Crop Flow**
   - Click "开始标注" → verify boxes appear at default positions
   - Drag box bodies → verify movement constrained to image
   - Resize boxes via handles → verify size changes correctly
   - Click "完成裁切" → verify crops extracted and displayed

4. **Label Flow**
   - Select card names for all 3 crops → verify "保存标注" enables
   - Leave one crop unlabeled → verify button stays disabled
   - Click "保存标注" → verify success message and return to browse mode

5. **Edge Cases**
   - Empty screenshot folder → verify empty state
   - Navigate while in crop mode → verify mode resets
   - Close browser and reopen → verify state doesn't persist (expected)

### Integration Testing

1. **Backend API**
   - `GET /screenshots/list` → verify returns all PNG files sorted
   - `GET /screenshots/file/{filename}` → verify base64 encoding correct
   - `POST /screenshots/extract-crops` → verify crops match box positions
   - `POST /screenshots/save-labeled-crops` → verify saves to dataset

2. **End-to-End**
   - Capture → Browse → Crop → Label → Train → Detect
   - Verify labeled cards appear in model
   - Verify detection uses new crops

---

## Migration & Rollout

### Phase 1: Backend API (Day 1)

- Add 3 new endpoints to `main.py`
- Add helper methods to `ScreenshotService` if needed
- Test endpoints via Postman/curl

### Phase 2: Frontend Components (Day 2-3)

- Extract `ImageBrowser` component
- Build `CropEditor` component with drag/resize
- Build `CropLabeler` component
- Add API client methods to `api.ts`

### Phase 3: Integration (Day 4)

- Refactor `ScreenshotContent.tsx` to use new components
- Wire up state management and handlers
- Test complete workflow

### Phase 4: Polish (Day 5)

- Add keyboard shortcuts (Left/Right arrows)
- Add loading indicators
- Improve error messages
- Add tooltips and help text

### Phase 5: Documentation (Day 6)

- Update `AGENTS.md` with new workflow
- Add inline code comments
- Update user guide (if exists)

---

## Future Enhancements

### Short-term

1. **Batch Labeling Multiple Screenshots**
   - Select multiple screenshots → extract all crops → label in bulk

2. **Copy Box Positions**
   - "Use same positions for next image" button
   - Useful when labeling similar screenshots

3. **Keyboard Shortcuts**
   - `Space` to toggle crop mode
   - `Enter` to confirm crops
   - `Esc` to cancel
   - Arrow keys to navigate files (already mentioned)

### Long-term

1. **Auto-Detection Preview**
   - Show detected card positions as overlay in browse mode
   - Click to accept or adjust

2. **Crop History**
   - Store crop positions per screenshot in localStorage
   - Reload positions when returning to same screenshot

3. **Export/Import Annotations**
   - Export all labeled crops as JSON
   - Import annotations from another user

4. **Multi-Card Support**
   - Handle screenshots with 1-5 cards (not always 3)
   - Add/remove boxes dynamically

---

## Alternatives Considered

### Alternative 1: Always-On Crop Mode

**Pros:** No mode switching, faster workflow  
**Cons:** Visual clutter, boxes obscure image  
**Decision:** Rejected - browsing and cropping are separate mental tasks, mode separation improves UX

### Alternative 2: Canvas-Based Freeform

**Pros:** Maximum flexibility, handle any card layout  
**Cons:** Overkill for fixed 3-card layout, requires canvas library, more complex  
**Decision:** Rejected - current design handles 99% of use cases with simpler implementation

### Alternative 3: Inline Labeling During Crop

**Pros:** Faster workflow (no separate labeling step)  
**Cons:** Cluttered UI, hard to compare all 3 crops before committing  
**Decision:** Rejected - batch labeling allows reviewing all crops before saving

---

## Success Metrics

### User-facing

- Time to label 10 screenshots: Target < 5 minutes (vs manual file opening)
- Crop accuracy: Target > 95% (boxes fit actual cards)
- User satisfaction: "Easier to label cards now" feedback

### Technical

- API response time: `GET /screenshots/file` < 200ms, `POST /screenshots/extract-crops` < 500ms
- No UI lag during box dragging (60fps)
- Zero data loss (all labels saved successfully)

---

## Appendix: TypeScript Interfaces

```typescript
// Screenshot folder browsing
interface ScreenshotFile {
  filename: string;
  timestamp: string;  // Parsed from filename
}

// Crop box
interface CropBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

// Extracted crop with label
interface LabeledCrop {
  image: string;  // Base64 data URL
  label: string;  // Card name
}

// API responses
interface ListScreenshotsResponse {
  success: boolean;
  files: string[];
  count: number;
}

interface GetScreenshotFileResponse {
  success: boolean;
  image: string;  // Base64 data URL
  filename: string;
  size: {width: number, height: number};
}

interface ExtractCropsResponse {
  success: boolean;
  crops: string[];  // Array of base64 data URLs
}

interface SaveLabeledCropsResponse {
  success: boolean;
  message: string;
  trained_cards: string[];
  total_samples: number;
}
```

---

## Appendix: API Client Methods

```typescript
// In src/services/api.ts

export const api = {
  // Existing methods...
  
  // New methods for screenshot folder
  listScreenshots: async (): Promise<ListScreenshotsResponse> => {
    const response = await fetch(`${API_BASE_URL}/screenshots/list`);
    return response.json();
  },
  
  getScreenshotFile: async (filename: string): Promise<GetScreenshotFileResponse> => {
    const response = await fetch(`${API_BASE_URL}/screenshots/file/${filename}`);
    return response.json();
  },
  
  extractCrops: async (filename: string, crops: CropBox[]): Promise<ExtractCropsResponse> => {
    const response = await fetch(`${API_BASE_URL}/screenshots/extract-crops`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({filename, crops})
    });
    return response.json();
  },
  
  saveLabeledCrops: async (filename: string, crops: Array<CropBox & {label: string}>): Promise<SaveLabeledCropsResponse> => {
    const response = await fetch(`${API_BASE_URL}/screenshots/save-labeled-crops`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({filename, crops})
    });
    return response.json();
  }
};
```

---

## Sign-off

**Design Approved By:** User (implicit via todo continuation)  
**Implementation Ready:** Yes  
**Next Step:** Invoke `writing-plans` skill to create detailed implementation plan

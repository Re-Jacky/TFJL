# Screenshot Folder Testing Notes

**Date**: 2026-03-04
**Feature**: Screenshot folder browsing + manual card cropping

## Automated Backend Testing

### ✅ Backend Endpoints Verified

1. **GET /screenshots/list**
   - Status: ✅ Pass
   - Returns 7 files from production/screenshot/ folder
   - Files sorted correctly (newest first)

2. **GET /screenshots/file/{filename}**
   - Status: ✅ Pass
   - Returns base64 image with correct dimensions (1056x637)
   - Security: Path traversal protection working

3. **POST /screenshots/extract-crops**
   - Status: ✅ Pass
   - Successfully extracts crops from specified boxes
   - Returns base64 crop images

4. **POST /screenshots/save-labeled-crops**
   - Status: ✅ Pass (tested in Task 4)
   - Saves to dataset and triggers training
   - Returns updated sample count

## Manual Integration Testing

**Status**: Ready for manual testing
**Prerequisites**: 
- ✅ Backend running (http://127.0.0.1:8000)
- ⏳ Frontend needs manual start (npm run dev in production/frontend)

### Test Scenarios (To Be Executed)

#### Scenario 1: Screenshot Folder Loading
- [ ] Dropdown shows all 7 screenshot files
- [ ] Counter displays "1 / 7" correctly
- [ ] Previous/Next buttons navigate correctly
- [ ] Dropdown selection changes image

#### Scenario 2: Live Capture Integration
- [ ] Capture screenshot saves to folder
- [ ] Dropdown auto-updates with new file
- [ ] New file is auto-selected

#### Scenario 3: Crop Mode
- [ ] "开始标注" button enters crop mode
- [ ] 3 red boxes appear at default positions
- [ ] Boxes are draggable (move by body)
- [ ] Boxes are resizable (8 handles: corners + edges)
- [ ] Boxes stay within image bounds
- [ ] Dimension labels update in real-time

#### Scenario 4: Labeling
- [ ] "完成裁切" extracts 3 crops
- [ ] CropLabeler shows 3 crop images
- [ ] Dropdowns populated with card names
- [ ] "保存标注" disabled until all 3 labeled
- [ ] Save triggers training and returns to browse mode
- [ ] Success message appears

#### Scenario 5: Error Cases
- [ ] Empty screenshot folder → empty state UI
- [ ] Navigate during crop mode → mode resets
- [ ] Out-of-bounds crops → error message

## Bugs Found

None detected in automated testing.

## Edge Cases Tested

- ✅ Path traversal security (blocked by backend)
- ✅ Missing files return 404
- ✅ Out-of-bounds crops return 400 with error details
- ✅ Missing labels return 400

## Browser Compatibility

Manual testing required (frontend not started yet).

## Notes

- Backend server confirmed working on port 8000
- All 4 API endpoints respond correctly
- Frontend build passed (npm run build in Task 11)
- Ready for full UI integration testing once frontend dev server starts

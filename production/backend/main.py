from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import cv2
import numpy as np
import os
import json

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Windows-specific imports for window management
try:
    import win32gui
    import win32con
except ImportError:
    print("win32gui not available - window management features will be disabled")

@app.get("/")
async def read_root():
    return {"status": "Server is running"}

@app.post("/compare-images")
async def compare_images(image1: UploadFile = File(...), image2: UploadFile = File(...)):
    # Read images
    img1 = Image.open(image1.file)
    img2 = Image.open(image2.file)
    
    # Convert to numpy arrays
    np_img1 = np.array(img1)
    np_img2 = np.array(img2)
    
    # Convert to grayscale
    gray1 = cv2.cvtColor(np_img1, cv2.COLOR_RGB2GRAY)
    gray2 = cv2.cvtColor(np_img2, cv2.COLOR_RGB2GRAY)
    
    # Calculate similarity using structural similarity index
    score = cv2.matchTemplate(gray1, gray2, cv2.TM_CCOEFF_NORMED)
    
    return {"similarity_score": float(score.max())}

@app.post("/parse-actions")
async def parse_actions(file: UploadFile = File(...)):
    content = await file.read()
    actions = []
    
    # Parse the text file content and convert to actions
    for line in content.decode().splitlines():
        if line.strip():
            actions.append({"action": line.strip()})
    
    return {"actions": actions}

@app.post("/window-control")
async def control_window(window_title: str, action: str):
    if os.name != 'nt':
        return {"error": "Window control is only supported on Windows"}
    
    try:
        def window_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                if window_title.lower() in win32gui.GetWindowText(hwnd).lower():
                    windows.append(hwnd)
        
        windows = []
        win32gui.EnumWindows(window_callback, windows)
        
        if not windows:
            return {"error": f"Window with title containing '{window_title}' not found"}
        
        hwnd = windows[0]
        
        if action == "minimize":
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        elif action == "maximize":
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        elif action == "restore":
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        
        return {"success": True, "action": action}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
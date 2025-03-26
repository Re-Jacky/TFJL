from fastapi import FastAPI, Request, File, UploadFile
import pyautogui
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
from app.services.utility_services import UtilityService
from app.services.image_services import ImageService
from urllib.parse import unquote
from app.utils.logger import logger

app = FastAPI()

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(
        f"Method: {request.method} Path: {request.url.path} "
        f"Status: {response.status_code} Duration: {process_time:.3f}s"
    )
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Error processing request: {request.url.path}", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

utility_service = UtilityService()
image_service = ImageService()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "uptime": time.time() - app.state.start_time
    }

# Store server start time
app.state.start_time = time.time()

## testing purpose
@app.post("/parse-file")
async def parse_file(file_data: dict):
    decoded_file_name = unquote(file_data['file'])
    logger.info(f"Loading file: {decoded_file_name}")
    content = utility_service.read_file(decoded_file_name)
    return utility_service.parse_actions(content)
## testing purpose
@app.post("/start-action")
async def start_action(config: dict):
    action = config['action']
    logger.info(f"Starting action: {action}")
    return image_service.click_on_image(config['pid'], action)
   


@app.post("/read-file")
async def read_file(file_data: dict):
    decoded_file_name = unquote(file_data['file'])
    logger.info(f"Loading file: {decoded_file_name}")
    return utility_service.read_file(decoded_file_name)

@app.get("/get-file-list")
async def get_file_list():
    return utility_service.get_public_files()

@app.post("/save-file")
async def save_file(script_data: dict):
    file_name = unquote(script_data.get('file'))
    content = script_data.get('content')
    
    if not file_name:
        return JSONResponse(
            status_code=400,
            content={"detail": "File name is are required"}
        )
    
    logger.info(f"Saving script to file: {file_name}")
    return utility_service.save_file(file_name, content)

@app.post("/delete-file")
async def delete_file(file_data: dict):
    file_name = unquote(file_data.get('file'))
    
    if not file_name:
        return JSONResponse(
            status_code=400,
            content={"detail": "File name is required"}
        )
    
    try:
        logger.info(f"Deleting file: {file_name}")
        return utility_service.delete_file(file_name)
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error deleting file: {str(e)}"}
        )

@app.get("/windows")
async def get_windows():
    windows = []
    for window in pyautogui.getAllWindows():
        if window.title and window.title == '塔防精灵':
            windows.append({"title": window.title, "pid": window._hWnd})
    return {"windows": windows}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
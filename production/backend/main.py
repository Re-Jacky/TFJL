from fastapi import FastAPI, Request, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
from app.services.game_services import GameService
from app.services.utility_services import UtilityService
from app.models.schemas import (
    CollabRequest,
    IceFortressRequest,
    DarkMoonRequest,
    TimingEventRequest,
    BattleRequest,
    BaseResponse
)
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
        content={"detail": "Internal server error"}
    )
game_service = GameService()
utility_service = UtilityService()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def read_root():
    return {"status": "Server is running"}

@app.post("/collab", response_model=BaseResponse)
async def handle_collab(request: CollabRequest):
    return game_service.handle_collab(request)

@app.post("/ice-fortress", response_model=BaseResponse)
async def handle_ice_fortress(request: IceFortressRequest):
    return game_service.handle_ice_fortress(request)

@app.post("/dark-moon", response_model=BaseResponse)
async def handle_dark_moon(request: DarkMoonRequest):
    return game_service.handle_dark_moon(request)

@app.post("/timing-event", response_model=BaseResponse)
async def handle_timing_event(request: TimingEventRequest):
    return game_service.handle_timing_event(request)

@app.post("/battle", response_model=BaseResponse)
async def handle_battle(request: BattleRequest):
    return game_service.handle_battle(request)

@app.post("/compare-images")
async def compare_images(image1: UploadFile = File(...), image2: UploadFile = File(...)):
    return await utility_service.compare_images(image1, image2)

@app.post("/parse-actions")
async def parse_actions(file: UploadFile = File(...)):
    return await utility_service.parse_actions(file)

@app.post("/window-control")
async def control_window(window_title: str, action: str):
    return utility_service.control_window(window_title, action)

@app.get("/parse-file/{file_name}")
async def parse_file(file_name: str, base_dir: str = "data"):
    return utility_service.parse_file_by_name(file_name, base_dir)

@app.get("/get-file-list")
async def get_file_list():
    return utility_service.get_public_files()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
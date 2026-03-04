from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import time
from datetime import datetime
from pathlib import Path
import base64
from io import BytesIO
from PIL import Image
import cv2
from app.services.utility_services import UtilityService
from app.services.event_services import EventService
from app.services.image_services import ImageService
from app.services.window_control_services import WindowControlService
from app.services.screenshot_service import ScreenshotService
from app.services.game_service import GameService
from app.services.shortcut_service import ShortcutService
from urllib.parse import unquote
from app.utils.logger import logger
from app.schema.schemas import FileModel, WithContentFileModel
from app.models.script_models import (
    ParseScriptRequest, ParseScriptResponse,
    ValidateScriptRequest, ValidateScriptResponse,
    ScriptExecutionRequest, ScriptExecutionResponse,
    ScriptExecutionStatus, ExecutionState,
    TestScriptRequest, TestScriptResponse
)
from app.services.script_parser import ScriptParserService
from app.services.script_validator import ScriptValidatorService
from app.services.script_executor import ScriptExecutorService
from app.services.script_simulator import ScriptSimulatorService, DryRunSimulator
import pygetwindow
from app.services.card_recognition_service import CardRecognitionService
from app.services.card_dataset_service import CardDatasetService
from app.services.card_model_service import CardModelService
import numpy as np

app = FastAPI()

utility_service = UtilityService()
event_service = EventService()
image_service = ImageService()
shortcut_service = ShortcutService()
window_service = WindowControlService()
game_service = GameService()
# Script services use static methods - no instance needed
# Script executor instances are per-window, managed via get_instance()
# Initialize executor with event service for SSE broadcasting
ScriptExecutorService.set_event_service(event_service)
DryRunSimulator.set_event_service(event_service)
# Initialize card dataset folders
CardDatasetService.initialize()

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

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTP Error: {request.url.path} - {exc.detail}", exc_info=exc)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": f"HTTP error: {exc.detail}"}
    )

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# pid is used to identify the window to be controlled
# it is passed in the header of the request, 
# and it is used to identify the client connection
def get_req_pid(request: Request):
    return request.headers.get('x-pid')

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
async def parse_file(file_data: FileModel):
    decoded_file_name = unquote(file_data.file)
    logger.info(f"Loading file: {decoded_file_name}")
    content = utility_service.read_file(decoded_file_name, file_data.type)
    return utility_service.parse_actions(content)
## testing purpose
@app.get("/test-api")
async def test():
    # return True
    return game_service.start_moon_island({"game":1836896, "tool":1836896},{"game":1836896, "tool":1836896})


@app.post("/read-file")
async def read_file(file_data: FileModel):
    decoded_file_name = unquote(file_data.file)
    file_type = file_data.type
    logger.info(f"Loading file: {decoded_file_name}")
    return utility_service.read_file(decoded_file_name, file_type)

@app.get("/get-file-list")
async def get_file_list(type: str):
    if type == 'collab' or type == 'activity':
        return utility_service.get_files(type)
    else:
        return JSONResponse(
            status_code=400,
            content={"detail": "Invalid type parameter"}
        )

@app.post("/save-file")
async def save_file(request: Request, script_data: WithContentFileModel):
    file_name = unquote(script_data.file)
    content = script_data.content
    file_type = script_data.type
    if not file_name:
        return JSONResponse(
            status_code=400,
            content={"detail": "File name is are required"}
        )
    
    logger.info(f"Saving script to file: {file_name}")
    resp = utility_service.save_file(file_name, content, file_type)
    await event_service.broadcast_log("info", "保存文件: " + file_name + " 成功!")
    return resp

@app.post("/delete-file")
async def delete_file(request: Request, file_data: FileModel):
    file_name = unquote(file_data.file)
    file_type = file_data.type
    if not file_name:
        return JSONResponse(
            status_code=400,
            content={"detail": "File name is required"}
        )
    
    try:
        logger.info(f"Deleting file: {file_name}")
        resp = utility_service.delete_file(file_name, file_type)
        await event_service.broadcast_log("info", "删除文件: " + file_name + " 成功!")
        return resp
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        await event_service.broadcast_log("error", "删除文件: " + file_name + " 失败!")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error deleting file: {str(e)}"}
        )

@app.get("/game-windows")
async def get_game_windows():
    windows = []
    for window in pygetwindow.getAllWindows():
        if window.title and window.title == '塔防精灵':
            title = window.title +( "(已锁定)" if window._hWnd in window_service.locked_windows else "")
            windows.append({"title": title, "pid": window._hWnd})
    return {"windows": windows}

@app.get("/tool-windows")
async def get_tool_windows():
    windows = []
    for window in pygetwindow.getAllWindows():
        if window.title and (window.title.startswith('版本:') or window.title.startswith('2.')):
            windows.append({"title": "老马", "pid": window._hWnd})
    return {"windows": windows}

@app.post("/lock-window")
async def lock_window(request: Request, config: dict):
    lock_wnd = config.get("lock")
    pid = config.get("pid")
    if not pid:
        pid = get_req_pid(request)
    if not pid:
        return JSONResponse(
            status_code=422,
            content={"detail": "missing pid in the request header"}
        )
    if lock_wnd and pid in window_service.locked_windows:
        event_service.broadcast_log("error", "窗口已被其他进程锁定.", [pid])
        return JSONResponse(
            status_code=400,
            content={"detail": "窗口已被其他进程锁定."}
        )
    return window_service.lock_window(pid, lock_wnd)


@app.post("/locate-window")
async def locate_window(window_data: dict):
    """
    Move and resize the specified window to top-left corner of screen.
    Args:
        window_data: dict containing 'pid' of window to locate
    """
    try:
        pid = int(window_data['pid'])
        result = window_service.locate_game_window(pid, 0, 0)
        if result["status"] == "error":
            return JSONResponse(
                status_code=404 if "not found" in result["message"] else 500,
                content={"detail": result["message"]}
            )
        return result
    except Exception as e:
        logger.error(f"Error locating window: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error locating window: {str(e)}"}
        )

@app.post("/locate-auto-window")
async def locate_auto_window(window_data: dict):
    """
    Move the windows for users to identify.
    """
    try:
        gameWnd = window_data['game']
        toolWnd = window_data['tool']
        index = int(window_data['idx'])
        x_pos = 1056 * index
        window_service.locate_game_window(gameWnd, x_pos, 0)
        window_service.locate_tool_window(toolWnd, x_pos, 600)
    except Exception as e:
        logger.error(f"check the game and tool windows in automator: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error checking windows: {str(e)}"}
        )


@app.post("/start-auto-game")
async def start_auto_game(request: Request, config: dict):
    try:
        main = config['main']
        sub = config['sub']
        mode = config['mode']
        logger.info(f"Starting auto game with mode: {mode}. (0=collab, 1=ice, 2=moon)")
        info = ""
        if mode == 0:
            game_service.start_collab(main, sub)
            info = "合作"
        elif mode == 1:
            ice_only_support = False
            try:
                ice_only_support = config['iceOnlySupport']
            except Exception as e:
                logger.error(f"Error getting iceOnlySupport: {str(e)}")
            game_service.start_ice_castle(main, sub, ice_only_support)
            info = "寒冰"
        elif mode == 2:
            game_service.start_moon_island(main, sub)
            info = "暗月"
        await event_service.broadcast_log("info", f"开始{info}")
        return {"status": "success"}

    except Exception as e:
        logger.error(f"Error starting auto game: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error starting auto game: {str(e)}"}
        )

@app.post("/start-auto-battle")
async def start_auto_battle(request: Request, config: dict):
    try:
        main = config['main']
        sub = config['sub']
        game_service.start_auto_battle(main, sub)
        await event_service.broadcast_log("info", "开始对战")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error stopping auto battle: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error stopping auto battle: {str(e)}"}
        )

@app.post("/is-in-game")
async def is_in_game(request: Request, config: dict):
    try:
        main = config['main']
        sub = config['sub']
        main_result = image_service.find_image(main, '笑脸')
        sub_result = image_service.find_image(sub, '笑脸')
        if main_result['found'] == True and sub_result['found'] == True:
            await event_service.broadcast_log("info", "游戏中...")
            return {"status": True}
        else :
            await event_service.broadcast_log("info", "已退出游戏...")
            return {"status": False}
    except Exception as e:
        logger.error(f"Error checking if in game: {str(e)}")
        await event_service.broadcast_log("error", f"游戏检测异常: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error checking if in game: {str(e)}"}
        )



@app.get("/shortcut")
async def get_shortcut():
    try:
        return utility_service.get_shortcut()
    except Exception as e:
        logger.error(f"Error getting shortcut: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error getting shortcut: {str(e)}"}
        )

@app.post("/shortcut")
async def save_shortcut(shortcut_data: dict):
    try:
        utility_service.save_shortcut(shortcut_data["shortcut"])
        shortcut_service.reload_listeners()
        await event_service.broadcast_log("info", f"保存快捷键成功！")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error saving shortcut: {str(e)}")
        await event_service.broadcast_log("error", f"保存失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error saving shortcut: {str(e)}"}
        )
        
@app.post("/shortcut-config")
async def set_shortcut_mode(request: Request, config_data: dict):
    try:
        pid = get_req_pid(request)
        config = config_data.get("config")
        mode = config.get("mode")
        side = config.get("side")
        shortcut_service.set_config(pid, config)
        broadcase_msg = "快捷键模式设置为: "
        if mode != None:
            broadcase_msg += f"{mode} "
        if side!= None:
            broadcase_msg += f"{side} "
        await event_service.broadcast_log("info", f"快捷键模式设置为: {mode}")
        return {"status": "success", "mode": mode}
    except Exception as e:
        logger.error(f"Error setting shortcut config: {str(e)}")
        await event_service.broadcast_log("error", f"设置快捷键配置失败: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error setting shortcut config: {str(e)}"}
        )

@app.post("/monitor-shortcut")
async def monitor_shortcut(request: Request, config: dict):
    try:
        pid = get_req_pid(request)
        status = config.get("status")
        shortcut_service.set_active(pid, status)
        await event_service.broadcast_log("info", "启用快捷键." if status else "禁用快捷键.")
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error monitoring shortcut: {str(e)}")

@app.get("/sse")
async def event_stream(request: Request):
    pid = request.query_params.get('pid')
    if not pid:
        return JSONResponse(
            status_code=422,
            content={"detail": "pid is required"}
        )

    client_queue = await event_service.connect(pid)
    await event_service.broadcast_log("info", f"初始化成功！", [pid])
    try:
        async def event_generator():
            while True:
                try:
                    event = await client_queue.get()
                    if event is None:  # Check for explicit disconnect signal
                        break
                    event_data = await event_service.format_sse(event)
                    yield event_data
                except Exception as e:
                    logger.error(f"Error generating event: {str(e)}")
                    # Don't break on transient errors, continue the loop
                    continue

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Access-Control-Allow-Origin": "*"
            }
        )
    except Exception as e:
        logger.error(f"Error in event stream: {str(e)}")
        await event_service.disconnect(client_queue)
        raise

@app.post("/turn-off-pc")
async def turn_off_pc():
    try:
        utility_service.turn_off_pc()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error turning off PC: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error turning off PC: {str(e)}"}
        )

@app.post("/screenshot")
async def capture_screenshot(request: Request):
    """Capture screenshot of the specified window."""
    try:
        pid = get_req_pid(request)
        
        if not pid:
            try:
                body = await request.json()
                if isinstance(body, dict):
                    pid = body.get("pid")
            except:
                pass

        if not pid:
            raise HTTPException(status_code=400, detail="Window PID is required")
            
        result = ScreenshotService.capture_screenshot(int(pid))
        return result
    except ValueError:
        return JSONResponse(status_code=400, content={"detail": "Invalid PID format"})
    except Exception as e:
        logger.error(f"Error capturing screenshot: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error capturing screenshot: {str(e)}"}
        )
@app.get("/screenshots/list")
def list_screenshots():
    """List all PNG files in production/screenshot/ folder"""
    try:
        screenshot_dir = Path("../screenshot")
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

@app.get("/screenshots/file/{filename}")
def get_screenshot_file(filename: str):
    """Return base64-encoded image for a specific screenshot file"""
    try:
        screenshot_dir = Path("../screenshot")
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

@app.post("/screenshots/extract-crops")
def extract_crops_from_screenshot(request: dict):
    """Extract 3 crop regions from screenshot based on box positions"""
    try:
        filename = request.get("filename")
        crops = request.get("crops")  # List of {x, y, w, h}
        
        if not filename or not crops:
            raise HTTPException(status_code=400, detail="Missing filename or crops")
        
        screenshot_dir = Path("../screenshot")
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


@app.post("/screenshots/save-labeled-crops")
def save_labeled_crops_from_screenshot(request: dict):
    """Save labeled crops from screenshot to dataset and trigger training"""
    try:
        filename = request.get("filename")
        crops = request.get("crops")  # List of {x, y, w, h, label}
        
        if not filename or not crops:
            raise HTTPException(status_code=400, detail="Missing filename or crops")
        
        screenshot_dir = Path("../screenshot")
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
        model_status = CardModelService.get_model_info()
        
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



# ============================================================================
# SCRIPT AUTOMATION ENDPOINTS
# ============================================================================

@app.post("/script/parse")
async def parse_script(request_data: ParseScriptRequest):
    """Parse raw script content into structured Script model."""
    try:
        script, errors, warnings = ScriptParserService.parse_script(
            content=request_data.content,
            name=request_data.name,
            script_type=request_data.script_type
        )
        return ParseScriptResponse(
            success=script is not None,
            script=script,
            errors=errors,
            warnings=warnings
        )
    except Exception as e:
        logger.error(f"Error parsing script: {str(e)}")
        return ParseScriptResponse(
            success=False,
            errors=[f"Parse error: {str(e)}"]
        )


@app.post("/script/validate")
async def validate_script(request_data: ValidateScriptRequest):
    """Validate script content for errors and warnings."""
    try:
        # First parse the script
        script, parse_errors, parse_warnings = ScriptParserService.parse_script(content=request_data.content)
        if script is None:
            return ValidateScriptResponse(
                valid=False,
                errors=parse_errors,
                warnings=parse_warnings
            )
        
        # Then validate the parsed script
        validation_result = ScriptValidatorService.validate(script)
        return ValidateScriptResponse(
            valid=validation_result.is_valid,
            errors=validation_result.errors,
            warnings=validation_result.warnings
        )
    except Exception as e:
        logger.error(f"Error validating script: {str(e)}")
        return ValidateScriptResponse(
            valid=False,
            errors=[f"Validation error: {str(e)}"]
        )


@app.post("/script/test")
async def test_script(request_data: TestScriptRequest):
    """Test/simulate script execution without a game window (dry-run).
    
    If dry_run=True, uses live simulation with VehicleState tracking
    and SSE broadcasting for real-time UI updates.
    If dry_run=False (default), uses static simulation returning action log.
    """
    try:
        if request_data.dry_run:
            # Live dry-run with SSE broadcasting
            result = await DryRunSimulator.run_dry_run(
                content=request_data.content,
                name=request_data.name,
                script_type=request_data.script_type,
                session_id=request_data.session_id,
                action_delay_ms=request_data.action_delay_ms,
                level_delay_ms=request_data.level_delay_ms
            )
        else:
            # Static simulation (no SSE)
            result = ScriptSimulatorService.simulate_script(
                content=request_data.content,
                name=request_data.name,
                script_type=request_data.script_type
            )
            # Add empty vehicle_history for consistency
            result["vehicle_history"] = []
        
        return TestScriptResponse(**result)
    except Exception as e:
        logger.error(f"Error testing script: {str(e)}")
        return TestScriptResponse(
            success=False,
            errors=[f"Test error: {str(e)}"]
        )



@app.get("/script/list/{script_type}")
async def list_scripts(script_type: str):
    """List available scripts by type (collab or activity)."""
    if script_type not in ['collab', 'activity']:
        return JSONResponse(
            status_code=400,
            content={"detail": "Invalid script type. Must be 'collab' or 'activity'."}
        )
    try:
        files = utility_service.get_files(script_type)
        return {"scripts": files, "type": script_type}
    except Exception as e:
        logger.error(f"Error listing scripts: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error listing scripts: {str(e)}"}
        )


@app.post("/script/execute")
async def control_script_execution(request: Request, exec_request: ScriptExecutionRequest):
    """Control script execution: start, pause, resume, or stop."""
    try:
        pid = exec_request.window_pid
        action = exec_request.action
        
        # Get or create executor instance for this window
        executor = ScriptExecutorService.get_instance(pid)
        
        if action == 'start':
            # Load and start the script
            script_content = utility_service.read_file(
                exec_request.script_name,
                exec_request.script_type
            )
            script, parse_errors, _ = ScriptParserService.parse_script(
                content=script_content,
                name=exec_request.script_name,
                script_type=exec_request.script_type
            )
            
            if script is None:
                return ScriptExecutionResponse(
                    success=False,
                    message=f"Failed to parse script: {'; '.join(parse_errors)}"
                )
            
            # Validate before execution
            validation = ScriptValidatorService.validate(script)
            if not validation.is_valid:
                return ScriptExecutionResponse(
                    success=False,
                    message=f"Script validation failed: {'; '.join(validation.errors)}"
                )
            
            executor.load_script(script)
            executor.start()
            await event_service.broadcast_log("info", f"脚本开始执行: {exec_request.script_name}", [str(pid)])
            
            return ScriptExecutionResponse(
                success=True,
                message="Script started",
                status=executor.get_status()
            )
        
        elif action == 'pause':
            executor.pause()
            await event_service.broadcast_log("info", "脚本已暂停", [str(pid)])
            return ScriptExecutionResponse(
                success=True,
                message="Script paused",
                status=executor.get_status()
            )
        
        elif action == 'resume':
            executor.resume()
            await event_service.broadcast_log("info", "脚本继续执行", [str(pid)])
            return ScriptExecutionResponse(
                success=True,
                message="Script resumed",
                status=executor.get_status()
            )
        
        elif action == 'stop':
            executor.stop()
            await event_service.broadcast_log("info", "脚本已停止", [str(pid)])
            return ScriptExecutionResponse(
                success=True,
                message="Script stopped",
                status=executor.get_status()
            )
        
        else:
            return ScriptExecutionResponse(
                success=False,
                message=f"Unknown action: {action}"
            )
    
    except Exception as e:
        logger.error(f"Error controlling script execution: {str(e)}")
        return ScriptExecutionResponse(
            success=False,
            message=f"Execution error: {str(e)}"
        )


@app.get("/script/status/{window_pid}")
async def get_script_status(window_pid: int):
    """Get current script execution status for a window."""
    try:
        executor = ScriptExecutorService.get_instance(window_pid)
        status = executor.get_status()
        return {
            "success": True,
            "status": status.model_dump()
        }
    except Exception as e:
        logger.error(f"Error getting script status: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error getting script status: {str(e)}"}
        )



@app.post("/cards/detect")
async def detect_cards(request: Request):
    """Detect cards in 3 slots from active window"""
    pid = request.headers.get("x-pid")
    if not pid:
        body = await request.json()
        pid = body.get("window_pid")
    if not pid:
        raise HTTPException(status_code=400, detail="Missing window_pid")
    
    result = CardRecognitionService.detect_cards(int(pid))
    return result


@app.get("/cards/unlabeled")
async def get_unlabeled_crops(limit: int = 10):
    """Get unlabeled crops for labeling UI"""
    crops = CardDatasetService.get_unlabeled_crops(limit)
    stats = CardDatasetService.get_dataset_stats()
    return {"crops": crops, "total_unlabeled": stats["unlabeled_count"]}


@app.post("/cards/label")
async def label_crop(request: Request):
    """Apply label to crop, trigger incremental training"""
    body = await request.json()
    crop_id = body.get("crop_id")
    card_name = body.get("card_name")
    crop_margins = body.get("crop_margins")  # Optional: {top, bottom, left, right}
    
    if not crop_id or not card_name:
        raise HTTPException(status_code=400, detail="Missing crop_id or card_name")
    
    result = CardDatasetService.apply_label(crop_id, card_name, crop_margins)
    stats = CardDatasetService.get_dataset_stats()
    result["dataset_stats"] = stats
    return result


@app.post("/cards/train")
async def train_model():
    """Trigger full model rebuild"""
    result = CardModelService.train_full_rebuild()
    return result


@app.get("/cards/model/status")
async def get_model_status():
    """Get current model info"""
    try:
        info = CardModelService.get_model_info()
        return info
    except Exception as e:
        return {"model_version": None, "trained_cards": [], "total_samples": 0, "message": "No model trained yet"}

@app.post("/cards/batch_train")
async def batch_train_from_screenshots():
    """Read screenshots from folder and extract cards for training"""
    result = CardDatasetService.batch_train_from_screenshots()
    return result


@app.post("/cards/export")
async def export_model(request: Request):
    """Export trained model to ZIP file"""
    body = await request.json()
    export_path = body.get("export_path")
    
    if not export_path:
        raise HTTPException(status_code=400, detail="Missing export_path")
    
    result = CardModelService.export_model(export_path)
    return result


@app.post("/cards/import")
async def import_model(request: Request):
    """Import trained model from ZIP file"""
    body = await request.json()
    import_path = body.get("import_path")
    
    if not import_path:
        raise HTTPException(status_code=400, detail="Missing import_path")
    
    result = CardModelService.import_model(import_path)
    return result

@app.get("/cards/names")
async def get_card_names():
    """Get all available card names from configuration"""
    from app.enums.script_commands import COMMON_CARDS
    return {
        "cards": sorted(list(COMMON_CARDS)),
        "count": len(COMMON_CARDS)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import time
from app.services.utility_services import UtilityService
from app.services.event_services import EventService
from app.services.image_services import ImageService
from app.services.window_control_services import WindowControlService
from app.services.game_service import GameService
from app.services.shortcut_service import ShortcutService
from urllib.parse import unquote
from app.utils.logger import logger
from app.schema.schemas import FileModel, WithContentFileModel
import pygetwindow

app = FastAPI()

utility_service = UtilityService()
event_service = EventService()
image_service = ImageService()
shortcut_service = ShortcutService()
window_service = WindowControlService()
game_service = GameService()


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
    return True
    # return utility_service.turn_off_pc()


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
        if window.title and (window.title.startswith('版本:') or window.title.startswith('2.17')):
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
        info = ""
        if mode == 0:
            game_service.start_collab(main, sub)
            info = "合作"
        elif mode == 1:
            ice_only_support = config['iceOnlySupport']
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
            return {"status": False}
    except Exception as e:
        logger.error(f"Error checking if in game: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error checking if in game: {str(e)}"}
        )
    return {"status": False}



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
async def turn_off_pc(request: Request, config: dict):
    try:
        utility_service.turn_off_pc()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error turning off PC: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error turning off PC: {str(e)}"}
        )
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
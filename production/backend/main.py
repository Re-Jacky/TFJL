from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
import time
from app.services.utility_services import UtilityService
from app.services.event_services import EventService
from app.services.image_services import ImageService
from app.services.window_control_services import WindowControlService
from urllib.parse import unquote
from app.utils.logger import logger
from app.schema.schemas import FileModel, WithContentFileModel
import pygetwindow

app = FastAPI()

utility_service = UtilityService()
event_service = EventService()
image_service = ImageService()
image_service.initialize_card_templates()


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
@app.post("/start-action")
async def start_action(config: dict):
    action = config['action']
    logger.info(f"Starting action: {action}")
    return image_service.click_on_image(config['pid'], action)


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

# FileData model is now imported from app.models.file_data

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

@app.get("/windows")
async def get_windows():
    windows = []
    for window in pygetwindow.getAllWindows():
        if window.title and window.title == '塔防精灵':
            windows.append({"title": window.title, "pid": window._hWnd})
    return {"windows": windows}


@app.post("/locate-window")
async def locate_window(window_data: dict):
    """
    Move and resize the specified window to top-left corner of screen.
    Args:
        window_data: dict containing 'pid' of window to locate
    """
    try:
        pid = int(window_data['pid'])
        result = WindowControlService.locate_window(pid)
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
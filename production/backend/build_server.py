import PyInstaller.__main__
import os
import sys

def build_server():
    # Get the absolute path to the main.py file
    main_path = os.path.abspath('main.py')
    dist_path = os.path.abspath('dist')
    
    # Define PyInstaller arguments
    args = [
        'main.py',
        '--onefile',
        '--name=tfjl_server',
        '--hidden-import=uvicorn.logging',
        '--hidden-import=uvicorn.loops',
        '--hidden-import=uvicorn.loops.auto',
        '--hidden-import=uvicorn.protocols',
        '--hidden-import=uvicorn.protocols.http',
        '--hidden-import=uvicorn.protocols.http.auto',
        '--hidden-import=uvicorn.lifespan',
        '--hidden-import=uvicorn.lifespan.on',
        '--hidden-import=app.services.game_services',
        '--hidden-import=app.services.utility_services',
        '--hidden-import=app.models.schemas',
        '--hidden-import=app.utils.logger',
        f'--distpath={dist_path}',
        '--noconsole'
    ]
    
    # Run PyInstaller
    PyInstaller.__main__.run(args)

if __name__ == '__main__':
    build_server()
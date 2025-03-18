# TFJL Project

## Development Setup

### Backend Server

1. Navigate to backend directory:
   ```bash
   cd backend
   ```
2. Create virtual environment:
   ```bash
   python -m venv venv
   ```
3. Activate virtual environment (using Git Bash):
   ```bash
   source venv/Scripts/activate
   ```
4. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
5. Start development server:
   ```bash
   python -m uvicorn main:app --reload
   ```
6. Deactivate virtual environment:
   ```bash
   deactivate
   ```

### Frontend Client

1. Navigate to frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start development server:
   ```bash
   npm run dev
   ```
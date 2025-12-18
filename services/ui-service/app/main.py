from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Crypto Knowledge UI Service",
    description="Frontend UI for the crypto knowledge system",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the UI directory path
ui_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "ui")
if not os.path.exists(ui_path):
    ui_path = "/app/ui"  # Docker path

# Mount static files
app.mount("/static", StaticFiles(directory=ui_path), name="static")

@app.get("/health")
async def health_check():
    """UI service health check"""
    return {
        "status": "healthy",
        "service": "ui-service"
    }

@app.get("/")
async def read_root():
    """Serve the main index page"""
    return FileResponse(os.path.join(ui_path, "index.html"))

@app.get("/ai-chat")
async def read_chat():
    """Serve the AI chat page"""
    return FileResponse(os.path.join(ui_path, "ai-chat.html"))

@app.get("/{page_name}.html")
async def read_page(page_name: str):
    """Serve any HTML page"""
    file_path = os.path.join(ui_path, f"{page_name}.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(ui_path, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=3000)

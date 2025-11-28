"""
Standalone API cho Leak Detection Service
Chạy độc lập, không cần WNTR/EPANET
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

# Import leak detection service (không cần wntr)
from services.leak_detection_service import leak_detection_service
from api.routes.leak_detection import router as leak_detection_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting Leak Detection API...")
    print(f"Service ready: {leak_detection_service.is_ready()}")
    yield
    # Shutdown
    print("Shutting down Leak Detection API...")

app = FastAPI(
    title="Leak Detection API",
    description="API để phát hiện rò rỉ trong mạng lưới cấp nước",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include leak detection router only
app.include_router(leak_detection_router, prefix="/api/v1/leak-detection", tags=["leak-detection"])

@app.get("/")
async def root():
    return {
        "message": "Leak Detection API",
        "version": "1.0.0",
        "status": "running",
        "service_ready": leak_detection_service.is_ready()
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "leak-detection-api",
        "model_ready": leak_detection_service.is_ready()
    }

if __name__ == "__main__":
    uvicorn.run(
        "leak_detection_api:app",
        host="0.0.0.0",
        port=8001,  # Port khác với main API (8000)
        reload=True
    )




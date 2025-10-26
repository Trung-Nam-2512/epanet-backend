from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os
from dotenv import load_dotenv

from api.routes import simulation, data_input, scada_integration
from routers.network_topology import router as network_topology_router
from core.config import settings
from core.database import init_db

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting EPANET Simulation API...")
    init_db()
    yield
    # Shutdown
    print("Shutting down EPANET Simulation API...")

app = FastAPI(
    title="EPANET Water Network Simulation API",
    description="API để mô phỏng mạng lưới cấp nước sử dụng EPANET với dữ liệu thời gian thực",
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

# Include routers
app.include_router(simulation.router, prefix="/api/v1/simulation", tags=["simulation"])
app.include_router(data_input.router, prefix="/api/v1/data", tags=["data-input"])
app.include_router(scada_integration.router, prefix="/api/v1/scada", tags=["scada-integration"])
app.include_router(network_topology_router, prefix="/api/v1", tags=["network-topology"])

@app.get("/")
async def root():
    return {
        "message": "EPANET Water Network Simulation API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "epanet-api"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

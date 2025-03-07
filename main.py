from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from middleware.auth_middleware import FirebaseAuthMiddleware
from routes import profile_routes, friend_routes, history_routes, analytics_routes, auth_routes

app = FastAPI(
    title="Portal Gambit Backend",
    description="Backend API for Portal Gambit chess variant game",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Firebase Authentication Middleware
# Add paths that should be excluded from authentication
excluded_paths = [
    r"^/$",  # Root path
    r"^/docs$",  # Swagger UI
    r"^/openapi.json$",  # OpenAPI schema
    r"^/redoc$",  # ReDoc UI
]
app.add_middleware(FirebaseAuthMiddleware, exclude_paths=excluded_paths)

# Include routers
app.include_router(profile_routes.router)
app.include_router(friend_routes.router)
app.include_router(history_routes.router)
app.include_router(analytics_routes.router)
app.include_router(auth_routes.router)

@app.get("/")
async def root():
    """Root endpoint returning API information."""
    return {
        "name": "Portal Gambit Backend API",
        "version": "1.0.0",
        "status": "running"
    }

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

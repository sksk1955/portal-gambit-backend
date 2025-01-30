from fastapi import FastAPI
from app.routes import auth_routes, game_routes

app = FastAPI(title="Portal Gambit")

# Register routers
app.include_router(auth_routes.router)
app.include_router(game_routes.router)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

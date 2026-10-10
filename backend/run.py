import uvicorn
from app.config import settings

if __name__ == "__main__":
    print(f"Starting {settings.app_name} on {settings.host}:{settings.port}...")
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, receipts, expenses, game, budgets, ai
from app.database import check_db_connection
import logging

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Smart Receipt Analyzer API")

@app.on_event("startup")
async def startup_event():
    import sys
    from dotenv import load_dotenv
    load_dotenv() # Explicitly load .env
    logger.info(f"Starting up with Python: {sys.executable}")
    await check_db_connection()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="uploads"), name="static")

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(receipts.router, prefix="/api/receipts", tags=["receipts"])
app.include_router(expenses.router, prefix="/api/expenses", tags=["expenses"])
app.include_router(game.router, prefix="/api/game", tags=["game"])
app.include_router(budgets.router, prefix="/api/budgets", tags=["budgets"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])
# Import users router inside main to avoid circular imports if any, or just import at top
from app.routers import users
app.include_router(users.router, prefix="/api/users", tags=["users"])


@app.get("/")
def read_root():
    return {"message": "Welcome to Smart Receipt Analyzer API", "status": "active"}

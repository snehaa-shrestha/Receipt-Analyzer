from fastapi import APIRouter, HTTPException
from app.models.user import UserSchema, UserLoginSchema
from app.utils.security import get_password_hash, verify_password, create_access_token
from app.database import get_database

router = APIRouter()

@router.post("/register")
async def register(user: UserSchema):
    db = get_database()
    
    # Check existing
    if await db.users.find_one({"email": user.email}):
        raise HTTPException(400, "Email already registered")
    if await db.users.find_one({"username": user.username}):
        raise HTTPException(400, "Username already taken")
    
    # Hash and save
    user.password = get_password_hash(user.password)
    result = await db.users.insert_one(user.model_dump())
    
    return {"message": "User created", "user_id": str(result.inserted_id)}


@router.post("/login")
async def login(user_data: UserLoginSchema):
    db = get_database()
    
    # Find user
    user = await db.users.find_one({"username": user_data.username})
    if not user:
        raise HTTPException(401, "Invalid credentials")
    
    # Check password
    if not verify_password(user_data.password, user["password"]):
        raise HTTPException(401, "Invalid credentials")
    
    # Create token
    token = create_access_token({"sub": user["username"], "user_id": str(user["_id"])})
    
    return {"access_token": token, "token_type": "bearer", "username": user["username"]}

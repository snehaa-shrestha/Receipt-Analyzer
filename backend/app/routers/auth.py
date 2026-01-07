from fastapi import APIRouter, HTTPException, Depends
from app.models.user import UserSchema, UserLoginSchema
from app.utils.security import get_password_hash, verify_password, create_access_token
from app.database import get_database
from pymongo.collection import Collection

router = APIRouter()

@router.post("/register")
async def register(user: UserSchema):
    db = get_database()
    users_collection: Collection = db.users
    
    existing_user = await users_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    existing_username = await users_collection.find_one({"username": user.username})
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    hashed_password = get_password_hash(user.password)
    user.password = hashed_password
    
    new_user = await users_collection.insert_one(user.model_dump())
    return {"message": "User created successfully", "user_id": str(new_user.inserted_id)}

@router.post("/login")
async def login(user_data: UserLoginSchema):
    db = get_database()
    users_collection: Collection = db.users
    
    user = await users_collection.find_one({"username": user_data.username})
    if not user or not verify_password(user_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    access_token = create_access_token(data={"sub": user["username"], "user_id": str(user["_id"])})
    return {"access_token": access_token, "token_type": "bearer", "username": user["username"]}

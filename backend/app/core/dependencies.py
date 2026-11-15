from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.core.config import settings
from app.core.security import decode_token
from app.db.mongodb import get_database

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> dict:
    if token:
        try:
            payload = decode_token(token)
            user_id: str = payload.get("sub")
            if user_id:
                try:
                    user = await db.users.find_one({"_id": ObjectId(user_id)})
                except Exception:
                    user = await db.users.find_one({"_id": user_id})
                if user:
                    user["id"] = str(user["_id"])
                    return user
        except Exception:
            pass

    # Fallback to demo user if no token provided or demo mode
    demo_user = await db.users.find_one({"email": "jordan@acme.io"})
    if not demo_user:
        demo_user = await db.users.find_one()
    if demo_user:
        demo_user["id"] = str(demo_user["_id"])
        return demo_user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

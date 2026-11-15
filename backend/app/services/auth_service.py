from datetime import datetime
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.schemas.auth import UserRegisterSchema, UserLoginSchema, TokenSchema, UserOutSchema
from app.core.security import get_password_hash, verify_password, create_access_token

class AuthService:

    @staticmethod
    async def register_user(db: AsyncIOMotorDatabase, user_in: UserRegisterSchema) -> TokenSchema:
        existing = await db.users.find_one({"email": user_in.email.lower()})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists."
            )

        user_doc = {
            "email": user_in.email.lower(),
            "password_hash": get_password_hash(user_in.password),
            "name": user_in.name,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        result = await db.users.insert_one(user_doc)
        user_id = str(result.inserted_id)

        user_out = UserOutSchema(
            id=user_id,
            email=user_doc["email"],
            name=user_doc["name"],
            created_at=user_doc["created_at"],
            updated_at=user_doc["updated_at"]
        )

        access_token = create_access_token(subject=user_id)
        return TokenSchema(access_token=access_token, token_type="bearer", user=user_out)

    @staticmethod
    async def login_user(db: AsyncIOMotorDatabase, user_in: UserLoginSchema) -> TokenSchema:
        user_doc = await db.users.find_one({"email": user_in.email.lower()})
        if not user_doc or not verify_password(user_in.password, user_doc.get("password_hash", "")):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password credentials."
            )

        user_id = str(user_doc["_id"])
        user_out = UserOutSchema(
            id=user_id,
            email=user_doc["email"],
            name=user_doc["name"],
            created_at=user_doc.get("created_at", datetime.utcnow()),
            updated_at=user_doc.get("updated_at")
        )

        access_token = create_access_token(subject=user_id)
        return TokenSchema(access_token=access_token, token_type="bearer", user=user_out)

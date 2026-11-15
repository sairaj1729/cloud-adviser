from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongodb import get_database
from app.schemas.auth import UserRegisterSchema, UserLoginSchema, TokenSchema, UserOutSchema
from app.services.auth_service import AuthService
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=TokenSchema, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserRegisterSchema,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Register a new user account."""
    return await AuthService.register_user(db, user_in)

@router.post("/login", response_model=TokenSchema)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """OAuth2 compatible token login using email as username."""
    login_in = UserLoginSchema(email=form_data.username, password=form_data.password)
    return await AuthService.login_user(db, login_in)

@router.get("/me", response_model=UserOutSchema)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Fetch current authenticated user profile."""
    return UserOutSchema(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        created_at=current_user.get("created_at"),
        updated_at=current_user.get("updated_at")
    )

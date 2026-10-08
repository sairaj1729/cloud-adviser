from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserRegisterSchema(BaseModel):
    email: EmailStr
    password: str
    name: str

class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str

class UserOutSchema(BaseModel):
    id: str
    email: EmailStr
    name: str
    created_at: datetime
    updated_at: Optional[datetime] = None

class TokenSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOutSchema

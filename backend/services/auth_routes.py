from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from motor.motor_asyncio import AsyncIOMotorClient
from .auth_service import AuthService, User, Token
from typing import Optional
import jwt
from datetime import datetime

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 数据库连接
client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client.chatbot_db  # 指定数据库名称
auth_service = AuthService(db)  # 传入数据库实例而不是客户端

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, auth_service.SECRET_KEY, algorithms=[auth_service.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.JWTError:
        raise credentials_exception
    
    user = await auth_service.get_user(username)
    if user is None:
        raise credentials_exception
    return user

@router.post("/register", response_model=User)
async def register(user: User):
    return await auth_service.register_user(user)

@router.post("/token", response_model=Token)
async def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    token = await auth_service.login(form_data.username, form_data.password)
    
    # 获取用户信息
    user = await auth_service.get_user(form_data.username)
    if user:
        # 设置 user_id cookie，有效期与 token 相同
        response.set_cookie(
            key="user_id",
            value=str(user.id),  # 确保 user.id 是字符串
            httponly=True,
            secure=False,  # 开发环境设为 False，生产环境应设为 True
            samesite="lax",
            max_age=30 * 60,  # 30 分钟，与 token 过期时间相同
            path="/"  # 确保 cookie 在所有路径下可用
        )
    
    return token

@router.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user 
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import json
from fastapi import HTTPException

logger = logging.getLogger(__name__)

# 北京时区
BEIJING_TZ = timezone(timedelta(hours=8))

def get_beijing_time():
    """获取北京时间"""
    return datetime.now(BEIJING_TZ)

class MongoDBService:
    def __init__(self):
        # MongoDB 连接配置
        self.mongo_url = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
        self.db_name = os.environ.get("MONGODB_DB_NAME", "chatbot_db")
        self.client = None
        self.db = None
        
    async def connect(self):
        """连接到 MongoDB"""
        try:
            self.client = AsyncIOMotorClient(self.mongo_url)
            self.db = self.client[self.db_name]
            # 测试连接
            await self.client.admin.command('ping')
            logger.info(f"Successfully connected to MongoDB: {self.db_name}")
            
            # 创建索引
            await self.create_indexes()
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise
    
    async def create_indexes(self):
        """创建数据库索引"""
        try:
            # 为会话集合创建索引
            await self.db.conversations.create_index("conversation_id", unique=True)
            await self.db.conversations.create_index("user_id")  # 添加用户ID索引
            await self.db.conversations.create_index([("user_id", 1), ("updated_at", -1)])  # 复合索引
            await self.db.conversations.create_index("created_at")
            await self.db.conversations.create_index("updated_at")
            
            # 为消息集合创建索引
            await self.db.messages.create_index("conversation_id")
            await self.db.messages.create_index("timestamp")
            await self.db.messages.create_index([("conversation_id", 1), ("timestamp", 1)])
            logger.info("Database indexes created successfully")
        except Exception as e:
            logger.error(f"Failed to create indexes: {str(e)}")
    
    async def disconnect(self):
        """断开 MongoDB 连接"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    async def save_conversation(self, conversation_data: Dict, user_id: str = "default_user") -> bool:
        """保存或更新会话信息"""
        try:
            conversation_id = conversation_data.get("id")
            if not conversation_id:
                logger.error("Missing conversation_id")
                return False
            
            # 准备会话数据
            conv_doc = {
                "conversation_id": conversation_id,
                "user_id": user_id,  # 使用传入的用户ID
                "title": conversation_data.get("title", ""),
                "models": conversation_data.get("models", []),
                "created_at": conversation_data.get("createdAt", get_beijing_time().isoformat()),
                "updated_at": get_beijing_time().isoformat(),
                "message_count": len(conversation_data.get("messages", [])),
                "userId": user_id  # 添加用户ID字段
            }
            
            # 使用 upsert 更新或插入会话
            result = await self.db.conversations.update_one(
                {"conversation_id": conversation_id, "user_id": user_id},
                {"$set": conv_doc},
                upsert=True
            )
            
            logger.info(f"Conversation saved: {conversation_id} for user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save conversation: {str(e)}")
            return False
    
    async def save_message(self, conversation_id: str, message_data: Dict, user_id: str = "default_user") -> bool:
        """保存消息"""
        try:
            # 准备消息数据
            msg_doc = {
                "conversation_id": conversation_id,
                "user_id": user_id,  # 添加用户ID
                "role": message_data.get("role"),
                "content": message_data.get("content"),
                "model": message_data.get("model", ""),
                "timestamp": message_data.get("timestamp", get_beijing_time().isoformat()),
                "created_at": get_beijing_time().isoformat()
            }
            
            # 插入消息
            result = await self.db.messages.insert_one(msg_doc)
            
            # 更新会话的最后更新时间和消息数量（只更新属于该用户的会话）
            await self.db.conversations.update_one(
                {"conversation_id": conversation_id, "user_id": user_id},
                {
                    "$set": {"updated_at": get_beijing_time().isoformat()},
                    "$inc": {"message_count": 1}
                }
            )
            logger.info(f"Message saved for conversation: {conversation_id}, user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save message: {str(e)}")
            return False
    
    async def get_conversation(self, conversation_id: str, user_id: str = "default_user") -> Optional[Dict]:
        """获取指定用户的会话信息"""
        try:
            # 获取会话基本信息（验证用户ID）
            conversation = await self.db.conversations.find_one(
                {"conversation_id": conversation_id, "user_id": user_id}
            )
            
            if not conversation:
                return None
            
            # 获取会话消息（确保只获取该用户的消息）
            messages_cursor = self.db.messages.find(
                {
                    "conversation_id": conversation_id,
                    "user_id": user_id  # 添加用户ID过滤
                }
            ).sort("timestamp", 1)
            
            messages = []
            async for msg in messages_cursor:
                messages.append({
                    "role": msg.get("role"),
                    "content": msg.get("content"),
                    "model": msg.get("model", ""),
                    "timestamp": msg.get("timestamp")
                })
            
            # 构建返回数据
            result = {
                "id": conversation["conversation_id"],
                "title": conversation.get("title", ""),
                "models": conversation.get("models", []),
                "createdAt": conversation.get("created_at"),
                "messages": messages,
                "userId": conversation.get("user_id", user_id)
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get conversation: {str(e)}")
            return None
    
    async def get_all_conversations(self, user_id: str = "default_user") -> List[Dict]:
        """获取指定用户的所有会话列表"""
        try:
            conversations = []
            cursor = self.db.conversations.find({"user_id": user_id}).sort("updated_at", -1)
            
            async for conv in cursor:
                conversations.append({
                    "id": conv["conversation_id"],
                    "title": conv.get("title", ""),
                    "models": conv.get("models", []),
                    "createdAt": conv.get("created_at"),
                    "messageCount": conv.get("message_count", 0),
                    "updatedAt": conv.get("updated_at"),
                    "userId": conv.get("user_id", user_id)
                })
            
            return conversations
            
        except Exception as e:
            logger.error(f"Failed to get conversations for user {user_id}: {str(e)}")
            return []

    async def delete_conversation(self, conversation_id: str, user_id: str = "default_user") -> bool:
        """删除指定用户的会话和相关消息"""
        try:
            # 删除消息（确保只删除该用户的消息）
            await self.db.messages.delete_many({
                "conversation_id": conversation_id,
                "user_id": user_id  # 添加用户ID过滤
            })
            
            # 删除会话（确保是该用户的会话）
            result = await self.db.conversations.delete_one(
                {"conversation_id": conversation_id, "user_id": user_id}
            )
            
            if result.deleted_count > 0:
                logger.info(f"Conversation deleted: {conversation_id} for user: {user_id}")
                return True
            else:
                logger.warning(f"Conversation not found or not owned by user: {conversation_id}, {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete conversation: {str(e)}")
            return False
    
    async def update_conversation_title(self, conversation_id: str, title: str, user_id: str = "default_user") -> bool:
        """更新指定用户的会话标题"""
        try:
            result = await self.db.conversations.update_one(
                {"conversation_id": conversation_id, "user_id": user_id},                {
                    "$set": {
                        "title": title,
                        "updated_at": get_beijing_time().isoformat()
                    }
                }
            )
            
            if result.matched_count > 0:
                logger.info(f"Conversation title updated: {conversation_id} for user: {user_id}")
                return True
            else:
                logger.warning(f"Conversation not found or not owned by user: {conversation_id}, {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update conversation title: {str(e)}")
            return False
    
    async def get_conversation_history(self, conversation_id: str, user_id: str, limit: int = 20) -> List[Dict]:
        """获取会话历史消息（用于AI上下文）"""
        try:
            # 首先验证会话是否属于该用户
            conversation = await self.db.conversations.find_one(
                {"conversation_id": conversation_id, "user_id": user_id}
            )
            if not conversation:
                return []
                
            messages = []
            cursor = self.db.messages.find(
                {
                    "conversation_id": conversation_id,
                    "user_id": user_id  # 添加用户ID过滤
                }
            ).sort("timestamp", -1).limit(limit)
            
            async for msg in cursor:
                messages.append({
                    "role": msg.get("role"),
                    "content": msg.get("content")
                })
            
            # 返回时间顺序排列（最早的在前）
            return list(reversed(messages))
            
        except Exception as e:
            logger.error(f"Failed to get conversation history: {str(e)}")
            return []
    
    async def get_user_conversation_with_messages(self, user_id: str, conversation_id: str) -> Optional[Dict]:
        """获取用户的会话及其消息"""
        try:
            # 获取会话基本信息（验证用户ID）
            conversation = await self.db.conversations.find_one(
                {"conversation_id": conversation_id, "user_id": user_id}
            )
            
            if not conversation:
                return None
            
            # 获取会话消息（确保只获取该用户的消息）
            messages_cursor = self.db.messages.find(
                {
                    "conversation_id": conversation_id,
                    "user_id": user_id  # 添加用户ID过滤
                }
            ).sort("timestamp", 1)
            
            messages = []
            async for msg in messages_cursor:
                messages.append({
                    "role": msg.get("role"),
                    "content": msg.get("content"),
                    "model": msg.get("model", ""),
                    "timestamp": msg.get("timestamp")
                })
            
            # 构建返回数据
            result = {
                "id": conversation["conversation_id"],
                "title": conversation.get("title", ""),
                "models": conversation.get("models", []),
                "createdAt": conversation.get("created_at"),
                "messages": messages,
                "userId": user_id
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get user conversation: {str(e)}")
            return None
    
    async def get_user_conversations(self, user_id: str) -> List[Dict]:
        """获取用户的所有会话"""
        return await self.get_all_conversations(user_id)

    async def delete_user_conversation(self, user_id: str, conversation_id: str) -> bool:
        """删除用户的会话"""
        return await self.delete_conversation(conversation_id, user_id)
    
    async def get_user_statistics(self, user_id: str) -> Dict:
        """获取用户统计信息"""
        try:
            # 获取会话数量
            conversation_count = await self.db.conversations.count_documents({"user_id": user_id})
            
            # 获取消息数量
            pipeline = [
                {
                    "$lookup": {
                        "from": "conversations",
                        "localField": "conversation_id",
                        "foreignField": "conversation_id",
                        "as": "conversation"
                    }
                },
                {
                    "$unwind": "$conversation"
                },
                {
                    "$match": {
                        "conversation.user_id": user_id
                    }
                },
                {
                    "$count": "total_messages"
                }
            ]
            
            message_count_result = await self.db.messages.aggregate(pipeline).to_list(1)
            message_count = message_count_result[0]["total_messages"] if message_count_result else 0
            
            return {
                "user_id": user_id,
                "conversation_count": conversation_count,
                "message_count": message_count
            }
            
        except Exception as e:
            logger.error(f"Failed to get user statistics: {str(e)}")
            return {
                "user_id": user_id,
                "conversation_count": 0,
                "message_count": 0
            }

    async def create_user(self, user_data: dict) -> dict:
        """创建新用户"""
        try:
            # 检查用户名是否已存在
            existing_user = await self.db.users.find_one({"username": user_data["username"]})
            if existing_user:
                raise HTTPException(status_code=400, detail="用户名已存在")
            
            # 检查邮箱是否已存在
            existing_email = await self.db.users.find_one({"email": user_data["email"]})
            if existing_email:
                raise HTTPException(status_code=400, detail="邮箱已被注册")
            
            # 创建用户文档
            user_doc = {
                "username": user_data["username"],
                "email": user_data["email"],
                "hashed_password": user_data["hashed_password"],
                "created_at": datetime.now(),
                "last_login": None,
                "is_active": True
            }
            
            result = await self.db.users.insert_one(user_doc)
            user_doc["id"] = str(result.inserted_id)
            
            return user_doc
            
        except Exception as e:
            logger.error(f"创建用户失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"创建用户失败: {str(e)}")

    async def get_user_by_username(self, username: str) -> Optional[dict]:
        """通过用户名获取用户"""
        try:
            user = await self.db.users.find_one({"username": username})
            if user:
                user["id"] = str(user["_id"])
                return user
            return None
        except Exception as e:
            logger.error(f"获取用户失败: {str(e)}")
            return None

    async def get_user_by_email(self, email: str) -> Optional[dict]:
        """通过邮箱获取用户"""
        try:
            user = await self.db.users.find_one({"email": email})
            if user:
                user["id"] = str(user["_id"])
                return user
            return None
        except Exception as e:
            logger.error(f"获取用户失败: {str(e)}")
            return None

    async def update_user_last_login(self, user_id: str) -> bool:
        """更新用户最后登录时间"""
        try:
            result = await self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"last_login": datetime.now()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"更新用户登录时间失败: {str(e)}")
            return False

    async def update_user_password(self, user_id: str, new_hashed_password: str) -> bool:
        """更新用户密码"""
        try:
            result = await self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"hashed_password": new_hashed_password}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"更新用户密码失败: {str(e)}")
            return False

    async def deactivate_user(self, user_id: str) -> bool:
        """停用用户"""
        try:
            result = await self.db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"is_active": False}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"停用用户失败: {str(e)}")
            return False

# 全局 MongoDB 服务实例
mongodb_service = MongoDBService()

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any
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
            
            # 为分享集合创建索引
            await self.db.shares.create_index("share_id", unique=True)
            await self.db.shares.create_index("user_id")
            await self.db.shares.create_index("conversation_id")
            await self.db.shares.create_index("created_at")
            
            # 为用户模型集合创建索引
            await self.db.user_models.create_index([("user_id", 1), ("model_id", 1)], unique=True)  # 复合唯一索引
            await self.db.user_models.create_index("user_id")
            await self.db.user_models.create_index([("user_id", 1), ("created_at", -1)])
            await self.db.user_models.create_index("created_at")
            await self.db.user_models.create_index("updated_at")
            await self.db.user_models.create_index("is_active")
            
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

    async def create_share(self, conversation_id: str, user_id: str) -> Optional[Dict]:
        """创建会话分享"""
        try:
            # 生成唯一的分享ID
            share_id = str(ObjectId())
            
            # 创建分享文档
            share_doc = {
                "share_id": share_id,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "created_at": get_beijing_time().isoformat(),
                "is_active": True
            }
            
            # 插入分享记录
            result = await self.db.shares.insert_one(share_doc)
            
            if result.inserted_id:
                return {
                    "shareId": share_id,
                    "conversationId": conversation_id,
                    "createdAt": share_doc["created_at"]
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to create share: {str(e)}")
            return None
    
    async def get_shared_conversation(self, share_id: str) -> Optional[Dict]:
        """获取分享的会话内容"""
        try:
            # 获取分享记录
            share = await self.db.shares.find_one({"share_id": share_id})
            if not share:
                return None
            
            # 获取会话内容
            conversation = await self.get_conversation(share["conversation_id"], share["user_id"])
            if not conversation:
                return None
            
            # 获取分享用户信息
            user = await self.db.users.find_one({"_id": ObjectId(share["user_id"])})
            user_info = {
                "id": str(user["_id"]),
                "username": user.get("username", "未知用户"),
                "email": user.get("email", "")
            } if user else {"username": "未知用户"}
            
            return {
                "conversation": conversation,
                "shareId": share_id,
                "createdAt": share["created_at"],
                "sharedBy": user_info
            }
            
        except Exception as e:
            logger.error(f"Failed to get shared conversation: {str(e)}")
            return None
    
    async def get_user_shares(self, user_id: str) -> List[Dict]:
        """获取用户的所有分享"""
        try:
            shares = []
            cursor = self.db.shares.find({"user_id": user_id}).sort("created_at", -1)
            
            async for share in cursor:
                # 获取会话标题
                conversation = await self.db.conversations.find_one(
                    {"conversation_id": share["conversation_id"]},
                    {"title": 1}
                )
                
                shares.append({
                    "id": share["share_id"],
                    "conversationId": share["conversation_id"],
                    "title": conversation.get("title", "未命名会话") if conversation else "未命名会话",
                    "createdAt": share["created_at"]
                })
            
            return shares
            
        except Exception as e:
            logger.error(f"Failed to get user shares: {str(e)}")
            return []
    
    async def deactivate_share(self, share_id: str, user_id: str) -> bool:
        """删除分享"""
        try:
            result = await self.db.shares.delete_one(
                {"share_id": share_id, "user_id": user_id}
            )
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Failed to delete share: {str(e)}")
            return False

    async def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """通过用户ID获取用户信息"""
        try:
            user = await self.db.users.find_one({"_id": ObjectId(user_id)})
            if user:
                return user
            return None
        except Exception as e:
            logger.error(f"获取用户信息失败: {str(e)}")
            return None

    # ==================== 模型配置管理方法 ====================
    
    async def save_user_model(self, model_config: Dict[str, Any], user_id: str = "default_user") -> bool:
        """
        保存用户自定义模型配置
        
        Args:
            model_config: 模型配置字典
            user_id: 用户ID
            
        Returns:
            bool: 是否保存成功
        """
        try:
            model_id = model_config.get("id")
            if not model_id:
                logger.error("模型配置缺少model_id")
                return False
            
            # 准备模型文档
            model_doc = {
                "model_id": model_id,
                "user_id": user_id,
                "name": model_config.get("name", ""),
                "api_key": model_config.get("apiKey", ""),
                "api_base": model_config.get("apiBase", ""),
                "model_type": model_config.get("type", "custom"),
                "description": model_config.get("description", ""),
                "max_tokens": model_config.get("maxTokens", 4000),
                "temperature": model_config.get("temperature", 0.7),
                "stream_support": model_config.get("streamSupport", True),
                "is_active": model_config.get("isActive", True),
                "created_at": get_beijing_time().isoformat(),
                "updated_at": get_beijing_time().isoformat(),
                "config_version": "1.0"
            }
            
            # 使用upsert更新或插入模型配置
            result = await self.db.user_models.update_one(
                {"model_id": model_id, "user_id": user_id},
                {"$set": model_doc},
                upsert=True
            )
            
            logger.info(f"用户模型配置已保存: {model_id} for user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"保存用户模型配置失败: {str(e)}")
            return False
    
    async def get_user_model(self, model_id: str, user_id: str = "default_user") -> Optional[Dict[str, Any]]:
        """
        获取指定的用户模型配置
        
        Args:
            model_id: 模型ID
            user_id: 用户ID
            
        Returns:
            Optional[Dict]: 模型配置字典或None
        """
        try:
            model_doc = await self.db.user_models.find_one(
                {"model_id": model_id, "user_id": user_id, "is_active": True}
            )
            
            if not model_doc:
                return None
            
            # 转换为前端格式
            return {
                "id": model_doc["model_id"],
                "name": model_doc.get("name", ""),
                "apiKey": model_doc.get("api_key", ""),
                "apiBase": model_doc.get("api_base", ""),
                "type": model_doc.get("model_type", "custom"),
                "description": model_doc.get("description", ""),
                "maxTokens": model_doc.get("max_tokens", 4000),
                "temperature": model_doc.get("temperature", 0.7),
                "streamSupport": model_doc.get("stream_support", True),
                "isActive": model_doc.get("is_active", True),
                "createdAt": model_doc.get("created_at"),
                "updatedAt": model_doc.get("updated_at")
            }
            
        except Exception as e:
            logger.error(f"获取用户模型配置失败: {str(e)}")
            return None
    
    async def get_all_user_models(self, user_id: str = "default_user") -> List[Dict[str, Any]]:
        """
        获取用户的所有模型配置
        
        Args:
            user_id: 用户ID
            
        Returns:
            List[Dict]: 模型配置列表
        """
        try:
            models = []
            cursor = self.db.user_models.find(
                {"user_id": user_id, "is_active": True}
            ).sort("created_at", -1)
            
            async for model_doc in cursor:
                models.append({
                    "id": model_doc["model_id"],
                    "name": model_doc.get("name", ""),
                    "apiKey": model_doc.get("api_key", ""),
                    "apiBase": model_doc.get("api_base", ""),
                    "type": model_doc.get("model_type", "custom"),
                    "description": model_doc.get("description", ""),
                    "maxTokens": model_doc.get("max_tokens", 4000),
                    "temperature": model_doc.get("temperature", 0.7),
                    "streamSupport": model_doc.get("stream_support", True),
                    "isActive": model_doc.get("is_active", True),
                    "createdAt": model_doc.get("created_at"),
                    "updatedAt": model_doc.get("updated_at")
                })
            
            return models
            
        except Exception as e:
            logger.error(f"获取用户模型配置列表失败: {str(e)}")
            return []
    
    async def update_user_model(self, model_id: str, updates: Dict[str, Any], user_id: str = "default_user") -> bool:
        """
        更新用户模型配置
        
        Args:
            model_id: 模型ID
            updates: 更新字段字典
            user_id: 用户ID
            
        Returns:
            bool: 是否更新成功
        """
        try:
            # 准备更新数据
            update_doc = {}
            field_mapping = {
                "name": "name",
                "apiKey": "api_key",
                "apiBase": "api_base",
                "type": "model_type",
                "description": "description",
                "maxTokens": "max_tokens",
                "temperature": "temperature",
                "streamSupport": "stream_support",
                "isActive": "is_active"
            }
            
            for front_key, db_key in field_mapping.items():
                if front_key in updates:
                    update_doc[db_key] = updates[front_key]
            
            update_doc["updated_at"] = get_beijing_time().isoformat()
            
            result = await self.db.user_models.update_one(
                {"model_id": model_id, "user_id": user_id},
                {"$set": update_doc}
            )
            
            if result.matched_count > 0:
                logger.info(f"用户模型配置已更新: {model_id} for user: {user_id}")
                return True
            else:
                logger.warning(f"未找到要更新的模型配置: {model_id}, {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"更新用户模型配置失败: {str(e)}")
            return False
    
    async def delete_user_model(self, model_id: str, user_id: str = "default_user") -> bool:
        """
        删除用户模型配置（软删除）
        
        Args:
            model_id: 模型ID
            user_id: 用户ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            result = await self.db.user_models.update_one(
                {"model_id": model_id, "user_id": user_id},
                {
                    "$set": {
                        "is_active": False,
                        "updated_at": get_beijing_time().isoformat()
                    }
                }
            )
            
            if result.matched_count > 0:
                logger.info(f"用户模型配置已删除: {model_id} for user: {user_id}")
                return True
            else:
                logger.warning(f"未找到要删除的模型配置: {model_id}, {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"删除用户模型配置失败: {str(e)}")
            return False
    
    async def restore_models_to_environment(self, user_id: str = "default_user") -> Dict[str, str]:
        """
        将用户的模型配置恢复到环境变量
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict[str, str]: 设置的环境变量字典
        """
        try:
            models = await self.get_all_user_models(user_id)
            env_vars = {}
            
            for model in models:
                model_id = model["id"].upper()
                api_key = model.get("apiKey", "")
                api_base = model.get("apiBase", "")
                
                if api_key:
                    key_var = f"{model_id}_API_KEY"
                    os.environ[key_var] = api_key
                    env_vars[key_var] = api_key
                
                if api_base:
                    base_var = f"{model_id}_API_BASE"
                    os.environ[base_var] = api_base
                    env_vars[base_var] = api_base
            
            logger.info(f"已恢复 {len(env_vars)} 个环境变量 for user: {user_id}")
            return env_vars
            
        except Exception as e:
            logger.error(f"恢复环境变量失败: {str(e)}")
            return {}
    
    async def get_model_statistics(self, user_id: str = "default_user") -> Dict[str, Any]:
        """
        获取用户模型统计信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        try:
            # 活跃模型数量
            active_count = await self.db.user_models.count_documents(
                {"user_id": user_id, "is_active": True}
            )
            
            # 总模型数量（包括已删除）
            total_count = await self.db.user_models.count_documents(
                {"user_id": user_id}
            )
            
            # 按类型统计
            pipeline = [
                {"$match": {"user_id": user_id, "is_active": True}},
                {"$group": {"_id": "$model_type", "count": {"$sum": 1}}}
            ]
            
            type_stats = {}
            async for doc in self.db.user_models.aggregate(pipeline):
                type_stats[doc["_id"]] = doc["count"]
            
            return {
                "user_id": user_id,
                "active_models": active_count,
                "total_models": total_count,
                "by_type": type_stats,
                "generated_at": get_beijing_time().isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取模型统计信息失败: {str(e)}")
            return {
                "user_id": user_id,
                "active_models": 0,
                "total_models": 0,
                "by_type": {},
                "generated_at": get_beijing_time().isoformat()
            }
    
    async def export_user_models(self, user_id: str = "default_user") -> Dict[str, Any]:
        """
        导出用户的所有模型配置
        
        Args:
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 导出的配置数据
        """
        try:
            models = await self.get_all_user_models(user_id)
            
            export_data = {
                "export_version": "1.0",
                "user_id": user_id,
                "exported_at": get_beijing_time().isoformat(),
                "model_count": len(models),
                "models": models
            }
            
            logger.info(f"已导出 {len(models)} 个模型配置 for user: {user_id}")
            return export_data
            
        except Exception as e:
            logger.error(f"导出模型配置失败: {str(e)}")
            return {
                "export_version": "1.0",
                "user_id": user_id,
                "exported_at": get_beijing_time().isoformat(),
                "model_count": 0,
                "models": [],
                "error": str(e)
            }
    
    async def import_user_models(self, import_data: Dict[str, Any], user_id: str = "default_user") -> Dict[str, Any]:
        """
        导入用户模型配置
        
        Args:
            import_data: 导入的配置数据
            user_id: 用户ID
            
        Returns:
            Dict[str, Any]: 导入结果
        """
        try:
            models = import_data.get("models", [])
            success_count = 0
            failed_count = 0
            errors = []
            
            for model in models:
                try:
                    # 为导入的模型添加用户ID
                    model["user_id"] = user_id
                    success = await self.save_user_model(model, user_id)
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                        errors.append(f"保存模型失败: {model.get('id', 'unknown')}")
                except Exception as e:
                    failed_count += 1
                    errors.append(f"处理模型失败: {model.get('id', 'unknown')} - {str(e)}")
            
            result = {
                "success": True,
                "imported_at": get_beijing_time().isoformat(),
                "total_models": len(models),
                "success_count": success_count,
                "failed_count": failed_count,
                "errors": errors
            }
            
            logger.info(f"模型配置导入完成: 成功 {success_count}, 失败 {failed_count} for user: {user_id}")
            return result
            
        except Exception as e:
            logger.error(f"导入模型配置失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "imported_at": get_beijing_time().isoformat()
            }

# 全局 MongoDB 服务实例
mongodb_service = MongoDBService()

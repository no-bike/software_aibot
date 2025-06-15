import os
import logging
from datetime import datetime
from typing import List, Dict, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import json

logger = logging.getLogger(__name__)

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
                "user_id": user_id,  # 添加用户ID
                "title": conversation_data.get("title", ""),
                "models": conversation_data.get("models", []),
                "created_at": conversation_data.get("createdAt", datetime.utcnow().isoformat()),
                "updated_at": datetime.utcnow().isoformat(),
                "message_count": len(conversation_data.get("messages", []))
            }
            
            # 使用 upsert 更新或插入会话
            result = await self.db.conversations.update_one(
                {"conversation_id": conversation_id, "user_id": user_id},
                {"$set": conv_doc},
                upsert=True            )
            
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
                "role": message_data.get("role"),
                "content": message_data.get("content"),
                "model": message_data.get("model", ""),
                "timestamp": message_data.get("timestamp", datetime.utcnow().isoformat()),
                "created_at": datetime.utcnow().isoformat()
            }
            
            # 插入消息
            result = await self.db.messages.insert_one(msg_doc)
            
            # 更新会话的最后更新时间和消息数量（只更新属于该用户的会话）
            await self.db.conversations.update_one(
                {"conversation_id": conversation_id, "user_id": user_id},
                {
                    "$set": {"updated_at": datetime.utcnow().isoformat()},
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
            
            # 获取会话消息
            messages_cursor = self.db.messages.find(
                {"conversation_id": conversation_id}
            ).sort("timestamp", 1)
            
            messages = []
            async for msg in messages_cursor:
                messages.append({
                    "role": msg.get("role"),
                    "content": msg.get("content"),
                    "model": msg.get("model", ""),
                    "timestamp": msg.get("timestamp")                })
            
            # 构建返回数据
            result = {
                "id": conversation["conversation_id"],
                "title": conversation.get("title", ""),
                "models": conversation.get("models", []),
                "createdAt": conversation.get("created_at"),
                "messages": messages,
                "userId": conversation.get("user_id", "default_user")
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
                    "messageCount": conv.get("message_count", 0),                    "updatedAt": conv.get("updated_at"),
                    "userId": conv.get("user_id", user_id)
                })
            
            return conversations
            
        except Exception as e:
            logger.error(f"Failed to get conversations for user {user_id}: {str(e)}")
            return []
    
    async def delete_conversation(self, conversation_id: str, user_id: str = "default_user") -> bool:
        """删除指定用户的会话和相关消息"""
        try:
            # 删除消息
            await self.db.messages.delete_many({"conversation_id": conversation_id})
            
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
    
    async def get_conversation_history(self, conversation_id: str, limit: int = 20) -> List[Dict]:
        """获取会话历史消息（用于AI上下文）"""
        try:
            messages = []
            cursor = self.db.messages.find(
                {"conversation_id": conversation_id}
            ).sort("timestamp", -1).limit(limit)
            
            async for msg in cursor:
                messages.append({
                    "role": msg.get("role"),
                    "content": msg.get("content")
                })
            
            # 反转顺序，最早的消息在前
            messages.reverse()
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get conversation history: {str(e)}")
            return []
    
    async def get_user_conversations(self, user_id: str) -> List[Dict]:
        """获取特定用户的所有会话列表"""
        try:
            conversations = []
            cursor = self.db.conversations.find(
                {"user_id": user_id}
            ).sort("updated_at", -1)
            
            async for conv in cursor:
                conversations.append({
                    "id": conv["conversation_id"],
                    "title": conv.get("title", ""),
                    "models": conv.get("models", []),
                    "createdAt": conv.get("created_at"),
                    "messageCount": conv.get("message_count", 0),
                    "updatedAt": conv.get("updated_at"),
                    "userId": conv.get("user_id")
                })
            
            return conversations
            
        except Exception as e:
            logger.error(f"Failed to get user conversations: {str(e)}")
            return []
    
    async def get_user_conversation_with_messages(self, user_id: str, conversation_id: str) -> Optional[Dict]:
        """获取特定用户的会话信息和消息"""
        try:
            # 获取会话基本信息，确保是该用户的会话
            conversation = await self.db.conversations.find_one(
                {"conversation_id": conversation_id, "user_id": user_id}
            )
            
            if not conversation:
                return None
            
            # 获取会话消息
            messages_cursor = self.db.messages.find(
                {"conversation_id": conversation_id}
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
                "userId": conversation.get("user_id"),
                "messages": messages
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get user conversation: {str(e)}")
            return None
    
    async def delete_user_conversation(self, user_id: str, conversation_id: str) -> bool:
        """删除特定用户的会话和相关消息"""
        try:
            # 验证会话属于该用户
            conversation = await self.db.conversations.find_one(
                {"conversation_id": conversation_id, "user_id": user_id}
            )
            
            if not conversation:
                logger.warning(f"Conversation {conversation_id} not found for user {user_id}")
                return False
            
            # 删除消息
            await self.db.messages.delete_many({"conversation_id": conversation_id})
            
            # 删除会话
            result = await self.db.conversations.delete_one(
                {"conversation_id": conversation_id, "user_id": user_id}
            )
            
            if result.deleted_count > 0:
                logger.info(f"Conversation {conversation_id} deleted for user {user_id}")
                return True
            else:
                logger.warning(f"Failed to delete conversation {conversation_id} for user {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete user conversation: {str(e)}")
            return False
    
    async def get_user_statistics(self, user_id: str) -> Dict:
        """获取用户的统计信息"""
        try:
            # 获取会话数量
            conversation_count = await self.db.conversations.count_documents(
                {"user_id": user_id}
            )
            
            # 获取消息数量
            pipeline = [
                {"$match": {"user_id": user_id}},
                {"$group": {"_id": None, "total_messages": {"$sum": "$message_count"}}}
            ]
            message_stats = await self.db.conversations.aggregate(pipeline).to_list(1)
            total_messages = message_stats[0]["total_messages"] if message_stats else 0
            
            # 获取最近活动时间
            latest_conversation = await self.db.conversations.find_one(
                {"user_id": user_id},
                sort=[("updated_at", -1)]
            )
            
            result = {
                "userId": user_id,
                "conversationCount": conversation_count,
                "totalMessages": total_messages,
                "lastActivity": latest_conversation.get("updated_at") if latest_conversation else None
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get user statistics: {str(e)}")
            return {
                "userId": user_id,
                "conversationCount": 0,
                "totalMessages": 0,
                "lastActivity": None
            }

# 全局 MongoDB 服务实例
mongodb_service = MongoDBService()

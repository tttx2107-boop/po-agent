"""微信入口"""
import json
import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WeChatMessage:
    """微信消息"""
    msg_id: str
    msg_type: str
    content: str
    from_user: str
    to_user: str
    timestamp: int
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WeChatMessage":
        return cls(
            msg_id=str(data.get("msgid", "")),
            msg_type=data.get("msgtype", "text"),
            content=data.get("content", ""),
            from_user=data.get("fromusername", ""),
            to_user=data.get("tousername", ""),
            timestamp=data.get("createtime", 0)
        )


class WeChatHandler:
    """
    微信消息处理器
    
    负责接收和响应微信消息
    """
    
    def __init__(self, agent: "PoAgent", webhook_url: str = ""):
        self.agent = agent
        self.webhook_url = webhook_url or ""
        self.session_context: Dict[str, Dict] = {}  # 用户上下文
    
    def handle_message(self, message_data: Dict[str, Any]) -> str:
        """
        处理微信消息
        
        Args:
            message_data: 微信消息数据
            
        Returns:
            响应文本
        """
        try:
            message = WeChatMessage.from_dict(message_data)
            
            # 忽略非文本消息
            if message.msg_type != "text":
                logger.info(f"忽略非文本消息: {message.msg_type}")
                return ""
            
            content = message.content.strip()
            if not content:
                return ""
            
            # 处理消息
            response = self.agent.process(content, source="wechat")
            
            return response
            
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            return f"处理消息时出错: {str(e)}"
    
    def handle_command(self, command: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理命令（供 Webhook 调用）
        
        Args:
            command: 命令类型
            args: 命令参数
            
        Returns:
            处理结果
        """
        try:
            if command == "assess":
                # 触发评估
                limit = args.get("limit", 3)
                results = self.agent.assess_pending(limit)
                return {"success": True, "count": len(results)}
            
            elif command == "list":
                # 列出想法
                ideas = self.agent.list_ideas()
                return {"success": True, "ideas": [i.to_dict() for i in ideas]}
            
            elif command == "stats":
                # 统计数据
                stats = self.agent.get_stats()
                return {"success": True, "stats": stats}
            
            else:
                return {"success": False, "error": f"未知命令: {command}"}
                
        except Exception as e:
            logger.error(f"处理命令失败: {e}")
            return {"success": False, "error": str(e)}
    
    def build_reminder_message(self, stats: Dict[str, Any]) -> str:
        """构建提醒消息"""
        pending = stats.get("pending_assessment", 0)
        
        msg = f"""📊 「破」评估提醒

⏰ 您的想法库有待评估的想法：

📋 待评估：{pending} 个

💡 建议：
• 「立即评估」- 开始深度评估
• 「查看想法」- 查看想法列表
• 「统计」- 查看整体统计
"""
        return msg


class WeChatAPI:
    """
    微信消息发送 API
    
    通过 HTTP 请求发送消息到微信
    """
    
    def __init__(self, base_url: str = ""):
        self.base_url = base_url
        self.timeout = 10
    
    def send_text(self, to_user: str, content: str) -> bool:
        """
        发送文本消息
        
        Args:
            to_user: 接收用户
            content: 消息内容
            
        Returns:
            是否成功
        """
        if not self.base_url:
            logger.warning("未配置微信 webhook URL")
            return False
        
        try:
            import requests
            payload = {
                "touser": to_user,
                "msgtype": "text",
                "text": {"content": content}
            }
            
            response = requests.post(
                self.base_url,
                json=payload,
                timeout=self.timeout
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False
    
    def send_markdown(self, to_user: str, content: str) -> bool:
        """发送 Markdown 消息"""
        if not self.base_url:
            return False
        
        try:
            import requests
            payload = {
                "touser": to_user,
                "msgtype": "markdown",
                "markdown": {"content": content}
            }
            
            response = requests.post(
                self.base_url,
                json=payload,
                timeout=self.timeout
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            return False

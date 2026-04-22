"""GitHub Gist 存储"""
import json
import requests
from typing import List, Dict, Any, Optional
from .base import BaseStorage


class GistStorage(BaseStorage):
    """GitHub Gist 存储"""
    
    FILES = {
        "ideas": "ideas.json",
        "tasks": "tasks.json",
        "activities": "activities.json"
    }
    
    def __init__(self, token: str, gist_id: str):
        self.token = token
        self.gist_id = gist_id
        self.api_base = "https://api.github.com/gists"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """发送 API 请求"""
        response = requests.request(method, url, headers=self.headers, **kwargs)
        response.raise_for_status()
        return response
    
    def _get_current_files(self) -> Dict[str, Any]:
        """获取当前 Gist 文件内容"""
        try:
            response = self._request("GET", f"{self.api_base}/{self.gist_id}")
            files = {}
            for f in response.json().get("files", {}).values():
                files[f["filename"]] = {
                    "content": f.get("content", ""),
                    "sha": f.get("sha")
                }
            return files
        except Exception:
            return {}
    
    def _read_file(self, filename: str) -> List[Dict]:
        """读取单个文件"""
        try:
            files = self._get_current_files()
            if filename in files:
                content = files[filename]["content"]
                if content:
                    return json.loads(content)
            return []
        except (json.JSONDecodeError, KeyError):
            return []
    
    def _write_file(self, filename: str, data: List[Dict], message: str = None) -> bool:
        """写入单个文件"""
        try:
            files = self._get_current_files()
            content = json.dumps(data, ensure_ascii=False, indent=2)
            
            # 构建更新内容
            file_update = {"content": content}
            if filename in files:
                file_update["sha"] = files[filename]["sha"]
            
            files[filename] = file_update
            
            # 构建 API 请求体
            payload = {"files": {filename: file_update}}
            if message:
                payload["description"] = message
            else:
                payload["description"] = f"更新 {filename}"
            
            self._request("PATCH", f"{self.api_base}/{self.gist_id}", json=payload)
            return True
        except Exception as e:
            print(f"Gist 写入失败: {e}")
            return False
    
    def save_ideas(self, ideas: List[Dict[str, Any]]) -> bool:
        return self._write_file(self.FILES["ideas"], ideas, "更新想法库")
    
    def load_ideas(self) -> List[Dict[str, Any]]:
        return self._read_file(self.FILES["ideas"])
    
    def save_tasks(self, tasks: List[Dict[str, Any]]) -> bool:
        return self._write_file(self.FILES["tasks"], tasks, "更新任务库")
    
    def load_tasks(self) -> List[Dict[str, Any]]:
        return self._read_file(self.FILES["tasks"])
    
    def append_activity(self, log: Dict[str, Any]) -> bool:
        logs = self.load_activities()
        logs.append(log)
        logs = logs[-1000:]  # 只保留最近 1000 条
        return self._write_file(self.FILES["activities"], logs, "追加活动日志")
    
    def load_activities(self, limit: int = 100) -> List[Dict[str, Any]]:
        logs = self._read_file(self.FILES["activities"])
        return logs[-limit:]


def get_storage(token: str = None, gist_id: str = None, local_path: str = "data") -> BaseStorage:
    """获取存储实例 - 优先 Gist，失败则本地"""
    if not token:
        print("⚠ 未配置 GitHub Token，使用本地存储")
        from .base import LocalStorage
        return LocalStorage(local_path)
    
    gist = GistStorage(token, gist_id)
    try:
        gist.load_ideas()  # 测试连接
        print("✓ 使用 GitHub Gist 存储")
        return gist
    except Exception as e:
        print(f"⚠ GitHub Gist 连接失败 ({e})，使用本地存储")
        from .base import LocalStorage
        return LocalStorage(local_path)

"""GitHub Gist 存储层"""
import json
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

class GistStorage:
    """想法库存储 - 使用 GitHub Gist"""
    
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
    
    def read(self, filename: str = "ideas.json") -> List[Dict[str, Any]]:
        """读取想法列表"""
        try:
            response = self._request("GET", f"{self.api_base}/{self.gist_id}")
            gist_data = response.json()
            
            for file in gist_data.get("files", {}).values():
                if file.get("filename") == filename:
                    content = file.get("content", "[]")
                    return json.loads(content)
            return []
        except Exception as e:
            print(f"读取失败: {e}")
            return []
    
    def write(self, ideas: List[Dict[str, Any]], filename: str = "ideas.json", 
              commit_message: str = None) -> bool:
        """写入想法列表"""
        try:
            content = json.dumps(ideas, ensure_ascii=False, indent=2)
            
            # 获取当前 Gist 内容以获取 ETag
            current = self._request("GET", f"{self.api_base}/{self.gist_id}")
            current_files = {}
            for f in current.json().get("files", {}).values():
                current_files[f["filename"]] = {
                    "content": f.get("content", "")
                }
            
            # 更新指定文件
            current_files[filename] = {"content": content}
            
            if commit_message is None:
                commit_message = f"更新想法库 ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
            
            self._request("PATCH", f"{self.api_base}/{self.gist_id}", 
                         json={"files": current_files, "description": commit_message})
            return True
        except Exception as e:
            print(f"写入失败: {e}")
            return False
    
    def backup(self) -> Optional[str]:
        """备份当前数据到文件"""
        try:
            ideas = self.read()
            backup_dir = Path(__file__).parent / "backups"
            backup_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"ideas_backup_{timestamp}.json"
            
            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(ideas, f, ensure_ascii=False, indent=2)
            
            return str(backup_file)
        except Exception as e:
            print(f"备份失败: {e}")
            return None


class LocalStorage:
    """本地文件存储（备用）"""
    
    def __init__(self, data_file: Path):
        self.data_file = data_file
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
    
    def read(self) -> List[Dict[str, Any]]:
        """读取想法列表"""
        try:
            if self.data_file.exists():
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"读取失败: {e}")
            return []
    
    def write(self, ideas: List[Dict[str, Any]]) -> bool:
        """写入想法列表"""
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(ideas, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"写入失败: {e}")
            return False


def get_storage(token: str, gist_id: str, local_path: Path = None) -> Any:
    """获取存储实例 - 优先使用 Gist，失败则回退到本地"""
    gist = GistStorage(token, gist_id)
    
    # 测试 Gist 连接
    try:
        gist.read()
        print("✓ 使用 GitHub Gist 存储")
        return gist
    except:
        print("⚠ GitHub Gist 连接失败，使用本地存储")
        if local_path:
            return LocalStorage(local_path)
        return LocalStorage(Path(__file__).parent / "data" / "ideas.json")

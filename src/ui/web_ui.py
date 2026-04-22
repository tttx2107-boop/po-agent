"""
Web UI 入口和静态文件服务
"""
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Any
import asyncio
import json
from datetime import datetime
import os

from ..storage.gist_store import get_storage
from ..utils.logger import setup_logger

logger = setup_logger("po-agent.web_ui")

# Web UI 路由
router = APIRouter(prefix="/ui", tags=["Web UI"])

# WebSocket 连接管理器
class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket 连接已建立，当前连接数: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket 连接已断开，当前连接数: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """广播消息到所有连接"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"广播消息失败: {e}")
                disconnected.append(connection)
        
        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)
    
    async def send_personal(self, websocket: WebSocket, message: Dict[str, Any]):
        """发送消息到特定连接"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"发送消息失败: {e}")
            self.disconnect(websocket)


manager = ConnectionManager()


# ==================== HTML 页面路由 ====================

@router.get("/", response_class=HTMLResponse)
async def index_page():
    """主页"""
    html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>「破」想法实现智能体</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            max-width: 1200px;
            width: 100%;
        }
        h1 {
            color: #333;
            font-size: 2.5em;
            margin-bottom: 10px;
            text-align: center;
        }
        .subtitle {
            color: #666;
            text-align: center;
            margin-bottom: 40px;
            font-size: 1.1em;
        }
        .features {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .feature-card {
            background: linear-gradient(135deg, #f5f7fa 0%, #e4e8eb 100%);
            padding: 25px;
            border-radius: 12px;
            transition: transform 0.3s;
        }
        .feature-card:hover { transform: translateY(-5px); }
        .feature-card h3 { color: #667eea; margin-bottom: 10px; }
        .feature-card p { color: #666; line-height: 1.6; }
        .cta {
            text-align: center;
        }
        .cta a {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 40px;
            border-radius: 25px;
            text-decoration: none;
            font-weight: bold;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .cta a:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>「破」</h1>
        <p class="subtitle">让想法从"灵光一现"到"落地成真"的 AI 助理</p>
        
        <div class="features">
            <div class="feature-card">
                <h3>💡 想法管理</h3>
                <p>统一管理所有想法，定期盘活，不再错过好点子</p>
            </div>
            <div class="feature-card">
                <h3>📊 智能评估</h3>
                <p>快速评估可行性，深度分析风险收益</p>
            </div>
            <div class="feature-card">
                <h3>📋 任务拆解</h3>
                <p>一键拆解复杂想法为可执行任务</p>
            </div>
            <div class="feature-card">
                <h3>⏰ 定时复盘</h3>
                <p>自动提醒定期复盘，持续优化迭代</p>
            </div>
        </div>
        
        <div class="cta">
            <a href="/ui/app">进入控制台 →</a>
        </div>
    </div>
</body>
</html>
    """
    return html_content


@router.get("/app", response_class=HTMLResponse)
async def app_page():
    """应用主页面"""
    html_content = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>「破」控制台</title>
    <style>
        :root {
            --primary: #667eea;
            --secondary: #764ba2;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --bg: #f5f7fa;
            --card-bg: white;
            --text: #1f2937;
            --text-muted: #6b7280;
            --border: #e5e7eb;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
        }
        /* 导航栏 */
        .navbar {
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            padding: 15px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .navbar-brand {
            color: white;
            font-size: 1.5em;
            font-weight: bold;
            text-decoration: none;
        }
        .navbar-menu {
            display: flex;
            gap: 20px;
        }
        .navbar-menu a {
            color: rgba(255,255,255,0.9);
            text-decoration: none;
            padding: 8px 16px;
            border-radius: 8px;
            transition: background 0.3s;
        }
        .navbar-menu a:hover, .navbar-menu a.active {
            background: rgba(255,255,255,0.2);
        }
        /* 主容器 */
        .main-container {
            display: flex;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            gap: 20px;
        }
        /* 侧边栏 */
        .sidebar {
            width: 280px;
            flex-shrink: 0;
        }
        .sidebar-card {
            background: var(--card-bg);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        .sidebar-card h3 {
            font-size: 0.9em;
            color: var(--text-muted);
            text-transform: uppercase;
            margin-bottom: 15px;
        }
        /* 统计卡片 */
        .stat-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        .stat-item {
            text-align: center;
            padding: 15px;
            background: var(--bg);
            border-radius: 8px;
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            color: var(--primary);
        }
        .stat-label {
            font-size: 0.85em;
            color: var(--text-muted);
        }
        /* 主内容区 */
        .main-content {
            flex: 1;
        }
        .content-card {
            background: var(--card-bg);
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        .content-card h2 {
            margin-bottom: 20px;
            color: var(--text);
            display: flex;
            align-items: center;
            gap: 10px;
        }
        /* 输入区 */
        .input-group {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .input-group textarea {
            flex: 1;
            padding: 15px;
            border: 2px solid var(--border);
            border-radius: 10px;
            font-size: 1em;
            resize: vertical;
            min-height: 100px;
            font-family: inherit;
            transition: border-color 0.3s;
        }
        .input-group textarea:focus {
            outline: none;
            border-color: var(--primary);
        }
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 10px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn-primary {
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: white;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        .btn-secondary {
            background: var(--bg);
            color: var(--text);
        }
        .btn-secondary:hover { background: var(--border); }
        /* 想法列表 */
        .idea-list {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        .idea-item {
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 15px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .idea-item:hover {
            border-color: var(--primary);
            transform: translateX(5px);
        }
        .idea-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 10px;
        }
        .idea-title {
            font-weight: 600;
            color: var(--text);
        }
        .idea-status {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 600;
        }
        .status-new { background: #dbeafe; color: #1d4ed8; }
        .status-assessing { background: #fef3c7; color: #d97706; }
        .status-confirmed { background: #d1fae5; color: #059669; }
        .status-deferred { background: #ede9fe; color: #7c3aed; }
        .status-rejected { background: #fee2e2; color: #dc2626; }
        .status-in_progress { background: #cffafe; color: #0891b2; }
        .status-completed { background: #d1fae5; color: #047857; }
        .idea-preview {
            color: var(--text-muted);
            font-size: 0.9em;
            line-height: 1.5;
        }
        .idea-meta {
            display: flex;
            gap: 15px;
            margin-top: 10px;
            font-size: 0.85em;
            color: var(--text-muted);
        }
        /* 标签 */
        .tag {
            display: inline-block;
            padding: 3px 10px;
            background: var(--bg);
            border-radius: 15px;
            font-size: 0.8em;
            color: var(--text-muted);
            margin-right: 5px;
            margin-bottom: 5px;
        }
        /* 加载状态 */
        .loading {
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 40px;
        }
        .spinner {
            width: 40px;
            height: 40px;
            border: 4px solid var(--border);
            border-top-color: var(--primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        /* 空状态 */
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: var(--text-muted);
        }
        .empty-state-icon {
            font-size: 4em;
            margin-bottom: 20px;
        }
        /* Toast 通知 */
        .toast-container {
            position: fixed;
            top: 80px;
            right: 20px;
            z-index: 1000;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .toast {
            padding: 15px 20px;
            border-radius: 10px;
            color: white;
            font-weight: 500;
            animation: slideIn 0.3s ease;
            box-shadow: 0 5px 20px rgba(0,0,0,0.2);
        }
        .toast-success { background: var(--success); }
        .toast-error { background: var(--danger); }
        .toast-warning { background: var(--warning); }
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        /* 模态框 */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        .modal.active { display: flex; }
        .modal-content {
            background: white;
            border-radius: 15px;
            padding: 30px;
            max-width: 600px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            animation: modalIn 0.3s ease;
        }
        @keyframes modalIn {
            from { transform: scale(0.9); opacity: 0; }
            to { transform: scale(1); opacity: 1; }
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .modal-close {
            background: none;
            border: none;
            font-size: 1.5em;
            cursor: pointer;
            color: var(--text-muted);
        }
        /* 评估卡片 */
        .assessment-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .assessment-item {
            text-align: center;
            padding: 20px;
            background: var(--bg);
            border-radius: 10px;
        }
        .assessment-score {
            font-size: 2.5em;
            font-weight: bold;
            color: var(--primary);
        }
        .assessment-label {
            color: var(--text-muted);
            font-size: 0.9em;
            margin-top: 5px;
        }
        /* 风险指示器 */
        .risk-indicator {
            display: flex;
            gap: 5px;
            margin-top: 10px;
        }
        .risk-bar {
            height: 8px;
            flex: 1;
            border-radius: 4px;
            background: var(--border);
        }
        .risk-bar.active.high { background: var(--danger); }
        .risk-bar.active.medium { background: var(--warning); }
        .risk-bar.active.low { background: var(--success); }
        /* 响应式 */
        @media (max-width: 768px) {
            .main-container { flex-direction: column; }
            .sidebar { width: 100%; }
            .navbar-menu { display: none; }
        }
    </style>
</head>
<body>
    <!-- 导航栏 -->
    <nav class="navbar">
        <a href="/" class="navbar-brand">「破」</a>
        <div class="navbar-menu">
            <a href="#" class="active">想法</a>
            <a href="#">任务</a>
            <a href="#">评估</a>
            <a href="#">设置</a>
        </div>
    </nav>

    <!-- 主容器 -->
    <div class="main-container">
        <!-- 侧边栏 -->
        <aside class="sidebar">
            <!-- 统计 -->
            <div class="sidebar-card">
                <h3>📊 统计概览</h3>
                <div class="stat-grid">
                    <div class="stat-item">
                        <div class="stat-value" id="total-count">0</div>
                        <div class="stat-label">总想法</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="pending-count">0</div>
                        <div class="stat-label">待评估</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="confirmed-count">0</div>
                        <div class="stat-label">已确认</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="completed-count">0</div>
                        <div class="stat-label">已完成</div>
                    </div>
                </div>
            </div>

            <!-- 快速操作 -->
            <div class="sidebar-card">
                <h3>⚡ 快速操作</h3>
                <button class="btn btn-primary" style="width: 100%; margin-bottom: 10px;" onclick="showIdeaModal()">
                    💡 新增想法
                </button>
                <button class="btn btn-secondary" style="width: 100%; margin-bottom: 10px;" onclick="refreshIdeas()">
                    🔄 刷新
                </button>
                <button class="btn btn-secondary" style="width: 100%;" onclick="exportIdeas()">
                    📥 导出
                </button>
            </div>

            <!-- 筛选 -->
            <div class="sidebar-card">
                <h3>🔍 筛选</h3>
                <select id="status-filter" style="width: 100%; padding: 10px; border-radius: 8px; border: 1px solid var(--border);">
                    <option value="">全部状态</option>
                    <option value="NEW">🆕 新想法</option>
                    <option value="ASSESSING">⏳ 待评估</option>
                    <option value="CONFIRMED">✅ 已确认</option>
                    <option value="DEFERRED">⏸️ 暂缓</option>
                    <option value="REJECTED">❌ 已否决</option>
                    <option value="IN_PROGRESS">🔄 执行中</option>
                    <option value="COMPLETED">⭐ 已完成</option>
                </select>
            </div>
        </aside>

        <!-- 主内容区 -->
        <main class="main-content">
            <!-- 输入区 -->
            <div class="content-card">
                <h2>💡 记录新想法</h2>
                <div class="input-group">
                    <textarea id="idea-input" placeholder="输入你的想法...&#10;例如：开发一个个人博客网站，用于分享技术文章"></textarea>
                    <button class="btn btn-primary" onclick="submitIdea()">提交</button>
                </div>
                <div style="display: flex; gap: 10px; flex-wrap: wrap;">
                    <input type="text" id="tag-input" placeholder="添加标签（回车添加）" 
                           style="padding: 8px 15px; border: 1px solid var(--border); border-radius: 20px; flex: 1; min-width: 200px;">
                    <div id="tags-container"></div>
                </div>
            </div>

            <!-- 想法列表 -->
            <div class="content-card">
                <h2>📋 我的想法 <span id="idea-count"></span></h2>
                <div id="idea-list" class="idea-list">
                    <div class="loading"><div class="spinner"></div></div>
                </div>
            </div>
        </main>
    </div>

    <!-- Toast 容器 -->
    <div class="toast-container" id="toast-container"></div>

    <!-- 模态框：想法详情 -->
    <div class="modal" id="idea-modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="modal-title">想法详情</h2>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div id="modal-body">
                <!-- 动态内容 -->
            </div>
        </div>
    </div>

    <script>
        // 全局状态
        let ideas = [];
        let selectedTags = [];
        let currentIdea = null;

        // API 基础路径
        const API_BASE = '/api/v1';

        // ==================== 初始化 ====================
        document.addEventListener('DOMContentLoaded', () => {
            loadIdeas();
            
            // 标签输入
            document.getElementById('tag-input').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    addTag(e.target.value);
                    e.target.value = '';
                }
            });

            // 筛选
            document.getElementById('status-filter').addEventListener('change', renderIdeas);
        });

        // ==================== API 调用 ====================
        async function loadIdeas() {
            try {
                const response = await fetch(`${API_BASE}/ideas`);
                const data = await response.json();
                ideas = data.ideas || [];
                updateStats();
                renderIdeas();
            } catch (error) {
                showToast('加载失败: ' + error.message, 'error');
                ideas = [];
                renderIdeas();
            }
        }

        async function submitIdea() {
            const content = document.getElementById('idea-input').value.trim();
            if (!content) {
                showToast('请输入想法内容', 'warning');
                return;
            }

            try {
                const response = await fetch(`${API_BASE}/ideas`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content, tags: selectedTags })
                });
                
                if (response.ok) {
                    const data = await response.json();
                    ideas.unshift(data.idea);
                    updateStats();
                    renderIdeas();
                    document.getElementById('idea-input').value = '';
                    selectedTags = [];
                    renderTags();
                    showToast('想法已添加！', 'success');
                } else {
                    showToast('添加失败', 'error');
                }
            } catch (error) {
                showToast('网络错误: ' + error.message, 'error');
            }
        }

        async function deleteIdea(id) {
            if (!confirm('确定要删除这个想法吗？')) return;

            try {
                const response = await fetch(`${API_BASE}/ideas/${id}`, { method: 'DELETE' });
                if (response.ok) {
                    ideas = ideas.filter(i => i.id !== id);
                    updateStats();
                    renderIdeas();
                    showToast('已删除', 'success');
                }
            } catch (error) {
                showToast('删除失败', 'error');
            }
        }

        async function quickAssess(id) {
            try {
                const response = await fetch(`${API_BASE}/ideas/${id}/quick-assess`, { method: 'POST' });
                if (response.ok) {
                    const data = await response.json();
                    const idea = ideas.find(i => i.id === id);
                    if (idea) {
                        idea.quick_assessment = data.assessment;
                        renderIdeas();
                        showToast('快速评估完成！', 'success');
                    }
                }
            } catch (error) {
                showToast('评估失败', 'error');
            }
        }

        // ==================== 渲染 ====================
        function updateStats() {
            document.getElementById('total-count').textContent = ideas.length;
            document.getElementById('pending-count').textContent = ideas.filter(i => i.status === 'NEW' || i.status === 'ASSESSING').length;
            document.getElementById('confirmed-count').textContent = ideas.filter(i => i.status === 'CONFIRMED').length;
            document.getElementById('completed-count').textContent = ideas.filter(i => i.status === 'COMPLETED').length;
        }

        function renderIdeas() {
            const container = document.getElementById('idea-list');
            const filter = document.getElementById('status-filter').value;
            
            let filtered = ideas;
            if (filter) {
                filtered = ideas.filter(i => i.status === filter);
            }

            if (filtered.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">💭</div>
                        <p>${ideas.length === 0 ? '还没有想法，快来添加第一个吧！' : '没有符合筛选条件的想法'}</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = filtered.map(idea => `
                <div class="idea-item" onclick="showIdeaDetail('${idea.id}')">
                    <div class="idea-header">
                        <span class="idea-title">${escapeHtml(idea.content.substring(0, 50))}${idea.content.length > 50 ? '...' : ''}</span>
                        <span class="idea-status status-${idea.status.toLowerCase()}">${getStatusName(idea.status)}</span>
                    </div>
                    <div class="idea-preview">${escapeHtml(idea.content.substring(0, 100))}</div>
                    ${idea.tags && idea.tags.length > 0 ? `
                        <div style="margin-top: 10px;">
                            ${idea.tags.map(t => `<span class="tag">${t}</span>`).join('')}
                        </div>
                    ` : ''}
                    <div class="idea-meta">
                        <span>🕐 ${idea.created_at ? idea.created_at.substring(0, 10) : '-'}</span>
                        ${idea.quick_assessment ? `<span>⚡ ${Math.round(idea.quick_assessment.completeness * 100)}%</span>` : ''}
                        ${idea.deep_assessment ? `<span>📊 ${idea.deep_assessment.overall_score}分</span>` : ''}
                    </div>
                </div>
            `).join('');

            document.getElementById('idea-count').textContent = `(${filtered.length})`;
        }

        function renderTags() {
            const container = document.getElementById('tags-container');
            container.innerHTML = selectedTags.map((tag, i) => 
                `<span class="tag" style="cursor: pointer;" onclick="removeTag(${i})">✕ ${tag}</span>`
            ).join('');
        }

        function addTag(tag) {
            tag = tag.trim();
            if (tag && !selectedTags.includes(tag) && selectedTags.length < 5) {
                selectedTags.push(tag);
                renderTags();
            }
        }

        function removeTag(index) {
            selectedTags.splice(index, 1);
            renderTags();
        }

        // ==================== 模态框 ====================
        function showIdeaModal() {
            document.getElementById('idea-input').focus();
        }

        function showIdeaDetail(id) {
            currentIdea = ideas.find(i => i.id === id);
            if (!currentIdea) return;

            document.getElementById('modal-title').textContent = '想法详情';
            document.getElementById('modal-body').innerHTML = `
                <div style="margin-bottom: 20px;">
                    <span class="idea-status status-${currentIdea.status.toLowerCase()}">${getStatusName(currentIdea.status)}</span>
                </div>
                
                <div style="background: var(--bg); padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                    ${escapeHtml(currentIdea.content)}
                </div>

                ${currentIdea.tags && currentIdea.tags.length > 0 ? `
                    <h4 style="margin-bottom: 10px;">🏷️ 标签</h4>
                    <div style="margin-bottom: 20px;">
                        ${currentIdea.tags.map(t => `<span class="tag">${t}</span>`).join('')}
                    </div>
                ` : ''}

                <h4 style="margin-bottom: 10px;">📊 评估</h4>
                ${currentIdea.quick_assessment ? `
                    <div class="assessment-grid">
                        <div class="assessment-item">
                            <div class="assessment-score">${Math.round(currentIdea.quick_assessment.completeness * 100)}%</div>
                            <div class="assessment-label">完整性</div>
                        </div>
                        <div class="assessment-item">
                            <div class="assessment-score">${currentIdea.quick_assessment.clarity || '-'}</div>
                            <div class="assessment-label">清晰度</div>
                        </div>
                    </div>
                ` : '<p style="color: var(--text-muted); margin-bottom: 20px;">暂无评估</p>'}

                ${currentIdea.deep_assessment ? `
                    <div class="assessment-grid">
                        <div class="assessment-item">
                            <div class="assessment-score">${currentIdea.deep_assessment.overall_score}</div>
                            <div class="assessment-label">综合得分</div>
                        </div>
                        <div class="assessment-item">
                            <div class="assessment-score">${currentIdea.deep_assessment.decision_level}</div>
                            <div class="assessment-label">决策建议</div>
                        </div>
                    </div>
                ` : ''}

                <div style="display: flex; gap: 10px; margin-top: 20px; flex-wrap: wrap;">
                    ${!currentIdea.quick_assessment ? `<button class="btn btn-primary" onclick="quickAssess('${id}')">⚡ 快速评估</button>` : ''}
                    <button class="btn btn-secondary" onclick="deleteIdea('${id}'); closeModal();">🗑️ 删除</button>
                </div>

                <div style="margin-top: 20px; color: var(--text-muted); font-size: 0.9em;">
                    创建于: ${currentIdea.created_at || '-'}
                    ${currentIdea.updated_at !== currentIdea.created_at ? `<br>更新于: ${currentIdea.updated_at || '-'}` : ''}
                </div>
            `;

            document.getElementById('idea-modal').classList.add('active');
        }

        function closeModal() {
            document.getElementById('idea-modal').classList.remove('active');
            currentIdea = null;
        }

        // 点击模态框外部关闭
        document.getElementById('idea-modal').addEventListener('click', (e) => {
            if (e.target.id === 'idea-modal') closeModal();
        });

        // ==================== 工具函数 ====================
        function showToast(message, type = 'info') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            toast.className = `toast toast-${type}`;
            toast.textContent = message;
            container.appendChild(toast);
            
            setTimeout(() => toast.remove(), 3000);
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        function getStatusName(status) {
            const names = {
                'NEW': '新想法',
                'ASSESSING': '评估中',
                'CONFIRMED': '已确认',
                'DEFERRED': '暂缓',
                'REJECTED': '已否决',
                'IN_PROGRESS': '进行中',
                'COMPLETED': '已完成'
            };
            return names[status] || status;
        }

        function refreshIdeas() {
            loadIdeas();
            showToast('已刷新', 'success');
        }

        function exportIdeas() {
            const data = JSON.stringify(ideas, null, 2);
            const blob = new Blob([data], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `po-agent-ideas-${new Date().toISOString().split('T')[0]}.json`;
            a.click();
            showToast('已导出', 'success');
        }
    </script>
</body>
</html>
    """
    return html_content


# ==================== WebSocket 路由 ====================

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 实时通信"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 处理不同类型的消息
            msg_type = message.get("type")
            
            if msg_type == "ping":
                await manager.send_personal(websocket, {"type": "pong", "time": datetime.now().isoformat()})
            
            elif msg_type == "subscribe":
                # 订阅特定事件
                await manager.send_personal(websocket, {
                    "type": "subscribed", 
                    "channels": message.get("channels", [])
                })
            
            elif msg_type == "refresh_ideas":
                # 触发想法刷新
                storage = get_storage()
                ideas = await storage.get_all_ideas()
                await manager.send_personal(websocket, {
                    "type": "ideas_updated",
                    "data": {"count": len(ideas)}
                })
            
            else:
                await manager.send_personal(websocket, {
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}"
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# ==================== 实时通知 API ====================

@router.post("/notify")
async def send_notification(title: str, message: str, level: str = "info"):
    """发送实时通知到所有连接的客户端"""
    await manager.broadcast({
        "type": "notification",
        "title": title,
        "message": message,
        "level": level,
        "time": datetime.now().isoformat()
    })
    return {"success": True, "connections": len(manager.active_connections)}


@router.get("/status")
async def get_status():
    """获取连接状态"""
    return {
        "active_connections": len(manager.active_connections),
        "uptime": "running"
    }

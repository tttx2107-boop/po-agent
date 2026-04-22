"""测试命令路由 - TDD"""
import pytest
from src.core.router import CommandRouter, RouteResult


class TestCommandRouter:
    """命令路由测试"""
    
    @pytest.fixture
    def router(self):
        return CommandRouter()
    
    # 测试想法相关命令
    def test_route_view_ideas(self, router):
        """测试查看想法"""
        result = router.route("查看想法")
        assert result.success is True
        assert result.module == "idea"
        assert result.action == "list"
    
    def test_route_list_alias(self, router):
        """测试 list 别名"""
        result = router.route("list")
        assert result.success is True
        assert result.module == "idea"
        assert result.action == "list"
    
    # 测试详情命令
    def test_route_detail(self, router):
        """测试详情命令"""
        result = router.route("查看详情 abc123")
        assert result.success is True
        assert result.module == "idea"
        assert result.action == "detail"
        assert result.args.get("id") == "abc123"
    
    def test_route_detail_alias(self, router):
        """测试详情别名"""
        result = router.route("detail xyz789")
        assert result.success is True
        assert result.args.get("id") == "xyz789"
    
    # 测试评估命令
    def test_route_evaluate(self, router):
        """测试评估命令"""
        result = router.route("立即评估")
        assert result.success is True
        assert result.module == "assessment"
        assert result.action == "trigger"
    
    def test_route_eval_alias(self, router):
        """测试 eval 别名"""
        result = router.route("eval")
        assert result.success is True
        assert result.module == "assessment"
    
    # 测试统计命令
    def test_route_stats(self, router):
        """测试统计命令"""
        result = router.route("统计")
        assert result.success is True
        assert result.module == "stats"
    
    # 测试帮助命令
    def test_route_help(self, router):
        """测试帮助命令"""
        result = router.route("帮助")
        assert result.success is True
        assert result.module == "help"
    
    def test_route_help_alias(self, router):
        """测试 help 别名"""
        result = router.route("?")
        assert result.success is True
        assert result.module == "help"
    
    # 测试确认/暂缓/否决命令
    def test_route_confirm(self, router):
        """测试确认执行"""
        result = router.route("确认执行 idea-001")
        assert result.success is True
        assert result.module == "idea"
        assert result.action == "confirm"
    
    def test_route_defer(self, router):
        """测试暂缓"""
        result = router.route("暂缓 idea-002")
        assert result.success is True
        assert result.module == "idea"
        assert result.action == "defer"
    
    def test_route_reject(self, router):
        """测试否决"""
        result = router.route("否决 idea-003")
        assert result.success is True
        assert result.module == "idea"
        assert result.action == "reject"
    
    # 测试任务命令
    def test_route_tasks(self, router):
        """测试任务列表"""
        result = router.route("查看任务")
        assert result.success is True
        assert result.module == "task"
        assert result.action == "list"
    
    def test_route_done(self, router):
        """测试完成任务"""
        result = router.route("完成任务 task-001")
        assert result.success is True
        assert result.module == "task"
        assert result.action == "done"
    
    # 测试系统命令
    def test_route_sync(self, router):
        """测试同步"""
        result = router.route("同步")
        assert result.success is True
        assert result.module == "system"
        assert result.action == "sync"
    
    def test_route_backup(self, router):
        """测试备份"""
        result = router.route("备份")
        assert result.success is True
        assert result.module == "system"
    
    # 测试想法创建
    def test_route_idea_creation(self, router):
        """测试想法创建（直接输入）"""
        result = router.route("我想做一个消防APP")
        assert result.success is True
        assert result.module == "idea"
        assert result.action == "create"
        assert result.args.get("content") == "我想做一个消防APP"
    
    def test_route_idea_long_content(self, router):
        """测试想法创建（长内容）"""
        content = "做一个结合AI和物联网的智能消防巡检系统，目标是提高消防检查效率"
        result = router.route(content)
        assert result.success is True
        assert result.args.get("content") == content
    
    # 测试空输入
    def test_route_empty(self, router):
        """测试空输入"""
        result = router.route("")
        assert result.success is False
        assert result.module == "system"
    
    def test_route_whitespace(self, router):
        """测试空白输入"""
        result = router.route("   ")
        assert result.success is False
    
    # 测试前缀匹配
    def test_route_prefix_match(self, router):
        """测试前缀匹配"""
        result = router.route("查看想法详情")
        assert result.success is True
        assert result.module == "idea"
        assert result.action == "list"
    
    # 测试 is_command
    def test_is_command_true(self, router):
        """测试 is_command 返回 True"""
        assert router.is_command("查看想法") is True
        assert router.is_command("list") is True
        assert router.is_command("立即评估") is True
    
    def test_is_command_false(self, router):
        """测试 is_command 返回 False"""
        assert router.is_command("我想做一个APP") is False
        assert router.is_command("随便写点什么") is False


class TestRouteResult:
    """路由结果测试"""
    
    def test_route_result_creation(self):
        """测试路由结果创建"""
        result = RouteResult(
            success=True,
            module="idea",
            action="list",
            args={"limit": 10},
            raw_input="查看想法"
        )
        assert result.success is True
        assert result.module == "idea"
        assert result.action == "list"
        assert result.args["limit"] == 10
        assert result.raw_input == "查看想法"

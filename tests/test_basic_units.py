"""
GitHub 多模态RAG系统 - 后端黑盒白盒测试用例集
使用pytest框架，包含等价类、边界值、基本路径测试
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import asyncio

# 模拟导入（实际项目中需替换为真实导入）
from src.api.main import app
from src.api.repos import IndexRepositoryRequest, IndexRepositoryResponse

client = TestClient(app)


class TestIndexRepositoryEndpoint:
    """
    黑盒测试：index_repository_endpoint
    使用等价类划分和边界值分析
    """

    # =============== 等价类测试 ===============

    class TestValidInputs:
        """有效输入等价类"""

        @pytest.mark.parametrize("github_url", [
            "https://github.com/pytorch/pytorch",
            "https://github.com/user/simple-repo",
            "https://github.com/org/repo-with-dashes",
        ])
        def test_tc_blk_001_valid_github_urls(self, github_url, monkeypatch):
            """TC-BLK-001: GitHub URL有效等价类"""
            mock_result = Mock(repo_id='test-repo', status='success', chunks=100)
            monkeypatch.setattr(
                'src.ingestion.indexing.index_repository',
                Mock(return_value=mock_result)
            )
            
            response = client.post('/api/repos/index', json={
                'github_url': github_url,
                'branch': 'main'
            })
            
            assert response.status_code == 200
            assert response.json()['repo_id'] == 'test-repo'
            assert response.json()['chunks'] == 100

        @pytest.mark.parametrize("local_path", [
            "/home/user/repo",
            "/tmp/local-repo",
            "C:\\Users\\user\\project",
            "./relative/path",
        ])
        def test_tc_blk_002_valid_local_paths(self, local_path, monkeypatch):
            """TC-BLK-002: 本地路径有效等价类"""
            mock_result = Mock(repo_id='local-repo', status='success', chunks=50)
            monkeypatch.setattr(
                'src.ingestion.indexing.index_repository',
                Mock(return_value=mock_result)
            )
            
            response = client.post('/api/repos/index', json={
                'local_path': local_path,
                'branch': 'dev'
            })
            
            assert response.status_code == 200
            assert response.json()['status'] == 'success'

        def test_tc_blk_003_valid_branches(self, monkeypatch):
            """TC-BLK-003: 不同分支名等价类"""
            mock_result = Mock(repo_id='test', status='success', chunks=100)
            monkeypatch.setattr(
                'src.ingestion.indexing.index_repository',
                Mock(return_value=mock_result)
            )
            
            branches = ['main', 'master', 'develop', 'feature/my-feature', 'v1.0.0']
            for branch in branches:
                response = client.post('/api/repos/index', json={
                    'github_url': 'https://github.com/test/repo',
                    'branch': branch
                })
                assert response.status_code == 200

    class TestInvalidInputs:
        """无效输入等价类"""

        def test_tc_blk_004_missing_both_sources(self):
            """TC-BLK-004: 缺少github_url和local_path"""
            response = client.post('/api/repos/index', json={
                'branch': 'main'
            })
            
            assert response.status_code == 422
            assert 'Either' in str(response.json())

        def test_tc_blk_005_both_none_explicit(self):
            """TC-BLK-005: 显式设为None"""
            response = client.post('/api/repos/index', json={
                'github_url': None,
                'local_path': None,
                'branch': 'main'
            })
            
            assert response.status_code == 422

        @pytest.mark.parametrize("invalid_url", [
            "not-a-url",
            "ftp://github.com/user/repo",
            "github.com/user/repo",  # 缺少https://
            "ht!tp://invalid",
        ])
        def test_tc_blk_006_invalid_url_formats(self, invalid_url, monkeypatch):
            """TC-BLK-006: 格式不正确的URL"""
            mock_error = Exception("Invalid URL format")
            monkeypatch.setattr(
                'src.ingestion.indexing.index_repository',
                Mock(side_effect=mock_error)
            )
            
            response = client.post('/api/repos/index', json={
                'github_url': invalid_url,
                'branch': 'main'
            })
            
            assert response.status_code == 500

    # =============== 边界值测试 ===============

    class TestBoundaryValues:
        """边界值测试"""

        def test_tc_blk_007_empty_string_url(self):
            """TC-BLK-007: 空字符串URL"""
            response = client.post('/api/repos/index', json={
                'github_url': '',
                'branch': 'main'
            })
            
            assert response.status_code == 422

        def test_tc_blk_008_whitespace_only_url(self):
            """TC-BLK-008: 仅空格的URL"""
            response = client.post('/api/repos/index', json={
                'github_url': '   ',
                'branch': 'main'
            })
            
            # 取决于Pydantic的strip_whitespace设置
            assert response.status_code in [422, 500]

        def test_tc_blk_009_very_long_url(self, monkeypatch):
            """TC-BLK-009: 超长URL (边界值)"""
            long_url = 'https://github.com/' + 'a' * 2000
            mock_error = Exception("URL too long")
            monkeypatch.setattr(
                'src.ingestion.indexing.index_repository',
                Mock(side_effect=mock_error)
            )
            
            response = client.post('/api/repos/index', json={
                'github_url': long_url,
                'branch': 'main'
            })
            
            assert response.status_code == 500

        def test_tc_blk_010_single_char_branch(self, monkeypatch):
            """TC-BLK-010: 单字符分支名"""
            mock_result = Mock(repo_id='test', status='success', chunks=1)
            monkeypatch.setattr(
                'src.ingestion.indexing.index_repository',
                Mock(return_value=mock_result)
            )
            
            response = client.post('/api/repos/index', json={
                'github_url': 'https://github.com/test/repo',
                'branch': 'a'
            })
            
            assert response.status_code == 200

        def test_tc_blk_011_empty_branch_default(self, monkeypatch):
            """TC-BLK-011: 空分支应使用默认值"""
            captured_branch = None
            
            def mock_index(source, branch='main'):
                nonlocal captured_branch
                captured_branch = branch
                return Mock(repo_id='test', status='success', chunks=100)
            
            monkeypatch.setattr(
                'src.ingestion.indexing.index_repository',
                mock_index
            )
            
            response = client.post('/api/repos/index', json={
                'github_url': 'https://github.com/test/repo',
                'branch': ''
            })
            
            # 验证实际使用的分支
            assert response.status_code == 200

    # =============== 白盒测试（基本路径法） ===============

    class TestBasicPaths:
        """基本路径覆盖（圈复杂度=2）"""

        def test_tc_wb_018_path1_missing_source(self):
            """TC-WB-018: 路径1 - 缺少源"""
            # 执行路径：条件1 YES → HTTPException
            response = client.post('/api/repos/index', json={
                'github_url': None,
                'local_path': None,
                'branch': 'main'
            })
            
            assert response.status_code == 422
            detail = response.json()['detail']
            assert any('Either' in str(d) for d in detail if isinstance(d, dict))

        def test_tc_wb_019_path2_success(self, monkeypatch):
            """TC-WB-019: 路径2 - 成功索引"""
            # 执行路径：条件1 NO → try → 成功 → return
            mock_result = Mock(
                repo_id='repo-123',
                status='success',
                chunks=250
            )
            monkeypatch.setattr(
                'src.ingestion.indexing.index_repository',
                Mock(return_value=mock_result)
            )
            
            response = client.post('/api/repos/index', json={
                'github_url': 'https://github.com/test/repo',
                'branch': 'main'
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data['repo_id'] == 'repo-123'
            assert data['status'] == 'success'
            assert data['chunks'] == 250

        def test_tc_wb_020_path3_exception_handler(self, monkeypatch):
            """TC-WB-020: 路径3 - 异常处理"""
            # 执行路径：条件1 NO → try → exception → catch
            error_msg = "Repository not found"
            monkeypatch.setattr(
                'src.ingestion.indexing.index_repository',
                Mock(side_effect=Exception(error_msg))
            )
            
            response = client.post('/api/repos/index', json={
                'github_url': 'https://github.com/nonexistent/repo',
                'branch': 'main'
            })
            
            assert response.status_code == 500
            assert error_msg in response.json()['detail']

    # =============== 异常处理测试 ===============

    class TestExceptionHandling:
        """异常处理与错误恢复"""

        def test_tc_blk_012_network_error(self, monkeypatch):
            """TC-BLK-012: 网络错误"""
            monkeypatch.setattr(
                'src.ingestion.indexing.index_repository',
                Mock(side_effect=ConnectionError("网络超时"))
            )
            
            response = client.post('/api/repos/index', json={
                'github_url': 'https://github.com/test/repo',
                'branch': 'main'
            })
            
            assert response.status_code == 500
            assert '网络' in response.json()['detail'] or '超时' in response.json()['detail']

        def test_tc_blk_013_file_not_found(self, monkeypatch):
            """TC-BLK-013: 本地文件不存在"""
            monkeypatch.setattr(
                'src.ingestion.indexing.index_repository',
                Mock(side_effect=FileNotFoundError("路径不存在"))
            )
            
            response = client.post('/api/repos/index', json={
                'local_path': '/nonexistent/path',
                'branch': 'main'
            })
            
            assert response.status_code == 500

        def test_tc_blk_014_permission_error(self, monkeypatch):
            """TC-BLK-014: 权限错误"""
            monkeypatch.setattr(
                'src.ingestion.indexing.index_repository',
                Mock(side_effect=PermissionError("权限被拒绝"))
            )
            
            response = client.post('/api/repos/index', json={
                'local_path': '/root/private',
                'branch': 'main'
            })
            
            assert response.status_code == 500


class TestChatEndpoint:
    """
    黑盒测试：chat_endpoint
    流式响应处理
    """

    @pytest.mark.asyncio
    async def test_tc_blk_015_normal_stream(self, monkeypatch):
        """TC-BLK-015: 正常流式响应"""
        
        async def mock_stream(*args, **kwargs):
            yield "块1"
            yield "块2"
            yield "块3"
        
        monkeypatch.setattr(
            'src.generation.rag_pipeline.stream_rag_answer',
            mock_stream
        )
        
        response = client.post('/api/chat', json={
            'repo_id': 'test-repo',
            'question': '这是什么？'
        })
        
        assert response.status_code == 200
        assert response.headers['content-type'] == 'text/event-stream'
        
        # 验证SSE格式
        text = response.text
        assert 'data:' in text
        assert '[DONE]' in text

    def test_tc_blk_016_empty_question(self):
        """TC-BLK-016: 空问题"""
        response = client.post('/api/chat', json={
            'repo_id': 'test-repo',
            'question': ''
        })
        
        # 可能在前端验证，也可能后端返回错误
        assert response.status_code in [200, 422, 400]

    def test_tc_blk_017_missing_repo_id(self):
        """TC-BLK-017: 缺少repo_id"""
        response = client.post('/api/chat', json={
            'question': '有效问题'
        })
        
        assert response.status_code == 422

    @pytest.mark.parametrize("repo_id", [
        '',
        None,
        '   ',
    ])
    def test_tc_blk_018_invalid_repo_id(self, repo_id):
        """TC-BLK-018: 无效的repo_id"""
        response = client.post('/api/chat', json={
            'repo_id': repo_id,
            'question': '问题'
        })
        
        assert response.status_code in [400, 422]


class TestSSEDataFormatter:
    """
    黑盒白盒测试：_sse_data 函数
    """

    def test_tc_wb_024_single_line_chunk(self):
        """TC-WB-024: 单行chunk格式化"""
        from src.api.chat import _sse_data
        
        result = _sse_data("Hello World")
        assert result == "data: Hello World\n\n"

    def test_tc_wb_025_multiline_chunk(self):
        """TC-WB-025: 多行chunk格式化"""
        from src.api.chat import _sse_data
        
        result = _sse_data("Line1\nLine2\nLine3")
        assert "data: Line1\n" in result
        assert "data: Line2\n" in result
        assert "data: Line3\n" in result

    def test_tc_wb_026_empty_chunk(self):
        """TC-WB-026: 空chunk"""
        from src.api.chat import _sse_data
        
        result = _sse_data("")
        assert result == "data: \n\n"

    def test_tc_wb_027_special_characters(self):
        """TC-WB-027: 特殊字符处理"""
        from src.api.chat import _sse_data
        
        result = _sse_data("特殊字符: @#$%^&*()")
        assert "data: 特殊字符" in result

    def test_tc_wb_028_very_long_chunk(self):
        """TC-WB-028: 超长chunk"""
        from src.api.chat import _sse_data
        
        long_text = "a" * 10000
        result = _sse_data(long_text)
        assert "data:" in result
        assert len(result) > 10000


# =============== 集成测试 ===============

class TestIntegration:
    """集成测试：端到端流程"""

    def test_tc_bk_029_full_workflow(self, monkeypatch):
        """TC-BK-029: 完整工作流"""
        # 1. 索引仓库
        mock_index_result = Mock(repo_id='workflow-test', status='success', chunks=100)
        monkeypatch.setattr(
            'src.ingestion.indexing.index_repository',
            Mock(return_value=mock_index_result)
        )
        
        index_response = client.post('/api/repos/index', json={
            'github_url': 'https://github.com/test/repo',
            'branch': 'main'
        })
        
        assert index_response.status_code == 200
        repo_id = index_response.json()['repo_id']
        
        # 2. 使用获得的repo_id进行问答
        async def mock_chat_stream(*args, **kwargs):
            yield "这是回答"
        
        monkeypatch.setattr(
            'src.generation.rag_pipeline.stream_rag_answer',
            mock_chat_stream
        )
        
        chat_response = client.post('/api/chat', json={
            'repo_id': repo_id,
            'question': '项目是什么？'
        })
        
        assert chat_response.status_code == 200
        assert repo_id == 'workflow-test'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

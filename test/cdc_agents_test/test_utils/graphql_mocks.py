"""
GraphQL mock utilities for CDC agents testing
"""
import json
import typing
import unittest
from dataclasses import dataclass, field
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock
import uuid


@dataclass
class MockCommit:
    """Mock commit data structure"""
    hash: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    message: str = "Mock commit message"
    author: str = "test@example.com"
    author_date: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    files_changed: int = 1
    insertions: int = 10
    deletions: int = 5
    diff: str = "mock diff content"
    parent_hashes: typing.List[str] = field(default_factory=list)


@dataclass
class MockCodeSearchResult:
    """Mock code search result"""
    file: str
    line: int
    content: str
    context: str = ""
    score: float = 0.95
    language: str = "python"
    repository: str = "/Users/hayde/IdeaProjects/test"


@dataclass
class MockFileContent:
    """Mock file content structure"""
    path: str
    content: str
    language: str = "python"
    size: int = field(init=False)
    last_modified: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self):
        self.size = len(self.content)


class GraphQLMockBuilder:
    """Builder for creating GraphQL mock responses"""

    @staticmethod
    def success_response(data: dict) -> dict:
        """Create a successful GraphQL response"""
        return {
            "data": data,
            "errors": None
        }

    @staticmethod
    def error_response(errors: typing.List[dict]) -> dict:
        """Create an error GraphQL response"""
        return {
            "data": None,
            "errors": errors
        }

    @staticmethod
    def partial_response(data: dict, errors: typing.List[dict]) -> dict:
        """Create a partial success/error response"""
        return {
            "data": data,
            "errors": errors
        }


class CDCGraphQLMocker:
    """Mock provider for CDC GraphQL operations"""

    def __init__(self):
        self.commits: typing.List[MockCommit] = []
        self.search_results: typing.List[MockCodeSearchResult] = []
        self.files: typing.Dict[str, MockFileContent] = {}
        self.staged_changes: typing.Dict[str, str] = {}

    def add_mock_commit(self, commit: MockCommit):
        """Add a mock commit to the repository"""
        self.commits.append(commit)

    def add_mock_search_result(self, result: MockCodeSearchResult):
        """Add a mock search result"""
        self.search_results.append(result)

    def add_mock_file(self, file: MockFileContent):
        """Add a mock file to the repository"""
        self.files[file.path] = file

    def mock_code_search(self, query: str, limit: int = 10) -> dict:
        """Mock code search operation"""
        # Filter results based on query
        filtered_results = [
            r for r in self.search_results
            if query.lower() in r.content.lower() or query.lower() in r.file.lower()
        ][:limit]

        return GraphQLMockBuilder.success_response({
            "codeSearch": {
                "results": [
                    {
                        "file": r.file,
                        "line": r.line,
                        "content": r.content,
                        "context": r.context,
                        "score": r.score,
                        "language": r.language,
                        "repository": r.repository
                    }
                    for r in filtered_results
                ],
                "total": len(filtered_results),
                "hasMore": len(filtered_results) == limit
            }
        })

    def mock_commit_diff_context(self, commit_hash: str) -> dict:
        """Mock commit diff context operation"""
        commit = next((c for c in self.commits if c.hash == commit_hash), None)

        if not commit:
            return GraphQLMockBuilder.error_response([{
                "message": f"Commit {commit_hash} not found",
                "path": ["commitDiffContext"],
                "extensions": {"code": "COMMIT_NOT_FOUND"}
            }])

        return GraphQLMockBuilder.success_response({
            "commitDiffContext": {
                "commit": {
                    "hash": commit.hash,
                    "message": commit.message,
                    "author": commit.author,
                    "authorDate": commit.author_date,
                    "diff": commit.diff,
                    "filesChanged": commit.files_changed,
                    "insertions": commit.insertions,
                    "deletions": commit.deletions
                },
                "parentCommits": [
                    {"hash": h} for h in commit.parent_hashes
                ],
                "success": True
            }
        })

    def mock_retrieve_code_context(self, paths: typing.List[str]) -> dict:
        """Mock code context retrieval"""
        found_files = []
        not_found = []

        for path in paths:
            if path in self.files:
                file = self.files[path]
                found_files.append({
                    "path": file.path,
                    "content": file.content,
                    "language": file.language,
                    "size": file.size,
                    "lastModified": file.last_modified
                })
            else:
                not_found.append(path)

        response_data = {
            "codeContext": {
                "files": found_files,
                "success": len(not_found) == 0
            }
        }

        if not_found:
            return GraphQLMockBuilder.partial_response(
                response_data,
                [{
                    "message": f"Files not found: {', '.join(not_found)}",
                    "path": ["codeContext", "files"],
                    "extensions": {"code": "FILES_NOT_FOUND", "files": not_found}
                }]
            )

        return GraphQLMockBuilder.success_response(response_data)

    def mock_repository_staged(self) -> dict:
        """Mock repository staged changes"""
        return GraphQLMockBuilder.success_response({
            "repositoryStaged": {
                "staged": [
                    {
                        "path": path,
                        "status": "modified",
                        "diff": diff
                    }
                    for path, diff in self.staged_changes.items()
                ],
                "total": len(self.staged_changes),
                "success": True
            }
        })

    def mock_apply_staged(self, paths: typing.List[str]) -> dict:
        """Mock applying staged changes"""
        applied = []
        failed = []

        for path in paths:
            if path in self.staged_changes:
                applied.append(path)
                # Update the file content
                if path in self.files:
                    # Apply the diff (simplified)
                    self.files[path].content += f"\n# Staged changes applied"
            else:
                failed.append(path)

        if failed:
            return GraphQLMockBuilder.partial_response(
                {
                    "applyStaged": {
                        "applied": applied,
                        "failed": failed,
                        "success": False
                    }
                },
                [{
                    "message": f"Failed to apply staged changes for: {', '.join(failed)}",
                    "path": ["applyStaged"],
                    "extensions": {"code": "APPLY_FAILED", "paths": failed}
                }]
            )

        return GraphQLMockBuilder.success_response({
            "applyStaged": {
                "applied": applied,
                "failed": [],
                "success": True
            }
        })

    def mock_reset_staged(self) -> dict:
        """Mock resetting staged changes"""
        count = len(self.staged_changes)
        self.staged_changes.clear()

        return GraphQLMockBuilder.success_response({
            "resetStaged": {
                "count": count,
                "success": True
            }
        })


class MockCDCToolProvider:
    """Mock CDC tool provider for testing"""

    def __init__(self, graphql_mocker: CDCGraphQLMocker):
        self.graphql_mocker = graphql_mocker
        self._setup_mock_tools()

    def _setup_mock_tools(self):
        """Set up mock tool implementations"""
        self.perform_commit_diff_context_git_actions = Mock(
            side_effect=lambda commit_hash, **kwargs:
            self.graphql_mocker.mock_commit_diff_context(commit_hash)
        )

        self.retrieve_commit_diff_code_context = Mock(
            side_effect=lambda paths, **kwargs:
            self.graphql_mocker.mock_retrieve_code_context(paths)
        )

        self.retrieve_current_repository_staged = Mock(
            side_effect=lambda **kwargs:
            self.graphql_mocker.mock_repository_staged()
        )

        self.apply_last_staged = Mock(
            side_effect=lambda paths, **kwargs:
            self.graphql_mocker.mock_apply_staged(paths)
        )

        self.reset_any_staged = Mock(
            side_effect=lambda **kwargs:
            self.graphql_mocker.mock_reset_staged()
        )


def create_sample_repository():
    """Create a sample repository with mock data for testing"""
    mocker = CDCGraphQLMocker()

    # Add sample commits
    mocker.add_mock_commit(MockCommit(
        hash="abc123",
        message="Fix critical bug in payment processing",
        author="developer@example.com",
        files_changed=3,
        insertions=45,
        deletions=12,
        diff="""
diff --git a/src/payment.py b/src/payment.py
@@ -10,5 +10,8 @@ def process_payment(amount):
-    return False  # Bug: always returns False
+    if amount > 0:
+        return True
+    return False
"""
    ))

    mocker.add_mock_commit(MockCommit(
        hash="def456",
        message="Add unit tests for payment module",
        author="tester@example.com",
        files_changed=1,
        insertions=50,
        deletions=0,
        parent_hashes=["abc123"]
    ))

    # Add sample search results
    mocker.add_mock_search_result(MockCodeSearchResult(
        file="/Users/hayde/IdeaProjects/example/src/payment.py",
        line=15,
        content="def process_payment(amount):",
        context="    # Process payment transaction\n    def process_payment(amount):\n        if amount > 0:"
    ))

    mocker.add_mock_search_result(MockCodeSearchResult(
        file="/Users/hayde/IdeaProjects/example/tests/test_payment.py",
        line=8,
        content="def test_process_payment():",
        context="class TestPayment(unittest.TestCase):\n    def test_process_payment():\n        assert process_payment(100) == True"
    ))

    # Add sample files
    mocker.add_mock_file(MockFileContent(
        path="/Users/hayde/IdeaProjects/example/src/payment.py",
        content="""
# Payment processing module

def process_payment(amount):
    \"\"\"Process a payment transaction\"\"\"
    if amount > 0:
        return True
    return False

def validate_payment(payment_data):
    \"\"\"Validate payment data\"\"\"
    required_fields = ['amount', 'currency', 'recipient']
    return all(field in payment_data for field in required_fields)
"""
    ))

    mocker.add_mock_file(MockFileContent(
        path="/Users/hayde/IdeaProjects/example/README.md",
        content="""
# Example Project

This is a sample project for testing CDC agents.

## Features
- Payment processing
- Data validation
- Unit testing
""",
        language="markdown"
    ))

    return mocker


def patch_cdc_tools(test_method):
    """Decorator to patch CDC tools with mocks for testing"""
    def wrapper(self, *args, **kwargs):
        mocker = create_sample_repository()
        provider = MockCDCToolProvider(mocker)

        with unittest.mock.patch(
            'cdc_agents.agents.cdc_server_agent.CdcServerAgentToolCallProvider',
            return_value=provider
        ):
            # Pass the mocker to the test for custom setup
            return test_method(self, mocker, *args, **kwargs)

    return wrapper

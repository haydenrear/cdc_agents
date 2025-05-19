import typing
from enum import Enum
from typing import List, Optional, Dict, Any, Union

import numpy as np
from pydantic import BaseModel, Field, GetCoreSchemaHandler
import pydantic
from pydantic_core import CoreSchema


class GitAction(str, Enum):
    ADD_BRANCH = "ADD_BRANCH"
    REMOVE_BRANCH = "REMOVE_BRANCH"
    UPDATE_HEAD = "UPDATE_HEAD"
    REMOVE_REPO = "REMOVE_REPO"
    RESET_HEAD = "RESET_HEAD"
    PARSE_BLAME_TREE = "PARSE_BLAME_TREE"
    SET_EMBEDDINGS = "SET_EMBEDDINGS"
    ADD_REPO = "ADD_REPO"
    DROP_COMMIT = "DROP_COMMIT"
    CHERRY_PICK = "CHERRY_PICK"
    REVERT = "REVERT"
    MERGE = "MERGE"
    ADD_AST = "ADD_AST"

# Enums
class DocumentType(str, Enum):
    COMMIT_DIFF = "CommitDiff"
    COMMIT_DIFF_CLUSTER = "CommitDiffCluster"
    COMMIT_DIFF_ITEM = "CommitDiffItem"
    EMBEDDED_GIT_ITEM = "EmbeddedGitItem"


class ContextType(str, Enum):
    LIB = "Lib"
    NOTE = "Note"
    ADDITIONAL = "Additional"
    BUILD_OUTPUT = "BuildOutput"
    RUNTIME_LOG = "RuntimeLog"
    SCREEN_SHARE = "ScreenShare"
    SCREENSHOT = "Screenshot"
    EMBEDDED = "Embedded"


class MpcContextType(str, Enum):
    EMBEDDED = "EMBEDDED"
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    UNKNOWN = "UNKNOWN"


class McpServer(str, Enum):
    POSTGRES = "Postgres"


class GitOperation(str, Enum):
    ADD_BRANCH = "ADD_BRANCH"
    REMOVE_BRANCH = "REMOVE_BRANCH"
    UPDATE_HEAD = "UPDATE_HEAD"
    REMOVE_REPO = "REMOVE_REPO"
    RESET_HEAD = "RESET_HEAD"
    PARSE_BLAME_TREE = "PARSE_BLAME_TREE"
    SET_EMBEDDINGS = "SET_EMBEDDINGS"
    ADD_REPO = "ADD_REPO"
    DROP_COMMIT = "DROP_COMMIT"
    CHERRY_PICK = "CHERRY_PICK"
    REVERT = "REVERT"
    MERGE = "MERGE"
    ADD_AST = "ADD_AST"


class DiffType(str, Enum):
    ADD = "ADD"
    MODIFY = "MODIFY"
    DELETE = "DELETE"
    RENAME = "RENAME"
    COPY = "COPY"


class EditType(str, Enum):
    INSERT = "INSERT"
    DELETE = "DELETE"
    REPLACE = "REPLACE"
    EMPTY = "EMPTY"


class RepoStatus(str, Enum):
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    FAIL = "FAIL"
    ASYNC = "ASYNC"


# Base models
class Error(BaseModel):
    message: str


class SessionKey(BaseModel):
    key: str


class ServerSessionKey(BaseModel):
    key: str


class GitRepo(BaseModel):
    path: str


class GitBranch(BaseModel):
    branch: str


# Context models
class FileStream(BaseModel):
    fileName: str


class MpcContext(BaseModel):
    type: str


class MpcEmbeddedContext(MpcContext):
    uri: str
    mimeType: str


class MpcTextContext(MpcContext):
    text: str


class MpcUnknownContext(MpcContext):
    value: str


class MpcImageContext(MpcContext):
    data: str
    mimeType: str


class ContextData(BaseModel):
    ctxData: str
    contextType: ContextType
    prev: Optional[List[str]] = None
    mimeType: Optional[str] = None


class ModelContextProtocolContext(BaseModel):
    underlying: FileStream
    contextType: MpcContextType
    serializedContext: str


class LibContext(BaseModel):
    files: List[str]
    underlying: FileStream


class NoteContext(BaseModel):
    value: str
    underlying: FileStream


class AdditionalContext(BaseModel):
    value: str
    underlying: FileStream


class BuildContext(BaseModel):
    error: List[str]
    buildOutput: str
    underlying: FileStream


class RuntimeLogContext(BaseModel):
    stackTrace: List[str]
    underlying: FileStream


class McpServerInstanceTy(BaseModel):
    mcp: McpServer
    name: str


class McpContext(BaseModel):
    mcpServer: McpServerInstanceTy
    underlying: FileStream


# Diff models
class EditLocation(BaseModel):
    begin: int
    end: int


class EditLocations(BaseModel):
    locationA: EditLocation
    locationB: EditLocation


class EditLocationInput(BaseModel):
    begin: int
    end: int


class EditLocationsInput(BaseModel):
    locationA: EditLocationInput
    locationB: EditLocationInput


class HunkLines(BaseModel):
    newStartLine: int
    newLineCount: int
    linesAdded: int
    linesDeleted: int


class HunkLinesInput(BaseModel):
    newStartLine: int
    newLineCount: int
    linesAdded: int
    linesDeleted: int


class CommitDiffEdit(BaseModel):
    diffType: EditType
    editLocations: EditLocations
    contentChange: List[str]


class CommitDiffEditInput(BaseModel):
    diffType: EditType
    editLocations: EditLocationsInput
    contentChange: List[str]
    oldContent: List[str]


class CommitDiffHunk(BaseModel):
    commitDiffEdits: List[CommitDiffEdit]
    hunkLines: HunkLines


class CommitDiffHunkInput(BaseModel):
    commitDiffEdits: List[CommitDiffEditInput]
    hunkLines: HunkLinesInput


class CommitDiffContent(BaseModel):
    hunks: List[CommitDiffHunk]
    content: str


class CommitDiffContentInput(BaseModel):
    hunks: List[CommitDiffHunkInput]
    content: str


class Diff(BaseModel):
    newPath: str
    oldPath: str
    newFileMode: Optional[int] = None
    oldFileMode: Optional[int] = None
    diffType: DiffType
    content: CommitDiffContent


class DiffInput(BaseModel):
    newPath: str
    oldPath: str
    newFileMode: Optional[int] = None
    oldFileMode: Optional[int] = None
    diffType: DiffType
    content: CommitDiffContentInput


class PrevDiff(BaseModel):
    underlyingDiff: DiffInput


class PromptDiff(BaseModel):
    underlyingDiff: DiffInput


class PromptDiffOut(BaseModel):
    underlyingDiff: Diff


class CommitMessage(BaseModel):
    value: str


class ServerCommitMessage(BaseModel):
    value: str


# Repository and commit models
class GitRepoValidatableDiffItem(BaseModel):
    value: str


class GitRepoValidatableDiff(BaseModel):
    items: List[GitRepoValidatableDiffItem]
    numDiffs: int


class RelevantFileItem(BaseModel):
    name: str
    linesWithLineNumbers: str


class RelevantFileItemOut(BaseModel):
    name: str
    linesWithLineNumbers: str


class RelevantFileItems(BaseModel):
    beforeApplyDiff: RelevantFileItem
    afterApplyDiff: RelevantFileItem


class RelevantFileItemsOut(BaseModel):
    beforeApplyDiff: RelevantFileItemOut
    afterApplyDiff: RelevantFileItemOut


class Staged(BaseModel):
    diffs: List[PromptDiff]
    files: Optional[List[RelevantFileItems]] = None


class StagedOut(BaseModel):
    files: List[RelevantFileItemsOut]


class PrevCommit(BaseModel):
    diffs: List[PrevDiff] = []
    commitMessage: Optional[CommitMessage] = None
    sessionKey: Optional[SessionKey] = None


# Request models
class CommitId(BaseModel):
    sha1: str


class MergeContext(BaseModel):
    fromCommit: CommitId
    toCommit: CommitId


class UpdateHeadCtx(BaseModel):
    commit: CommitId


class RebaseContext(BaseModel):
    fromCommit: CommitId
    toCommit: CommitId


class CherryPickContext(BaseModel):
    toPick: CommitId


class ResetContext(BaseModel):
    toResetTo: CommitId


class DropContext(BaseModel):
    toDrop: CommitId


class AddBranchContext(BaseModel):
    patterns: List[str]


class TagContext(BaseModel):
    toTag: CommitId
    tagName: str


class BlameTreeOptions(BaseModel):
    maxBlameTreeDepth: Optional[int] = None
    squashEmbed: Optional[bool] = None
    maxTimeBlameTree: Optional[int] = None
    maxTimePerBlameTreeRefRecursive: Optional[int] = None
    maxTimePerBlameTreeCommitRef: Optional[int] = None
    maxTimePerBlameTreeNoSquash: Optional[int] = None
    maxTimePerRetrieveBlameNodeChildren: Optional[int] = None
    maxCommitDiffs: Optional[int] = None
    maxCommitsPerPath: Optional[int] = None
    maxDepthSingleBlameTree: Optional[int] = None
    topKCommitsPerSingleBlameTree: Optional[int] = None
    maxPathsParsedCommitDiffCluster: Optional[int] = None
    maxPathsConsideredGreedyDistinct: Optional[int] = None
    maxCommitDiffClustersForBranch: Optional[int] = None


class ParseGitOptions(BaseModel):
    maxCommitDepth: Optional[int] = None
    maxCommitDiffs: Optional[int] = None


class RagOptions(BaseModel):
    blameTreeOptions: Optional[BlameTreeOptions] = None
    parseGitOptions: Optional[ParseGitOptions] = None


class GitRepoQueryRequest(BaseModel):
    gitRepo: Optional[GitRepo] = None
    gitBranch: Optional[GitBranch] = None
    sessionKey: Optional[SessionKey] = None


class PromptingOptions(BaseModel):
    numKClosestCommits: Optional[int] = None
    includeRepoClosestCommits: Optional[List[GitRepoQueryRequest]] = None
    numLinesAround: Optional[int] = None
    numTriesWithTools: Optional[int] = None
    numFilesPerChatItem: Optional[int] = None
    numChatItemsTotal: Optional[int] = None
    maxDiffsPerFile: Optional[int] = None
    doPerformBlameTree: Optional[bool] = None

class GitRepoRequestOptions(BaseModel):
    skipValidation: Optional[bool] = None
    promptingOptions: Optional[PromptingOptions] = None

class CodeQuery(BaseModel):
    codeString: Optional[str] = None
    codeEmbedding: Optional[Any] = None


class PrevRequests(BaseModel):
    prevCommits: PrevCommit
    contextData: List[ContextData]


class GitRepoPromptingRequest(BaseModel):
    gitRepo: GitRepo
    commitMessage: Optional[CommitMessage] = None
    branchName: str
    contextData: List[ContextData] = []
    prevRequests: List[PrevRequests] = []
    sessionKey: SessionKey
    prev: Optional[PrevCommit] = None
    staged: Optional[Staged] = None
    ragOptions: Optional[RagOptions] = None
    gitRepoRequestOptions: Optional[GitRepoRequestOptions] = None
    lastRequestStagedApplied: Optional[Staged] = None
    codeQuery: Optional[CodeQuery] = None
    async_: Optional[bool] = Field(default=False, alias="async")


class GitRepositoryRequest(BaseModel):
    operation: List[GitOperation]
    gitBranch: GitBranch
    gitRepo: GitRepo
    sessionKey: Optional[SessionKey] = None
    merge: Optional[MergeContext] = None
    rebase: Optional[RebaseContext] = None
    cherryPick: Optional[CherryPickContext] = None
    reset: Optional[ResetContext] = None
    drop: Optional[DropContext] = None
    tag: Optional[TagContext] = None
    updateHead: Optional[UpdateHeadCtx] = None
    gitRepoRequestOptions: Optional[GitRepoRequestOptions] = None
    ragOptions: Optional[RagOptions] = None
    async_: Optional[bool] = Field(default=False, alias="async")


# Result models
class NextCommit(BaseModel):
    diffs: List[Diff]
    commitMessage: ServerCommitMessage
    sessionKey: Optional[ServerSessionKey] = None
    errors: Optional[List[Error]] = None
    ctx: Optional[List[MpcContext]] = None


class GitRepoResult(BaseModel):
    branch: Optional[str] = None
    url: Optional[str] = None
    repoStatus: Optional[List[RepoStatus]] = None
    error: Optional[List[Error]] = None
    sessionKey: Optional[ServerSessionKey] = None
    clientServerDiffs: Optional[List[GitRepoValidatableDiff]] = None


class GitStagedResult(BaseModel):
    staged: StagedOut
    sessionKey: ServerSessionKey
    error: Optional[List[Error]] = None


class CommitDiffFileItem(BaseModel):
    path: str
    source: str


class CommitDiffFileResult(BaseModel):
    sessionKey: ServerSessionKey
    files: List[CommitDiffFileItem]
    errs: Optional[List[Error]] = None



class Embedding(BaseModel):
    value: typing.List[float]

    @pydantic.field_serializer('value')
    def serialize_value(self, value_to_serialize):
        return np.array(value_to_serialize)


class EmbeddingResult(BaseModel):
    value: Embedding
    err: Optional[List[Error]] = None


class Embeddings(BaseModel):
    values: List[EmbeddingResult]
    sessionKey: ServerSessionKey


class DocumentRequest(BaseModel):
    branch: Optional[str] = None
    url: Optional[str] = None
    documentToMatch: str


class EmbeddingQuery(BaseModel):
    matchDoc: DocumentRequest
    returnDocs: int = 1
    sessionKey: Optional[SessionKey] = None
    documentType: Optional[DocumentType] = None


class EmbeddedDocument(BaseModel):
    documentType: DocumentType
    document: str


class EmbeddingQueryResult(BaseModel):
    embeddedDocuments: List[EmbeddedDocument]
    sessionKey: ServerSessionKey


class EmbeddingRequest(BaseModel):
    documents: List[str]
    sessionKey: Optional[SessionKey] = None


# Additional models for CDC Agent
class CdcGitRepoBranch(BaseModel):
    """CDC-specific GitRepo model that matches the dataclass in cdc_server_agent.py"""
    git_repo_url: str
    git_branch: str = "main"


# Utility class for GraphQL HTTP operations
class GraphQLResponse(BaseModel):
    """Generic GraphQL response model"""
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[Dict[str, Any]]] = None
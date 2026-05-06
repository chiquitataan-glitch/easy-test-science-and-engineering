from datetime import datetime
from pydantic import BaseModel, model_validator


class GeneratePaperRequest(BaseModel):
    courseName: str
    fileId: str | None = None
    documentIds: list[str] = []
    config: dict | None = None
    category: str = "general"

    @model_validator(mode="after")
    def normalize_doc_ids(self):
        if self.fileId and not self.documentIds:
            self.documentIds = [self.fileId]
        return self


class QuestionItem(BaseModel):
    id: str | None = None
    questionNo: int
    questionType: str
    content: str
    options: list[dict] | None = None
    answer: str
    analysis: str | None = None
    knowledgePoints: list[str] | None = None
    difficulty: str | None = None
    score: float | None = None
    sourceChunkIds: list[str] | None = None
    isCrossDoc: bool = False


class PaperResponse(BaseModel):
    id: str
    userId: str
    courseName: str
    paperTitle: str | None = None
    paperJson: dict | None = None
    status: str
    questionCount: int
    totalScore: float | None = None
    qualityScore: float | None = None
    durationSeconds: float | None = None
    category: str | None = None
    config: dict | None = None
    retrievalMode: str | None = None
    knowledgeSummary: dict | None = None
    qualityReport: dict | None = None
    questions: list[QuestionItem] = []
    failReason: str | None = None
    modelName: str | None = None
    promptVersion: str | None = None
    tokenUsage: int | None = None
    originalPaperId: str | None = None
    createdAt: str | None = None

"""Public API contracts for custom models, used by the MCP adapter."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ModelId = Annotated[str, Field(pattern=r"^[a-f0-9]{32}$")]
Version = Annotated[str, Field(min_length=1, max_length=100)]
Name = Annotated[str, Field(min_length=1, max_length=100)]
Instructions = Annotated[str, Field(min_length=3, max_length=2000)]
RequestId = Annotated[str, Field(pattern=r"^[A-Za-z0-9_-]{16,100}$")]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Label(Input):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def nonblank(self):
        if not self.name.strip() or not self.description.strip():
            raise ValueError("Label names and definitions must contain text")
        return self


class TrainingChunk(Input):
    text: str = Field(min_length=1, max_length=2_000_000)
    document_id: str = Field(min_length=1, max_length=1024)

    @model_validator(mode="after")
    def nonblank(self):
        if not self.text.strip() or not self.document_id.strip():
            raise ValueError("Training text and document IDs must contain text")
        return self


class Instance(Input):
    text: str = Field(min_length=1, max_length=4000)
    id: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def nonblank(self):
        if not self.text.strip():
            raise ValueError("Input text must contain text")
        return self


class Document(Input):
    text: str = Field(min_length=1, max_length=2_000_000)
    id: str | None = Field(default=None, max_length=1024)

    @model_validator(mode="after")
    def nonblank(self):
        if not self.text.strip():
            raise ValueError("Document text must contain text")
        return self


class Output(BaseModel):
    # Only declared public fields cross into the MCP host.
    model_config = ConfigDict(extra="ignore", allow_inf_nan=False)


class OutputLabel(Output):
    """A label as reported by the API. Tolerates additive fields and legacy shapes."""

    id: str
    name: str = ""
    description: str = ""


class Model(Output):
    id: ModelId
    name: str = ""
    version: Version
    labels: list[OutputLabel] = Field(default_factory=list)
    document_types: list[str] = Field(default_factory=list)
    created_at: str = ""


class ModelList(Output):
    models: list[Model]
    total: int = Field(ge=0)

    @model_validator(mode="after")
    def complete(self):
        if self.total != len(self.models):
            raise ValueError("Incomplete model list")
        return self


class TrainingStatus(Output):
    # model_id is the contract; id is an alias some responses repeat.
    id: ModelId | None = None
    model_id: ModelId
    name: str = ""
    status: Literal["creating", "ready", "failed", "canceled"]
    progress: float = Field(default=0, ge=0, le=100)
    created_at: str = ""
    labels: list[OutputLabel] = Field(default_factory=list)
    version: Version | None = None
    error: str | None = None

    @model_validator(mode="after")
    def consistent(self):
        if (self.id is not None and self.id != self.model_id) or (self.status == "ready") != (self.version is not None):
            raise ValueError("Inconsistent model status")
        self.error = "Model creation failed. Check the run in My models." if self.status == "failed" else None
        return self


class Prediction(Output):
    index: int = Field(ge=0)
    id: str | None = None
    label_id: str
    label: str
    score: float = Field(ge=0, le=1)
    probabilities: dict[str, Annotated[float, Field(ge=0, le=1)]]

    @model_validator(mode="after")
    def distribution(self):
        if self.label_id not in self.probabilities or abs(sum(self.probabilities.values()) - 1) > 1e-4:
            raise ValueError("Invalid prediction probabilities")
        if abs(self.score - self.probabilities[self.label_id]) > 1e-4:
            raise ValueError("Inconsistent prediction score")
        if self.score + 1e-4 < max(self.probabilities.values()):
            raise ValueError("Prediction label does not match the highest score")
        return self


class InstancePrediction(Prediction):
    """One prediction per submitted text. chunks > 1 means the text was split and averaged."""

    chunks: int = Field(default=1, ge=1)


class ClassifyResult(Output):
    model_id: ModelId
    version: Version
    task: Literal["sequence_classification"]
    predictions: list[InstancePrediction] = Field(min_length=1, max_length=128)


class ChunkPrediction(Prediction):
    document_index: int = Field(ge=0)
    chunk_index: int = Field(ge=0)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=1)


class DocumentResult(Output):
    model_id: ModelId
    version: Version
    task: Literal["chunk_classification"]
    total_chunks: int = Field(ge=1, le=128)
    predictions: list[ChunkPrediction] = Field(min_length=1, max_length=128)

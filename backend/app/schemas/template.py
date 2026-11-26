from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

HEX_COLOR_PATTERN = r"^#[0-9a-fA-F]{6}$"


class TemplateStatus(str, Enum):
    ACTIVA = "ACTIVA"
    ARCHIVADA = "ARCHIVADA"


class TokenColors(BaseModel):
    model_config = ConfigDict(extra="ignore")

    accent: str = Field("#0ea5e9", pattern=HEX_COLOR_PATTERN)
    background: str = Field("#ffffff", pattern=HEX_COLOR_PATTERN)
    surface: str = Field("#f8fafc", pattern=HEX_COLOR_PATTERN)
    text: str = Field("#0f172a", pattern=HEX_COLOR_PATTERN)
    textMuted: str = Field("#64748b", pattern=HEX_COLOR_PATTERN)
    border: str = Field("#e2e8f0", pattern=HEX_COLOR_PATTERN)
    link: str = Field("#0369a1", pattern=HEX_COLOR_PATTERN)
    codeBg: str = Field("#0f172a", pattern=HEX_COLOR_PATTERN)


class TokenTypography(BaseModel):
    model_config = ConfigDict(extra="ignore")

    headingFont: str = Field("Inter, ui-sans-serif, system-ui, sans-serif", max_length=200)
    bodyFont: str = Field("Inter, ui-sans-serif, system-ui, sans-serif", max_length=200)
    codeFont: str = Field("ui-monospace, SFMono-Regular, Menlo, monospace", max_length=200)
    baseSize: int = Field(17, ge=14, le=22)
    lineHeight: float = Field(1.7, ge=1.2, le=2.2)


class TokenLayout(BaseModel):
    model_config = ConfigDict(extra="ignore")

    maxWidth: int = Field(720, ge=480, le=1100)
    density: Literal["compact", "comfortable", "spacious"] = "comfortable"
    headerStyle: Literal["banner", "editorial-centered", "split-cover", "minimal"] = "minimal"
    imageRadius: int = Field(8, ge=0, le=32)
    shadow: Literal["none", "soft", "elevated"] = "soft"


class CalloutColorPair(BaseModel):
    model_config = ConfigDict(extra="ignore")

    bg: str = Field(..., pattern=HEX_COLOR_PATTERN)
    border: str = Field(..., pattern=HEX_COLOR_PATTERN)


class TokenCalloutBlocks(BaseModel):
    model_config = ConfigDict(extra="ignore")

    info: CalloutColorPair = Field(default_factory=lambda: CalloutColorPair(bg="#e0f2fe", border="#0284c7"))
    tip: CalloutColorPair = Field(default_factory=lambda: CalloutColorPair(bg="#dcfce7", border="#16a34a"))
    warning: CalloutColorPair = Field(default_factory=lambda: CalloutColorPair(bg="#fef9c3", border="#ca8a04"))
    danger: CalloutColorPair = Field(default_factory=lambda: CalloutColorPair(bg="#fee2e2", border="#dc2626"))


class TokenQuoteBlock(BaseModel):
    model_config = ConfigDict(extra="ignore")

    borderColor: str = Field("#0ea5e9", pattern=HEX_COLOR_PATTERN)
    style: Literal["normal", "italic"] = "italic"


class TokenCodeBlock(BaseModel):
    model_config = ConfigDict(extra="ignore")

    radius: int = Field(8, ge=0, le=32)
    showLanguageBadge: bool = True


class TokenBlocks(BaseModel):
    model_config = ConfigDict(extra="ignore")

    callout: TokenCalloutBlocks = Field(default_factory=TokenCalloutBlocks)
    quote: TokenQuoteBlock = Field(default_factory=TokenQuoteBlock)
    code: TokenCodeBlock = Field(default_factory=TokenCodeBlock)


class TemplateTokens(BaseModel):
    model_config = ConfigDict(extra="ignore")

    version: int = Field(1, ge=1)
    colors: TokenColors = Field(default_factory=TokenColors)
    typography: TokenTypography = Field(default_factory=TokenTypography)
    layout: TokenLayout = Field(default_factory=TokenLayout)
    blocks: TokenBlocks = Field(default_factory=TokenBlocks)


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: str = Field("", max_length=300)
    tokens: TemplateTokens = Field(default_factory=TemplateTokens)


class TemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=300)
    tokens: Optional[TemplateTokens] = None


class TemplateResponse(BaseModel):
    template_id: str
    name: str
    description: str
    status: TemplateStatus
    is_default: bool
    tokens: dict
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class TemplateSummary(BaseModel):
    template_id: str
    name: str
    tokens: dict

    model_config = ConfigDict(from_attributes=True)

"""用户行业关注列表（Watchlist）"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class WatchlistItem(BaseModel):
    industry: str = Field(..., description="行业名称（使用 18-bucket 体系）")
    user_id: str = Field(..., description="用户ID")
    note: Optional[str] = Field(None, description="备注说明")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

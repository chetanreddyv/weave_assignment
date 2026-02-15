from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class Contributor(BaseModel):
    login: str
    avatar_url: str
    html_url: str

class Review(BaseModel):
    user_login: str
    state: str  # APPROVED, CHANGES_REQUESTED, COMMENTED
    submitted_at: Optional[datetime]
    body: Optional[str]

class PullRequest(BaseModel):
    number: int
    title: str
    user_login: str
    state: str
    created_at: datetime
    merged_at: Optional[datetime]
    closed_at: Optional[datetime]
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    reviews: List[Review] = []
    html_url: str
    # LLM Metrics
    llm_quality_score: Optional[float] = None
    llm_reasoning: Optional[str] = None

class IssueActivity(BaseModel):
    issue_number: int
    title: str
    user_login: str
    created_at: datetime
    event_type: str # e.g., 'commented', 'closed', 'referenced'
    body: Optional[str]
    
class ContributorImpact(BaseModel):
    login: str
    avatar_url: str
    html_url: str
    prs_merged: int = 0
    prs_opened: int = 0
    reviews_given: int = 0
    additions: int = 0
    deletions: int = 0
    files_changed: int = 0
    issue_interactions: int = 0
    issues_closed: int = 0
    impact_score: float = 0.0
    baseline_impact_score: float = 0.0
    # LLM Metrics
    avg_quality_score: float = 0.0
    
class ImpactData(BaseModel):
    repo_name: str
    cutoff_date: datetime
    fetched_at: datetime
    pull_requests: List[PullRequest]
    issue_activities: List[IssueActivity]
    contributor_metrics: List[ContributorImpact]

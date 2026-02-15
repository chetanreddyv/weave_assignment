import os
import json
import math
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from github import Github, GithubException
from models import PullRequest, Review, IssueActivity, ContributorImpact, ImpactData
from pydantic_ai import Agent
from pydantic import BaseModel

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
REPO_NAME = "PostHog/posthog"

# --- LLM Setup ---
class PRQualityEvaluation(BaseModel):
    substance_score: int
    product_impact_score: int
    technical_quality_score: int
    blast_radius_score: int
    reasoning: str

if DEEPSEEK_API_KEY:
    os.environ["OPENAI_API_KEY"] = DEEPSEEK_API_KEY
    os.environ["OPENAI_BASE_URL"] = "https://api.deepseek.com"
    
    judge_agent = Agent(
        'openai:deepseek-chat',
        output_type=PRQualityEvaluation,
        system_prompt="""You are a distinguished VP of Engineering at a top-tier tech company, evaluating a GitHub Pull Request for its real-world engineering impact. You have deep expertise in software architecture, product strategy, and engineering culture.

Analyze the PR based on its title, description, and code change statistics. Rate each dimension on a strict 1-5 scale:

1. **Substance & Complexity** (Weight: High)
   - 5: Major architectural change, new system/service, complex algorithm, or significant refactor affecting multiple subsystems
   - 4: Substantial feature with non-trivial logic, meaningful abstraction changes, or cross-cutting concerns
   - 3: Standard feature implementation, moderate logic changes, or well-scoped module work
   - 2: Simple bug fix with clear root cause, config change with minor logic, or routine update
   - 1: Typo fix, comment update, dependency bump, or trivial one-liner

2. **Product & Business Impact** (Weight: High)
   - 5: Directly enables a new revenue stream, unblocks a critical launch, or fixes a P0 user-facing issue
   - 4: Improves core user workflow, meaningfully affects key metrics (retention, activation), or enables important integration
   - 3: Enhances existing feature, improves UX, or addresses moderate user pain point
   - 2: Internal tooling improvement, minor UX polish, or edge case fix
   - 1: No direct user impact — internal chore, refactor for code health only, or dead code removal

3. **Technical Excellence** (Weight: Medium)
   - 5: Exemplary — introduces tests, updates docs, clean abstractions, handles edge cases, follows best practices
   - 4: Well-crafted — reasonable test coverage, clear naming, good separation of concerns
   - 3: Adequate — functional but could use more tests or documentation
   - 2: Below average — limited tests, unclear naming, tight coupling
   - 1: Poor — no tests, unclear intent, potential for regressions

4. **Scope of Blast Radius** (Weight: Medium)
   - 5: Touches core infrastructure used by 5+ teams/services (database schemas, shared libraries, auth)
   - 4: Affects multiple features or modules across the codebase
   - 3: Scoped to a single feature but with multiple touchpoints
   - 2: Isolated change within a single module
   - 1: Completely isolated — no downstream dependencies

Provide a concise 1-2 sentence reasoning summarizing why this PR matters (or doesn't)."""
    )
    print("LLM Agent initialized with DeepSeek.")
else:
    judge_agent = None
    print("WARNING: DEEPSEEK_API_KEY not found. LLM evaluation will be skipped.")

# --- Stage 1: Minimal Data Collection (Volume) ---
def fetch_stage_1_volume(days=30, limit=500) -> tuple[List[PullRequest], List[IssueActivity], Dict[str, ContributorImpact]]:
    """
    Fetches broad metadata for the last `days`. 
    Captures: PRs, Issues, Reviews (counts), Reactions.
    Avoids: Full diffs/bodies for everyone (fetches PR details only for stats).
    """
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    print(f"\n--- STAGE 1: Volume Data Collection ---")
    print(f"Fetching data from {REPO_NAME} since {cutoff_date} (Limit: {limit} items)...")

    prs: List[PullRequest] = []
    issue_activities: List[IssueActivity] = []
    contributors: Dict[str, ContributorImpact] = {}

    items = repo.get_issues(since=cutoff_date, state='all', sort='updated')
    
    count = 0
    for item in items:
        if count >= limit:
            print(f"Reached limit of {limit} items. Stopping Stage 1 fetch.")
            break
        count += 1
        
        login = item.user.login if item.user else "ghost"
        
        # Init contributor
        if login not in contributors:
            contributors[login] = ContributorImpact(
                login=login,
                avatar_url=item.user.avatar_url if item.user else "",
                html_url=item.user.html_url if item.user else ""
            )
        
        if item.pull_request:
            if count % 10 == 0: print(f"Processing item {count} (PR)...")
            try:
                # We need get_pull for merged_at, additions, deletions
                # This is "semi-expensive" but necessary for the baseline "merged" metric.
                pr_detail = repo.get_pull(item.number)
                pr_reviews = []
                review_iter_count = 0
                for r in pr_detail.get_reviews():
                    if review_iter_count >= 5: break
                    review_iter_count += 1
                    
                    reviewer_login = r.user.login if r.user else "ghost"
                    pr_reviews.append(Review(
                        user_login=reviewer_login,
                        state=r.state,
                        submitted_at=r.submitted_at,
                        body="" # Exclude body in Stage 1
                    ))
                    
                    if reviewer_login not in contributors:
                        contributors[reviewer_login] = ContributorImpact(
                            login=reviewer_login,
                            avatar_url=r.user.avatar_url if r.user else "",
                            html_url=r.user.html_url if r.user else ""
                        )
                    contributors[reviewer_login].reviews_given += 1

                pr_model = PullRequest(
                    number=pr_detail.number,
                    title=pr_detail.title,
                    user_login=pr_detail.user.login if pr_detail.user else "ghost",
                    state=pr_detail.state,
                    created_at=pr_detail.created_at,
                    merged_at=pr_detail.merged_at,
                    closed_at=pr_detail.closed_at,
                    additions=pr_detail.additions,
                    deletions=pr_detail.deletions,
                    changed_files=pr_detail.changed_files,
                    reviews=pr_reviews,
                    html_url=pr_detail.html_url,
                )
                prs.append(pr_model)
                
                # Update Contributor (Author)
                c = contributors[login]
                c.prs_opened += 1
                if pr_model.merged_at:
                    c.prs_merged += 1
                
                c.additions += pr_model.additions
                c.deletions += pr_model.deletions
                c.files_changed += pr_model.changed_files

            except GithubException as e:
                print(f"Error fetching PR #{item.number}: {e}")
                
        else:
            # Issue
            is_closed = item.state == 'closed'
            issue_activities.append(IssueActivity(
                issue_number=item.number,
                title=item.title,
                user_login=login,
                created_at=item.created_at,
                event_type="closed" if is_closed else "opened",
                body=None, # Exclude body
            ))
            contributors[login].issue_interactions += 1
            if is_closed:
                contributors[login].issues_closed += 1

    return prs, issue_activities, contributors

# --- Stage 2: Value-Based Baseline Impact ---
def calculate_baseline_metrics(contributors: Dict[str, ContributorImpact], all_prs: List[PullRequest]):
    """
    Value-based scoring model reflecting real-world engineering impact.
    
    Philosophy: Impact = Shipping (primary) + Force-multiplication (reviews) 
                       + Code Substance (volume) + Problem Resolution (issues)
    
    All dimensions are log-normalized to prevent any single metric from dominating.
    Weights sum to 100% with documented rationale.
    """
    print(f"\n--- STAGE 2: Value-Based Impact Analysis ---")
    
    # Pre-compute PR type multipliers from title conventions
    pr_type_multipliers = {}
    for pr in all_prs:
        title_lower = pr.title.lower().strip()
        # Detect conventional commit prefixes: feat:, fix:, refactor:, chore:, docs:, etc.
        if any(title_lower.startswith(p) for p in ['feat', 'feature']):
            pr_type_multipliers[pr.number] = 1.5  # Features drive product forward
        elif any(title_lower.startswith(p) for p in ['fix', 'bug', 'hotfix', 'patch']):
            pr_type_multipliers[pr.number] = 1.3  # Fixes resolve user pain
        elif any(title_lower.startswith(p) for p in ['refactor', 'perf', 'optimize']):
            pr_type_multipliers[pr.number] = 1.1  # Refactors improve long-term health
        elif any(title_lower.startswith(p) for p in ['chore', 'ci', 'docs', 'style', 'bump']):
            pr_type_multipliers[pr.number] = 0.7  # Maintenance is necessary but lower impact
        else:
            pr_type_multipliers[pr.number] = 1.0  # Default
    
    for c in contributors.values():
        if c.login.endswith('[bot]'):
            c.impact_score = -1
            continue

        # --- 1. SHIPPING SCORE (40% weight) ---
        # Primary value driver: merged PRs move the product forward.
        # Base: 10 pts per merged PR, with type multiplier from title.
        # Log-dampened so 20 trivial PRs don't outweigh 3 complex ones.
        user_merged_prs = [p for p in all_prs if p.user_login == c.login and p.merged_at]
        
        # Sum of type-weighted PR credits
        raw_pr_value = sum(10 * pr_type_multipliers.get(p.number, 1.0) for p in user_merged_prs)
        shipping_score = math.log(1 + raw_pr_value) * 15  # Scale factor for readability
        
        # --- 2. REVIEW SCORE (30% weight) ---
        # Force multiplier: reviews unblock teammates and maintain quality.
        # Log-dampened: 10 rubber-stamp reviews ≠ 10× the value of 1 thoughtful review.
        # math.log(1 + 5) ≈ 1.79, math.log(1 + 20) ≈ 3.04 — natural diminishing returns.
        review_score = math.log(1 + c.reviews_given) * 30
        
        # --- 3. CODE VOLUME (15% weight) ---
        # Substance signal: larger changes require more engineering effort.
        # log10-dampened: 100 lines → 2, 10000 lines → 4. Prevents massive refactors from dominating.
        code_volume_score = math.log10(1 + c.additions + c.deletions) * 8
        
        # --- 4. ISSUE RESOLUTION (15% weight) ---
        # Problem-solving: closing issues (5 pts) is 5× more valuable than opening/commenting (1 pt).
        # Reflects that resolution > identification in real-world impact.
        issue_score = (c.issues_closed * 5) + (max(c.issue_interactions - c.issues_closed, 0) * 1)
        issue_score = math.log(1 + issue_score) * 10
        
        c.impact_score = shipping_score + review_score + code_volume_score + issue_score

# --- Stage 3: LLM Quality Evaluation ---
async def fetch_stage_3_quality(contributors: Dict[str, ContributorImpact], all_prs: List[PullRequest]):
    """
    Targeted evaluation for Top 15 candidates.
    Fetches bodies and runs Agent.
    """
    print(f"\n--- STAGE 3: Trusted LLM Evaluation ---")
    
    # Filter valid candidates
    candidates = [c for c in contributors.values() if not c.login.endswith('[bot]')]
    # Sort by baseline
    candidates.sort(key=lambda x: x.impact_score, reverse=True)
    
    # Select Top 15
    top_candidates = candidates[:15]
    print(f"Selected {len(top_candidates)} candidates for deep dive.")

    for c in top_candidates:
        # Find their merged PRs
        user_prs = [p for p in all_prs if p.user_login == c.login and p.merged_at]
        # Sort by size (proxy for complexity/impact possibility)
        user_prs.sort(key=lambda x: x.additions + x.deletions, reverse=True)
        # Take Top 10
        sample_prs = user_prs[:10]
        
        if not sample_prs:
            continue
            
        print(f"Evaluating {c.login} (Baseline: {c.impact_score:.1f}) - {len(sample_prs)} PRs...")
        
        scores = []
        for pr in sample_prs:
            # Optimization: In a real app, we'd fetch the full body here if we skipped it in Stage 1.
            # For this script, we'll use the title (and body if we had it).
            # If we exclude body in Stage 1, we must fetch it here. 
            # Since we can't easily re-fetch just the body without an API call, let's assume 
            # we infer context from Title + Stats for this demo OR make one API call if needed.
            # To be safe and fast, we'll use the metadata we have.
            
            evaluation = await evaluate_pr_with_llm(pr)
            if evaluation:
                pr.llm_quality_score = (
                    evaluation.substance_score * 1.5
                    + evaluation.product_impact_score * 1.5
                    + evaluation.technical_quality_score
                    + evaluation.blast_radius_score
                ) / 5.0
                pr.llm_reasoning = evaluation.reasoning
                scores.append(pr.llm_quality_score)
                # Save these updates back to the list
        
        if scores:
            avg_quality = sum(scores) / len(scores)
            c.avg_quality_score = avg_quality
            
            # Snapshot the baseline score before applying AI multiplier
            c.baseline_impact_score = c.impact_score
            
            # Quality Multiplier:
            # Avg 3 -> 1.0x (neutral)
            # Avg 5 -> 1.4x (boost)
            # Avg 1 -> 0.6x (penalty)
            multiplier = 1.0 + (avg_quality - 3) * 0.2
            c.impact_score = c.impact_score * multiplier
            print(f"  -> Avg Quality: {avg_quality:.1f} | Multiplier: {multiplier:.2f} | Baseline: {c.baseline_impact_score:.1f} | AI Score: {c.impact_score:.1f}")

async def evaluate_pr_with_llm(pr: PullRequest) -> Optional[PRQualityEvaluation]:
    if not judge_agent:
        return None
        
    content = f"""
    PR #{pr.number}: {pr.title}
    Code Stats: +{pr.additions} additions / -{pr.deletions} deletions across {pr.changed_files} files
    Total scope: {pr.additions + pr.deletions} lines changed
    Status: Merged at {pr.merged_at}
    
    Context signals:
    - Change density: {(pr.additions + pr.deletions) / max(pr.changed_files, 1):.0f} lines/file avg
    - Net growth: {'+' if pr.additions > pr.deletions else ''}{pr.additions - pr.deletions} lines
    - Review engagement: {len(pr.reviews)} reviewers participated
    
    Evaluate the engineering impact and quality of this contribution.
    """
    
    try:
        result = await judge_agent.run(content)
        return result.output
    except Exception as e:
        print(f"LLM Error on PR #{pr.number}: {e}")
        return None

def main():
    try:
        # 1. Volume
        # Limiting to 50 for Speed in this demo, fully adjustable
        prs, issues, contributors = fetch_stage_1_volume(days=30, limit=300)
        
        # 2. Baseline
        calculate_baseline_metrics(contributors, prs)
        
        # Snapshot baseline for all contributors (Stage 3 will re-set for top 15 before multiplier)
        for c in contributors.values():
            c.baseline_impact_score = c.impact_score
        
        # 3. Quality (Async)
        asyncio.run(fetch_stage_3_quality(contributors, prs))

        # Final Sort & Save
        sorted_metrics = sorted(contributors.values(), key=lambda x: x.impact_score, reverse=True)
        filtered_metrics = [c for c in sorted_metrics if not c.login.endswith('[bot]')]

        impact_data = ImpactData(
            repo_name=REPO_NAME,
            cutoff_date=datetime.now(timezone.utc) - timedelta(days=30),
            fetched_at=datetime.now(timezone.utc),
            pull_requests=prs,
            issue_activities=issues,
            contributor_metrics=filtered_metrics
        )
        
        with open("impact_data.json", "w") as f:
            f.write(impact_data.model_dump_json(indent=2))
            
        print(f"\nSUCCESS: Engine run complete. Data saved to impact_data.json.")
        print("Run 'streamlit run dashboard.py' to view results.")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

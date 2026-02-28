import os
from github import Github

def scout_github_issues(repo_name: str) -> str:
    """
    Search for up to 3 open issues in a GitHub repository with labels 'good first issue' or 'help wanted'.

    Args:
        repo_name: The full name of the repository on GitHub (e.g., "fastapi/fastapi", "pallets/flask").

    Returns:
        A formatted string summarizing the titles and numbers of up to 3 matching open issues.
        If the repository is not found or another error occurs, it returns a graceful error message.
    """
    try:
        github_token = os.getenv("GITHUB_TOKEN")
        g = Github(github_token) # If github_token is None, it uses unauthenticated access
        repo = g.get_repo(repo_name)
        
        # Search for issues with specific labels
        issues = repo.get_issues(state='open', labels=['good first issue'])
        help_wanted_issues = repo.get_issues(state='open', labels=['help wanted'])
        
        found_issues = []
        for issue in issues:
            if issue.pull_request is None: # Only grab issues, not PRs
                found_issues.append(issue)
                if len(found_issues) >= 3:
                    break
                    
        if len(found_issues) < 3:
            for issue in help_wanted_issues:
                if issue.pull_request is None and issue not in found_issues:
                    found_issues.append(issue)
                    if len(found_issues) >= 3:
                        break
        
        if not found_issues:
            return f"No open 'good first issue' or 'help wanted' issues found in {repo_name}."
            
        summary = f"Found {len(found_issues)} issues in {repo_name}:\n"
        for issue in found_issues:
            summary += f"- Issue #{issue.number}: {issue.title}\n"
            
        return summary
    except Exception as e:
        return f"Error fetching issues for {repo_name}. Exception: {str(e)}"


def analyze_issue_code(repo_name: str, issue_number: int) -> str:
    """
    Fetch the specific details of a GitHub issue and provide a plan of attack.
    
    Args:
        repo_name: The full name of the repository on GitHub (e.g., "fastapi/fastapi").
        issue_number: The number of the issue to analyze.
        
    Returns:
        A string mocked analysis and plan of attack for the issue.
    """
    # Mocked function as per instructions to keep it fast
    return f"Fetched issue details for {repo_name} #{issue_number}. The bug appears to be in the routing module. Here is a mocked plan of attack..."

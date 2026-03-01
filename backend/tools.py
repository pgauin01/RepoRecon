import os
from github import Github

def scout_github_issues(repo_name: str) -> str:
    """
    Fetches the latest open issues from a GitHub repository.
    Call this when the user asks to scan a repo for bugs, targets, or issues.
    """
    print(f"\n[TOOL EXECUTION] 🕵️‍♂️ Gemini triggered scout_github_issues for: {repo_name}...\n")
    
    token = os.getenv("GITHUB_TOKEN")
    g = Github(token)
    
    try:
        repo = g.get_repo(repo_name)
        # Fetch the most recent open issues (ignoring labels) to guarantee we find something for the demo
        issues = repo.get_issues(state='open', sort='created', direction='desc')
        
        result_lines = [f"Tactical scan complete for {repo_name}. Here are the top 3 open targets:"]
        count = 0
        
        for issue in issues:
            # We only want actual issues, not Pull Requests
            if not issue.pull_request:
                result_lines.append(f"Target {count + 1}: Issue #{issue.number} - {issue.title}")
                count += 1
            if count >= 3:
                break
                
        if count == 0:
            result = f"No open issues found in {repo_name}."
            print(f"[TOOL RESULT] {result}")
            return result
            
        final_summary = "\n".join(result_lines)
        print(f"[TOOL RESULT] Successfully fetched {count} issues.")
        return final_summary
        
    except Exception as e:
        error_msg = f"Recon failed. I could not access {repo_name}. Error details: {str(e)}"
        print(f"[TOOL ERROR] {error_msg}")
        return error_msg

def analyze_issue_code(repo_name: str, issue_number: int) -> str:
    """
    Fetch the specific details of a GitHub issue and provide a plan of attack.
    
    Args:
        repo_name: The full name of the repository on GitHub.
        issue_number: The number of the issue to analyze.
    """
    print(f"\n[TOOL EXECUTION] 🛠️ Gemini triggered analyze_issue_code for {repo_name} #{issue_number}...\n")
    return f"Fetched issue details for {repo_name} #{issue_number}. The bug appears to be in the routing module. Here is a mocked plan of attack..."
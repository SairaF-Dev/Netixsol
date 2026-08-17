from langchain_core.tools import tool
import sqlite3
import requests
import os

# Tool 1: Real File parhne ka tool
@tool
def fetch_server_logs(service_name: str) -> str:
    """
    Fetch recent server error logs for a specific service.
    Returns only log entries associated with the requested service.
    """

    try:
        # Validate input
        if not service_name or not service_name.strip():
            return "Error: service_name cannot be empty."

        log_file = "data/server.log"

        # Check whether log file exists
        if not os.path.exists(log_file):
            return "Error: server.log file not found."

        # Read log lines
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Filter logs belonging to requested service
        matching_logs = [
            line.strip()
            for line in lines
            if service_name.lower() in line.lower()
        ]

        # No matching logs
        if not matching_logs:
            return f"No logs found for service: {service_name}"

        return (
            f"Recent Logs for {service_name}:\n"
            + "\n".join(matching_logs)
        )

    except OSError as e:
        return f"Error reading logs: {str(e)}"

    except Exception as e:
        return f"Unexpected error reading logs: {str(e)}"
# Tool 2: Real Local Database ko query karne ka tool
@tool
def get_db_metrics(service_name: str) -> str:
    """
    Query the local database to get real-time CPU, Memory, and Database connection metrics for a specific service.
    Use this to check if the server is overloaded.
    """
    try:
        conn = sqlite3.connect("data/local_metrics.db")
        cursor = conn.cursor()
        
        # Strict SQL Query: Sirf specific service ka data layega (Prevents SQL Injection)
        cursor.execute("SELECT cpu_usage_percent, memory_usage_percent, active_db_connections, max_db_connections, status FROM server_metrics WHERE service_name = ?", (service_name,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return f"Metrics for {service_name} - CPU: {row[0]}%, Memory: {row[1]}%, DB Connections: {row[2]}/{row[3]} (Status: {row[4]})"
        else:
            return f"No metrics found for service: {service_name}"
    except Exception as e:
        return f"Database error: {str(e)}"

# Tool 3: Real External API ko call karne ka tool
@tool
def check_github_commits(repository: str) -> str:
    """
    Fetch the latest GitHub commit and changed files for a repository.

    Used by the SRE agent to determine whether a recent code change
    may be related to an incident.
    """

    if not repository or not repository.strip():
        return "Error: repository cannot be empty."

    repository = repository.strip()

    # Basic repository format validation
    if repository.count("/") != 1:
        return (
            "Error: repository must use the format "
            "'owner/repository'."
        )

    url = f"https://api.github.com/repos/{repository}/commits"

    try:
        response = requests.get(
            url,
            timeout=5,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "SRE-Agent-Capstone",
            },
        )

        response.raise_for_status()

        commits = response.json()

        if not commits:
            return (
                f"No commits found for repository: {repository}"
            )

        latest_commit = commits[0]

        sha = latest_commit.get("sha", "Unknown")

        commit_data = latest_commit.get("commit", {})

        author_data = commit_data.get("author", {})

        author = author_data.get(
            "name",
            "Unknown"
        )

        date = author_data.get(
            "date",
            "Unknown"
        )

        message = commit_data.get(
            "message",
            "No commit message"
        )

        # ----------------------------------------------------
        # Fetch detailed commit information
        # This gives us changed files.
        # ----------------------------------------------------

        commit_url = (
            f"https://api.github.com/repos/"
            f"{repository}/commits/{sha}"
        )

        commit_response = requests.get(
            commit_url,
            timeout=5,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "SRE-Agent-Capstone",
            },
        )

        commit_response.raise_for_status()

        commit_details = commit_response.json()

        files = commit_details.get("files", [])

        if files:
            changed_files = []

            for file in files:
                filename = file.get(
                    "filename",
                    "Unknown file"
                )

                status = file.get(
                    "status",
                    "unknown"
                )

                additions = file.get(
                    "additions",
                    0
                )

                deletions = file.get(
                    "deletions",
                    0
                )

                changed_files.append(
                    f"- {filename} "
                    f"(status={status}, "
                    f"+{additions}/-{deletions})"
                )

            files_text = "\n".join(changed_files)

        else:
            files_text = "No changed files returned."

        return (
            f"Latest GitHub commit for {repository}:\n\n"
            f"Author: {author}\n"
            f"Date: {date}\n"
            f"SHA: {sha}\n"
            f"Message: {message}\n\n"
            f"Changed files:\n"
            f"{files_text}"
        )

    except requests.exceptions.Timeout:
        return (
            "Error: GitHub API request timed out "
            "after 5 seconds."
        )

    except requests.exceptions.HTTPError as exc:
        return (
            f"Error: GitHub API returned an HTTP error: {exc}"
        )

    except requests.exceptions.RequestException as exc:
        return (
            f"Error: GitHub API request failed: {exc}"
        )

    except Exception as exc:
        return (
            f"Error processing GitHub response: {exc}"
        )

# In teeno tools ko ek list mein daal dete hain taake Agent inhein use kar sakay
tools_list = [fetch_server_logs, get_db_metrics, check_github_commits]
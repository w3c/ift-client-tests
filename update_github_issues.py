#!/usr/bin/env python3
"""
Usage:
python3 update_github_issues.py <path to test-coverage-report.txt> [--dry-run]
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from urllib.error import HTTPError

def get_repo_name():
    try:
        output = subprocess.check_output(['git', 'remote', 'get-url', 'origin'], text=True).strip()
        # Handle formats like git@github.com:owner/repo.git or https://github.com/owner/repo.git
        if output.startswith('git@github.com:'):
            return output.split('git@github.com:')[1].replace('.git', '')
        elif output.startswith('https://github.com/'):
            return output.split('https://github.com/')[1].replace('.git', '')
    except subprocess.CalledProcessError:
        pass
    return None

def github_api_request(method, url, token, data=None, dry_run=False):
    if dry_run:
        print(f"  {method} {url}")
        if data:
            print(f"  Body: {json.dumps(data, indent=4)}")
        return {}

    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'ift-client-tests-script'
    }
    if token:
        headers['Authorization'] = f'token {token}'

    req = urllib.request.Request(url, headers=headers, method=method)
    if data is not None:
        req.add_header('Content-Type', 'application/json')
        req.data = json.dumps(data).encode('utf-8')

    try:
        with urllib.request.urlopen(req) as response:
            if response.status in (204, 205):
                return {}
            resp_body = response.read().decode('utf-8')
            return json.loads(resp_body) if resp_body else {}
    except HTTPError as e:
        print(f"GitHub API Error: {e.code} {e.reason}", file=sys.stderr)
        err_body = e.read().decode('utf-8')
        print(err_body, file=sys.stderr)
        sys.exit(1)

def get_all_issues(repo, token):
    issues = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{repo}/issues?state=all&per_page=100&page={page}"
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'ift-client-tests-script'
        }
        if token:
            headers['Authorization'] = f'token {token}'

        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req) as response:
                page_issues = json.loads(response.read().decode('utf-8'))
                if not page_issues:
                    break
                issues.extend(page_issues)

                # Check for pagination
                link_header = response.headers.get('Link', '')
                if 'rel="next"' not in link_header:
                    break
                page += 1
        except HTTPError as e:
            print(f"GitHub API Error: {e.code} {e.reason}", file=sys.stderr)
            sys.exit(1)

    return issues

def main():
    parser = argparse.ArgumentParser(description="Update GitHub issues based on coverage report.")
    parser.add_argument('report', help="Path to the test-coverage-report.txt")
    parser.add_argument('--dry-run', action='store_true', help="Print API calls without executing them")
    parser.add_argument('--repo', help="GitHub repository in the format owner/repo")
    args = parser.parse_args()

    repo = args.repo or get_repo_name()
    if not repo:
        print("Could not determine repository. Please use --repo.", file=sys.stderr)
        sys.exit(1)

    token = os.environ.get('GITHUB_TOKEN')
    if not token and not args.dry_run:
        print("Warning: GITHUB_TOKEN environment variable is not set. API calls may fail or be rate-limited.", file=sys.stderr)

    untested = set()
    tested = set()

    try:
        with open(args.report, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 2:
                    if parts[0] == 'UNTESTED':
                        untested.add(parts[1])
                    elif parts[0] == 'TESTED':
                        tested.add(parts[1])
    except FileNotFoundError:
        print(f"Error: Report file '{args.report}' not found.", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching issues for {repo}...")
    issues = get_all_issues(repo, token)

    open_issues_by_id = {}
    has_existing_issue = set()

    title_prefix = "Implement Test for Conformance Requirement: "
    for issue in issues:
        # Ignore pull requests
        if 'pull_request' in issue:
            continue

        title = issue.get('title', '')
        if title.startswith(title_prefix):
            stmt_id = title[len(title_prefix):]
            has_existing_issue.add(stmt_id)
            if issue.get('state') == 'open':
                open_issues_by_id.setdefault(stmt_id, []).append(issue)

    to_create = []
    for stmt_id in sorted(untested):
        if stmt_id not in has_existing_issue:
            to_create.append(stmt_id)

    to_close = []
    for stmt_id in sorted(tested):
        if stmt_id in open_issues_by_id:
            to_close.append(stmt_id)

    if not to_create and not to_close:
        print("No issues to create or close.")
        return

    if to_create:
        print("Opening issues for:")
        for stmt_id in to_create:
            print(f"  {stmt_id}")

    if to_close:
        print("\nClosing issues for:")
        for stmt_id in to_close:
            print(f"  {stmt_id}")


    if not args.dry_run:
        print("\nProceed? [y/N] ", end="", flush=True)
        choice = input().strip().lower()
        if choice != 'y':
            print("Aborted.")
            return
    else:
        print("\nDry run requested, no changes will be made.")

    # 1. Create new issue for untested conformance statements if one doesn't exist
    for stmt_id in to_create:
        title = f"{title_prefix}{stmt_id}"
        body = f"Link to requirement: https://w3c.github.io/IFT/Overview.html#{stmt_id}"
        url = f"https://api.github.com/repos/{repo}/issues"
        data = {"title": title, "body": body}
        print(f">> Opening issue for: {stmt_id}")
        github_api_request('POST', url, token, data, args.dry_run)

    # 2. Close open issues for tested conformance statements
    for stmt_id in to_close:
        for issue in open_issues_by_id[stmt_id]:
            issue_number = issue['number']
            url = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
            data = {"state": "closed"}
            print(f">> Closing issue #{issue_number} for: {stmt_id}")
            github_api_request('PATCH', url, token, data, args.dry_run)

if __name__ == '__main__':
    main()

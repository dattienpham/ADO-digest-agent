import os

ADO_PAT = os.environ["ADO_PAT"]
ADO_ORG = os.environ.get("ADO_ORG", "agentiqai")
ADO_PROJECT = os.environ.get("ADO_PROJECT", "AgentIQ")
ADO_BASE_URL = f"https://dev.azure.com/{ADO_ORG}/{ADO_PROJECT}"

TEAMS_WEBHOOK_URL = os.environ["TEAMS_WEBHOOK_URL"]

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

BOARDS = ["Recruitment", "Operation", "Training/Workshop/Sharing"]

MAX_STORIES = int(os.environ.get("MAX_STORIES", 10))
MAX_COMMENT_STORIES = int(os.environ.get("MAX_COMMENT_STORIES", 10))
MAX_COMMENTS_PER_STORY = int(os.environ.get("MAX_COMMENTS_PER_STORY", 2))

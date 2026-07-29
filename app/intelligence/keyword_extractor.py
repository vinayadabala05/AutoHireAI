"""Deterministic keyword extraction against a curated vocabulary.

No embeddings, no LLM — each vocabulary entry is matched against the input
text with a case-insensitive, alnum-boundary regex (so "Go" doesn't match
inside "Golang", "R" doesn't match inside "Order", etc.). Terms with
aliases (e.g. "Postgres" for "PostgreSQL") report only the canonical name,
so downstream components never have to reconcile near-duplicate spellings.
"""

import re

from app.intelligence.models import KeywordSet

# category -> canonical term -> alias spellings (canonical is always matched too)
_VOCABULARY: dict[str, dict[str, list[str]]] = {
    "programming_languages": {
        "Python": [],
        "Java": [],
        "JavaScript": ["JS"],
        "TypeScript": ["TS"],
        "Go": ["Golang"],
        "Rust": [],
        "C++": [],
        "C#": [],
        "Ruby": [],
        "PHP": [],
        "Swift": [],
        "Kotlin": [],
        "Scala": [],
        "SQL": [],
        "Bash": [],
        "R": [],
        "Perl": [],
        "MATLAB": [],
    },
    "frameworks": {
        "FastAPI": [],
        "Django": [],
        "Flask": [],
        "React": [],
        "Angular": [],
        "Vue": [],
        "Next.js": ["NextJS"],
        "Spring Boot": ["Spring"],
        "Express": ["Express.js"],
        ".NET": ["ASP.NET"],
        "Ruby on Rails": ["Rails"],
        "Svelte": [],
        "Laravel": [],
        "NestJS": [],
    },
    "cloud": {
        "AWS": ["Amazon Web Services"],
        "Azure": [],
        "GCP": ["Google Cloud"],
        "Heroku": [],
        "DigitalOcean": [],
        "Cloudflare": [],
        "Vercel": [],
        "Netlify": [],
    },
    "devops": {
        "Docker": [],
        "Kubernetes": ["K8s"],
        "Terraform": [],
        "Ansible": [],
        "Jenkins": [],
        "CI/CD": [],
        "GitHub Actions": [],
        "GitLab CI": [],
        "CircleCI": [],
        "Helm": [],
        "Prometheus": [],
        "Grafana": [],
        "Nginx": [],
    },
    "databases": {
        "PostgreSQL": ["Postgres"],
        "MySQL": [],
        "MongoDB": [],
        "Redis": [],
        "Elasticsearch": [],
        "DynamoDB": [],
        "Cassandra": [],
        "SQLite": [],
        "Oracle": [],
        "MariaDB": [],
        "Neo4j": [],
    },
    "tools": {
        "Git": [],
        "GitHub": [],
        "GitLab": [],
        "Jira": [],
        "Figma": [],
        "Postman": [],
        "Slack": [],
        "Confluence": [],
        "Notion": [],
        "Vim": [],
    },
    "operating_systems": {
        "Linux": [],
        "Windows": [],
        "macOS": [],
        "Ubuntu": [],
        "Debian": [],
        "CentOS": [],
        "Unix": [],
        "Android": [],
        "iOS": [],
    },
    "ai_ml": {
        "Machine Learning": ["ML"],
        "Deep Learning": [],
        "TensorFlow": [],
        "PyTorch": [],
        "scikit-learn": ["sklearn"],
        "Keras": [],
        "NLP": ["Natural Language Processing"],
        "Computer Vision": [],
        "LLM": ["Large Language Model", "Large Language Models"],
        "Transformers": [],
        "Pandas": [],
        "NumPy": [],
        "Data Science": [],
        "Reinforcement Learning": [],
        "Neural Network": ["Neural Networks"],
        "Generative AI": [],
        "MLOps": [],
        "Hugging Face": [],
        "OpenCV": [],
        "spaCy": [],
        "Research": [],
        "Publications": [],
    },
    "soft_skills": {
        "Communication": [],
        "Leadership": [],
        "Teamwork": [],
        "Problem Solving": [],
        "Collaboration": [],
        "Mentoring": [],
        "Ownership": [],
        "Adaptability": [],
        "Critical Thinking": [],
        "Time Management": [],
        "Attention to Detail": [],
        "Creativity": [],
        "Self-Starter": [],
        "Cross-functional": [],
    },
}


def _compile_pattern(term: str) -> re.Pattern[str]:
    """Case-insensitive match, bounded by non-alphanumeric characters only
    where the term itself starts/ends alphanumeric (so punctuation-heavy
    terms like "C++" or ".NET" aren't broken by a `\\b` that doesn't apply)."""
    escaped = re.escape(term)
    prefix = r"(?<![A-Za-z0-9])" if term[0].isalnum() else ""
    suffix = r"(?![A-Za-z0-9])" if term[-1].isalnum() else ""
    return re.compile(prefix + escaped + suffix, re.IGNORECASE)


class KeywordExtractor:
    def extract(self, text: str) -> KeywordSet:
        found: dict[str, list[str]] = {category: [] for category in _VOCABULARY}
        for category, terms in _VOCABULARY.items():
            for canonical, aliases in terms.items():
                candidates = [canonical, *aliases]
                if any(_compile_pattern(candidate).search(text) for candidate in candidates):
                    found[category].append(canonical)
        return KeywordSet(**found)

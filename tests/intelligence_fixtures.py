"""Shared sample data for Resume Intelligence tests.

Five representative job postings (Backend Engineer, AI Engineer, Research
Engineer, ML Engineer, Python Developer) plus one `CareerContext` standing
in for a real user's profile — reused across every test module in this
package so behavior is checked against the same fixtures.
"""

from app.intelligence.models import (
    CareerContext,
    ExperienceInput,
    JobPostingInput,
    ProjectInput,
    SkillInput,
)

BACKEND_ENGINEER_JOB = JobPostingInput(
    title="Backend Engineer",
    description=(
        "We're looking for a Backend Engineer to help build our core platform. "
        "This is a full-time role. 3-5 years of experience preferred."
    ),
    requirements=[
        "Strong experience with Python and FastAPI",
        "Experience with PostgreSQL and relational database design",
        "Experience with Docker and containerized deployments",
        "Experience with AWS",
        "Bachelor's degree in Computer Science or related field",
    ],
    responsibilities=[
        "Design and build REST APIs",
        "Own services in production",
        "Collaborate with frontend and product teams",
    ],
    preferred_skills=["Kubernetes", "Redis", "CI/CD"],
)

AI_ENGINEER_JOB = JobPostingInput(
    title="AI Engineer",
    description=(
        "Join our AI team building production machine learning systems. "
        "Full-time, senior level (5+ years)."
    ),
    requirements=[
        "Strong Python skills",
        "Experience with PyTorch or TensorFlow",
        "Experience with Machine Learning and Deep Learning",
        "Experience with NLP",
        "Master's degree in Computer Science, Machine Learning, or related field",
    ],
    responsibilities=[
        "Train and deploy ML models",
        "Build data pipelines for model training",
    ],
    preferred_skills=["Hugging Face", "MLOps", "AWS"],
)

RESEARCH_ENGINEER_JOB = JobPostingInput(
    title="Research Engineer",
    description=(
        "Our research team is looking for a full-time Research Engineer to advance the state "
        "of the art in reinforcement learning. PhD preferred."
    ),
    requirements=[
        "Python",
        "Machine Learning research experience",
        "Reinforcement Learning",
        "Publications in top-tier venues a plus",
        "PhD in Computer Science, Machine Learning, or a related field",
    ],
    responsibilities=[
        "Design and run ML research experiments",
        "Publish findings",
    ],
    preferred_skills=["PyTorch", "Deep Learning"],
)

ML_ENGINEER_JOB = JobPostingInput(
    title="ML Engineer",
    description="Build and operate our ML infrastructure. Full-time.",
    requirements=[
        "Python",
        "TensorFlow",
        "MLOps",
        "Docker",
        "Kubernetes",
    ],
    responsibilities=[
        "Build ML training and serving infrastructure",
        "Monitor model performance in production",
    ],
    preferred_skills=["AWS", "CI/CD"],
)

PYTHON_DEVELOPER_JOB = JobPostingInput(
    title="Python Developer",
    description="Full-time Python Developer role building web applications.",
    requirements=[
        "Python",
        "Django",
        "PostgreSQL",
        "REST APIs",
    ],
    responsibilities=[
        "Build and maintain Django web applications",
    ],
    preferred_skills=["Docker"],
)

SAMPLE_JOBS = {
    "backend_engineer": BACKEND_ENGINEER_JOB,
    "ai_engineer": AI_ENGINEER_JOB,
    "research_engineer": RESEARCH_ENGINEER_JOB,
    "ml_engineer": ML_ENGINEER_JOB,
    "python_developer": PYTHON_DEVELOPER_JOB,
}


def sample_career_context() -> CareerContext:
    """A backend-leaning engineer with one ML-flavored project, for
    testing how rankings/sections shift across backend vs. AI/ML jobs.
    """
    return CareerContext(
        full_name="Jordan Smith",
        skills=[
            SkillInput(name="Python", years_experience=5),
            SkillInput(name="FastAPI", years_experience=3),
            SkillInput(name="PostgreSQL", years_experience=4),
            SkillInput(name="Docker", years_experience=3),
            SkillInput(name="AWS", years_experience=2),
            SkillInput(name="Git", years_experience=5),
        ],
        projects=[
            ProjectInput(
                name="Market Data Platform",
                description=(
                    "Built a real-time market data platform using FastAPI and PostgreSQL, "
                    "deployed with Docker on AWS."
                ),
                technologies=["FastAPI", "PostgreSQL", "Docker", "AWS"],
                priority="featured",
                is_ongoing=True,
            ),
            ProjectInput(
                name="ML Recommendation Engine",
                description=(
                    "Built a recommendation engine using TensorFlow and Pandas for feature "
                    "engineering, with a Python training pipeline."
                ),
                technologies=["Python", "TensorFlow", "Pandas"],
                priority="medium",
                is_ongoing=False,
            ),
            ProjectInput(
                name="Personal Blog",
                description="A simple personal blog built with React and JavaScript.",
                technologies=["React", "JavaScript"],
                priority="low",
                is_ongoing=False,
            ),
        ],
        experiences=[
            ExperienceInput(
                title="Backend Engineer",
                company_name="Acme Corp",
                description=(
                    "Building backend services with FastAPI and PostgreSQL, deployed via Docker."
                ),
                technologies=["Python", "FastAPI", "PostgreSQL", "Docker"],
                is_current=True,
                years_ago_ended=0.0,
            ),
            ExperienceInput(
                title="Data Analyst Intern",
                company_name="Globex",
                description="Analyzed datasets with Python and SQL.",
                technologies=["Python", "SQL"],
                is_current=False,
                years_ago_ended=3.0,
            ),
        ],
    )

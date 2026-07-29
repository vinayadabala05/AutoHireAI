"""Pure transformation from `RawProfileData` (loaded ORM rows) to a `CareerProfile`.

No database access, no I/O — every field is copied or derived directly
from what `loader.py` fetched. This is what makes the builder testable
with hand-built in-memory ORM instances and no database at all.
"""

from collections import Counter
from datetime import UTC, datetime

from app.career_profile.loader import RawProfileData
from app.career_profile.models import (
    ApplicationPreference,
    CareerProfile,
    CertificateProfile,
    EducationProfile,
    ExperienceProfile,
    GithubProfile,
    InterviewPreference,
    PersonalInfo,
    PreferenceProfile,
    ProjectProfile,
    SkillProfile,
)
from app.models.profile import Certificate, Education, Experience, GithubRepository, Project, Skill


class CareerProfileBuilder:
    def build(self, raw: RawProfileData) -> CareerProfile:
        return CareerProfile(
            user_id=raw.user.id,
            generated_at=datetime.now(UTC),
            personal_info=self._build_personal_info(raw),
            education=[self._build_education(e) for e in raw.educations],
            experience=[self._build_experience(e) for e in raw.experiences],
            projects=[self._build_project(p) for p in raw.projects],
            skills=[self._build_skill(s) for s in raw.skills],
            certificates=[self._build_certificate(c) for c in raw.certificates],
            github_repositories=[self._build_github(g) for g in raw.github_repositories],
            preferences=self._build_preferences(raw),
        )

    def _build_personal_info(self, raw: RawProfileData) -> PersonalInfo:
        user = raw.user
        return PersonalInfo(
            full_name=user.full_name,
            email=user.email,
            phone=user.phone,
            location=user.location,
            headline=user.headline,
            summary=user.summary,
            linkedin_url=user.linkedin_url,
            portfolio_url=user.portfolio_url,
            timezone=user.timezone,
        )

    def _build_education(self, education: Education) -> EducationProfile:
        return EducationProfile(
            institution=education.institution,
            degree=education.degree,
            field_of_study=education.field_of_study,
            start_date=education.start_date,
            end_date=education.end_date,
            is_current=education.is_current,
            gpa=education.gpa,
            description=education.description,
        )

    def _build_experience(self, experience: Experience) -> ExperienceProfile:
        return ExperienceProfile(
            title=experience.title,
            company_name=experience.company_name,
            location=experience.location,
            start_date=experience.start_date,
            end_date=experience.end_date,
            is_current=experience.is_current,
            description=experience.description,
            achievements=list(experience.achievements or []),
            technologies=list(experience.technologies or []),
        )

    def _build_project(self, project: Project) -> ProjectProfile:
        return ProjectProfile(
            name=project.name,
            description=project.description,
            technologies=list(project.technologies or []),
            achievements=list(project.achievements or []),
            github_url=project.github_url,
            demo_url=project.demo_url,
            priority=project.priority,
            start_date=project.start_date,
            end_date=project.end_date,
        )

    def _build_skill(self, skill: Skill) -> SkillProfile:
        return SkillProfile(
            name=skill.name,
            category=skill.category,
            years_experience=skill.years_experience,
            confidence_level=skill.confidence_level,
        )

    def _build_certificate(self, certificate: Certificate) -> CertificateProfile:
        return CertificateProfile(
            name=certificate.name,
            issuing_organization=certificate.issuing_organization,
            issue_date=certificate.issue_date,
            expiration_date=certificate.expiration_date,
            credential_id=certificate.credential_id,
            credential_url=certificate.credential_url,
        )

    def _build_github(self, repo: GithubRepository) -> GithubProfile:
        return GithubProfile(
            name=repo.name,
            full_name=repo.full_name,
            description=repo.description,
            url=repo.url,
            stars=repo.stars,
            forks=repo.forks,
            primary_language=repo.primary_language,
            topics=list(repo.topics or []),
            is_featured=repo.is_featured,
            last_synced_at=repo.last_synced_at,
        )

    def _build_preferences(self, raw: RawProfileData) -> PreferenceProfile:
        jobs = [raw.jobs_by_id[a.job_id] for a in raw.applications if a.job_id in raw.jobs_by_id]

        employment_types = Counter(j.employment_type for j in jobs if j.employment_type is not None)
        remote_types = Counter(j.remote_type for j in jobs if j.remote_type is not None)
        locations = Counter(j.location for j in jobs if j.location)

        salary_mins = [float(j.salary_min) for j in jobs if j.salary_min is not None]
        salary_maxes = [float(j.salary_max) for j in jobs if j.salary_max is not None]

        application_preference = ApplicationPreference(
            total_applications=len(raw.applications),
            total_resume_versions=raw.total_resume_versions,
            preferred_employment_types=[t for t, _ in employment_types.most_common()],
            preferred_remote_types=[t for t, _ in remote_types.most_common()],
            preferred_locations=[loc for loc, _ in locations.most_common()],
            observed_salary_min=min(salary_mins) if salary_mins else None,
            observed_salary_max=max(salary_maxes) if salary_maxes else None,
        )

        interview_types = Counter(i.interview_type for i in raw.interviews)
        durations = [i.duration_minutes for i in raw.interviews if i.duration_minutes is not None]

        interview_preference = InterviewPreference(
            total_interviews=len(raw.interviews),
            preferred_interview_types=[t for t, _ in interview_types.most_common()],
            average_duration_minutes=(sum(durations) / len(durations)) if durations else None,
        )

        return PreferenceProfile(application=application_preference, interview=interview_preference)

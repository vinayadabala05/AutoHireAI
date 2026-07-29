"""Turns a `ResumeBlueprint` + `CareerProfile` into a `ResumeDocument`.

This is the only module in `app/resume/` that talks to `LLMService`
(Sprint 4) — every other module here is a pure transform. Two sections get
an LLM enhancement pass (`Summary`, via `prompts/resume/summary_rewrite.txt`,
and each `Experience` achievement, via `prompts/resume/bullet_point_rewrite.txt`)
because those are the only existing Sprint 4 resume prompts; every other
section (`Skills`, `Projects`, `Education`, `Certificates`) is built
deterministically straight from `CareerProfile` data, ranked/filtered by the
`ResumeBlueprint`, so resume generation stays testable and reproducible
without mocking the LLM for the whole document.
"""

from datetime import UTC, date, datetime

from app.career_profile.models import (
    CareerProfile,
    CertificateProfile,
    EducationProfile,
    ExperienceProfile,
    ProjectProfile,
    SkillProfile,
)
from app.intelligence.models import ResumeBlueprint
from app.llm.models import LLMRequest
from app.llm.service import LLMService
from app.resume.models import ResumeDocument, ResumeSection, ResumeSectionType, ResumeTemplate
from app.resume.templates import resolve_section_order


def _format_date_range(start: date | None, end: date | None, is_current: bool) -> str:
    start_label = start.strftime("%b %Y") if start else "—"
    end_label = "Present" if is_current or end is None else end.strftime("%b %Y")
    return f"{start_label} – {end_label}"


def _contact_line(profile: CareerProfile) -> str:
    info = profile.personal_info
    parts = [info.email]
    if info.phone:
        parts.append(info.phone)
    if info.location:
        parts.append(info.location)
    if info.linkedin_url:
        parts.append(info.linkedin_url)
    if info.portfolio_url:
        parts.append(info.portfolio_url)
    return " | ".join(parts)


def _rank_projects(profile: CareerProfile, blueprint: ResumeBlueprint) -> list[ProjectProfile]:
    by_name = {project.name.strip().lower(): project for project in profile.projects}
    ranked: list[ProjectProfile] = []
    seen: set[str] = set()
    for ranking in sorted(blueprint.recommended_projects, key=lambda r: r.confidence, reverse=True):
        key = ranking.name.strip().lower()
        project = by_name.get(key)
        if project is not None and key not in seen:
            ranked.append(project)
            seen.add(key)
    _priority_rank = {"featured": 0, "high": 1, "medium": 2, "low": 3}
    for project in sorted(profile.projects, key=lambda p: _priority_rank.get(str(p.priority), 2)):
        key = project.name.strip().lower()
        if key not in seen:
            ranked.append(project)
            seen.add(key)
    return ranked


def _skills_content(profile: CareerProfile, blueprint: ResumeBlueprint) -> str:
    if not profile.skills:
        return "_No skills on file._"
    recommended = {name.strip().lower() for name in blueprint.recommended_skills}
    by_category: dict[str, list[SkillProfile]] = {}
    for skill in profile.skills:
        by_category.setdefault(str(skill.category), []).append(skill)
    lines = []
    for category in sorted(by_category):
        skills = sorted(
            by_category[category],
            key=lambda s: s.name.strip().lower() not in recommended,
        )
        names = ", ".join(skill.name for skill in skills)
        label = category.replace("_", " ").title()
        lines.append(f"- **{label}:** {names}")
    return "\n".join(lines)


def _project_block(project: ProjectProfile) -> str:
    lines = [f"### {project.name}"]
    if project.description:
        lines.append(project.description)
    if project.technologies:
        lines.append(f"**Technologies:** {', '.join(project.technologies)}")
    for achievement in project.achievements:
        lines.append(f"- {achievement}")
    return "\n".join(lines)


def _projects_content(profile: CareerProfile, blueprint: ResumeBlueprint) -> str:
    ranked = _rank_projects(profile, blueprint)
    if not ranked:
        return "_No projects on file._"
    return "\n\n".join(_project_block(project) for project in ranked)


def _experience_block(experience: ExperienceProfile, achievements: list[str]) -> str:
    lines = [f"### {experience.title} — {experience.company_name}"]
    location = f"{experience.location} | " if experience.location else ""
    date_range = _format_date_range(
        experience.start_date, experience.end_date, experience.is_current
    )
    lines.append(f"{location}{date_range}")
    if experience.description:
        lines.append(experience.description)
    for achievement in achievements:
        lines.append(f"- {achievement}")
    return "\n".join(lines)


def _education_block(education: EducationProfile) -> str:
    lines = (
        [f"### {education.degree} in {education.field_of_study}"]
        if education.field_of_study
        else [f"### {education.degree}"]
    )
    date_range = _format_date_range(education.start_date, education.end_date, education.is_current)
    lines.append(f"{education.institution} | {date_range}")
    if education.gpa is not None:
        lines.append(f"GPA: {education.gpa:.2f}")
    if education.description:
        lines.append(education.description)
    return "\n".join(lines)


def _education_content(profile: CareerProfile) -> str:
    if not profile.education:
        return "_No education on file._"
    ordered = sorted(
        profile.education,
        key=lambda e: (e.is_current, e.end_date or date.min, e.start_date or date.min),
        reverse=True,
    )
    return "\n\n".join(_education_block(education) for education in ordered)


def _certificate_line(certificate: CertificateProfile) -> str:
    issued = f" ({certificate.issue_date.strftime('%b %Y')})" if certificate.issue_date else ""
    return f"- {certificate.name} — {certificate.issuing_organization}{issued}"


def _certificates_content(profile: CareerProfile) -> str:
    if not profile.certificates:
        return "_No certificates on file._"
    return "\n".join(_certificate_line(certificate) for certificate in profile.certificates)


class ResumeGenerator:
    """Async pipeline turning (blueprint, profile) into a `ResumeDocument`."""

    def __init__(self, llm_service: LLMService) -> None:
        self._llm = llm_service

    async def generate(
        self,
        blueprint: ResumeBlueprint,
        profile: CareerProfile,
        template: ResumeTemplate = ResumeTemplate.SOFTWARE_ENGINEER,
        job_title: str | None = None,
        job_description: str = "",
        enhance_with_llm: bool = True,
    ) -> ResumeDocument:
        order = resolve_section_order(template, blueprint.resume_sections)
        sections: list[ResumeSection] = []
        for index, section_type in enumerate(order):
            content = await self._build_section(
                section_type, blueprint, profile, job_title, job_description, enhance_with_llm
            )
            sections.append(
                ResumeSection(
                    section_type=section_type,
                    title=section_type.value,
                    content=content,
                    order=index,
                )
            )
        return ResumeDocument(
            full_name=profile.personal_info.full_name,
            headline=profile.personal_info.headline,
            contact_line=_contact_line(profile),
            template=template,
            job_title=job_title,
            match_score=blueprint.match_score,
            sections=sections,
            generated_at=datetime.now(UTC),
            metadata={"reasoning": blueprint.reasoning},
        )

    async def _build_section(
        self,
        section_type: ResumeSectionType,
        blueprint: ResumeBlueprint,
        profile: CareerProfile,
        job_title: str | None,
        job_description: str,
        enhance_with_llm: bool,
    ) -> str:
        if section_type is ResumeSectionType.SUMMARY:
            return await self._summary_content(
                profile, job_title, job_description, enhance_with_llm
            )
        if section_type is ResumeSectionType.SKILLS:
            return _skills_content(profile, blueprint)
        if section_type is ResumeSectionType.PROJECTS:
            return _projects_content(profile, blueprint)
        if section_type is ResumeSectionType.EXPERIENCE:
            return await self._experience_content(profile, blueprint, enhance_with_llm)
        if section_type is ResumeSectionType.EDUCATION:
            return _education_content(profile)
        return _certificates_content(profile)

    async def _summary_content(
        self,
        profile: CareerProfile,
        job_title: str | None,
        job_description: str,
        enhance_with_llm: bool,
    ) -> str:
        current_summary = profile.personal_info.summary or ""
        if not enhance_with_llm or not job_title:
            return current_summary or "_No summary on file._"
        prompt_text = self._llm.render_prompt(
            "resume",
            "summary_rewrite",
            {
                "full_name": profile.personal_info.full_name,
                "job_title": job_title,
                "current_summary": current_summary,
                "job_description": job_description,
            },
        )
        response = await self._llm.generate(LLMRequest(prompt=prompt_text))
        return response.content.strip()

    async def _experience_content(
        self, profile: CareerProfile, blueprint: ResumeBlueprint, enhance_with_llm: bool
    ) -> str:
        if not profile.experience:
            return "_No experience on file._"
        ordered = sorted(
            profile.experience,
            key=lambda e: (e.is_current, e.end_date or date.min, e.start_date),
            reverse=True,
        )
        blocks = []
        for experience in ordered:
            achievements = experience.achievements
            if enhance_with_llm and achievements:
                achievements = [
                    await self._rewrite_bullet(profile, bullet, blueprint.recommended_skills)
                    for bullet in achievements
                ]
            blocks.append(_experience_block(experience, achievements))
        return "\n\n".join(blocks)

    async def _rewrite_bullet(
        self, profile: CareerProfile, original_bullet: str, target_keywords: list[str]
    ) -> str:
        prompt_text = self._llm.render_prompt(
            "resume",
            "bullet_point_rewrite",
            {
                "full_name": profile.personal_info.full_name,
                "original_bullet": original_bullet,
                "target_keywords": ", ".join(target_keywords) if target_keywords else "N/A",
            },
        )
        response = await self._llm.generate(LLMRequest(prompt=prompt_text))
        return response.content.strip()

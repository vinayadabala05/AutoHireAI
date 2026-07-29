"""Enums shared across the Career Intelligence data layer.

Each is a `StrEnum` so it serializes cleanly to/from JSON and stores as a
native Postgres `ENUM` type via SQLAlchemy without a separate lookup table.
"""

from enum import StrEnum


class EmploymentType(StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    FREELANCE = "freelance"
    TEMPORARY = "temporary"


class RemoteType(StrEnum):
    ONSITE = "onsite"
    REMOTE = "remote"
    HYBRID = "hybrid"


class ExperienceLevel(StrEnum):
    INTERN = "intern"
    ENTRY = "entry"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    PRINCIPAL = "principal"
    EXECUTIVE = "executive"


class JobSource(StrEnum):
    LINKEDIN = "linkedin"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"
    COMPANY_SITE = "company_site"
    REFERRAL = "referral"
    MANUAL = "manual"
    OTHER = "other"


class ResumeStatus(StrEnum):
    DRAFT = "draft"
    GENERATED = "generated"
    REVIEWED = "reviewed"
    FINAL = "final"
    ARCHIVED = "archived"


class SkillCategory(StrEnum):
    LANGUAGE = "language"
    FRAMEWORK = "framework"
    LIBRARY = "library"
    DATABASE = "database"
    CLOUD = "cloud"
    DEVOPS_TOOL = "devops_tool"
    SOFT_SKILL = "soft_skill"
    OTHER = "other"


class ProjectPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    FEATURED = "featured"


class ApplicationStatus(StrEnum):
    APPLIED = "applied"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    OFFER = "offer"
    WITHDRAWN = "withdrawn"
    ACCEPTED = "accepted"


class ApplicationEventType(StrEnum):
    STATUS_CHANGE = "status_change"
    NOTE_ADDED = "note_added"
    EMAIL_RECEIVED = "email_received"
    EMAIL_SENT = "email_sent"
    FOLLOW_UP = "follow_up"
    REMINDER = "reminder"


class InterviewType(StrEnum):
    PHONE_SCREEN = "phone_screen"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    SYSTEM_DESIGN = "system_design"
    ONSITE = "onsite"
    HR = "hr"
    FINAL = "final"


class InterviewStatus(StrEnum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"
    NO_SHOW = "no_show"


class NotificationType(StrEnum):
    APPLICATION_UPDATE = "application_update"
    INTERVIEW_REMINDER = "interview_reminder"
    JOB_MATCH = "job_match"
    RESUME_READY = "resume_ready"
    SYSTEM = "system"


class NotificationChannel(StrEnum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class ActivityAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    GENERATE = "generate"
    EXPORT = "export"
    OTHER = "other"

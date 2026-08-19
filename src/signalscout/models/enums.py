from enum import Enum


class SignalType(str, Enum):
    HIRING = "Hiring"
    AI_ADOPTION = "AI Adoption"
    EXPANSION = "Expansion"
    PRODUCT_LAUNCH = "Product Launch"
    TECHNOLOGY_CHANGE = "Technology Change"
    PARTNERSHIP = "Partnership"
    UNKNOWN = "Unknown"


class Confidence(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class Qualification(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class ScanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class FetchMethod(str, Enum):
    HTTPX = "httpx"
    PLAYWRIGHT = "playwright"


class ReviewStatus(str, Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    NEEDS_REVIEW = "Needs Review"


class PageType(str, Enum):
    HOMEPAGE = "homepage"
    ABOUT = "about"
    PRODUCT = "product"
    CAREERS = "careers"
    NEWS = "news"

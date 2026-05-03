import enum


class IdentityProvider(enum.StrEnum):
    password = "password"
    wechat_mini_program = "wechat_mini_program"
    phone = "phone"


class ClientType(enum.StrEnum):
    web = "web"
    wechat_mini_program = "wechat_mini_program"
    admin = "admin"


class FileStatus(enum.StrEnum):
    pending = "pending"
    parsed = "parsed"
    failed = "failed"
    classifying = "classifying"
    chunking = "chunking"
    embedding = "embedding"
    ready = "ready"


class PaperStatus(enum.StrEnum):
    pending = "pending"
    generating = "generating"
    completed = "completed"
    failed = "failed"
    timeout = "timeout"

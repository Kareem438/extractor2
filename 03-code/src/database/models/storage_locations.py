"""
Storage Locations Model

Tracks storage location history and current active location.
"""

from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, func, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class StorageLocation(Base):
    """
    Storage locations history table.

    Tracks all storage locations used by the application,
    with one marked as active at any time.
    """
    __tablename__ = "storage_locations"

    location_id = Column(Integer, primary_key=True, autoincrement=True)
    path = Column(String(500), nullable=False, unique=True)
    is_active = Column(Boolean, nullable=False, default=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    notes = Column(Text, nullable=True)

    def __repr__(self):
        active = "ACTIVE" if self.is_active else "inactive"
        return f"<StorageLocation(id={self.location_id}, path='{self.path}', {active})>"

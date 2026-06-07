from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from .db import Base

class Workload(Base):
    __tablename__ = "workloads"

    id = Column(Integer, primary_key=True, index=True)
    namespace = Column(String, index=True)
    name = Column(String, index=True)
    kind = Column(String, index=True)
    desired_replicas = Column(Integer, default=0)
    available_replicas = Column(Integer, default=0)
    labels = Column(JSON, default={})
    annotations = Column(JSON, default={})
    last_observed = Column(DateTime, default=datetime.utcnow)

    containers = relationship("WorkloadImage", back_populates="workload", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint('namespace', 'name', 'kind', name='_workload_uc'),)

class WorkloadImage(Base):
    __tablename__ = "containers"

    id = Column(Integer, primary_key=True, index=True)
    workload_id = Column(Integer, ForeignKey("workloads.id"))
    name = Column(String)
    image_full = Column(String)
    image_repository = Column(String)
    image_tag = Column(String)
    
    # Freshness info
    current_tag = Column(String)
    latest_tag = Column(String)
    freshness_status = Column(String, default="unknown")
    freshness_reason = Column(String)
    checked_at = Column(DateTime)

    # Vulnerability info
    critical_cve = Column(Integer, default=0)
    high_cve = Column(Integer, default=0)
    medium_cve = Column(Integer, default=0)
    low_cve = Column(Integer, default=0)
    unknown_cve = Column(Integer, default=0)
    vulnerability_report_name = Column(String)

    workload = relationship("Workload", back_populates="containers")

class RegistryCache(Base):
    __tablename__ = "registry_cache"

    id = Column(Integer, primary_key=True, index=True)
    image_repository = Column(String, unique=True, index=True)
    tags_json = Column(JSON)
    latest_tag = Column(String)
    last_updated = Column(DateTime, default=datetime.utcnow)

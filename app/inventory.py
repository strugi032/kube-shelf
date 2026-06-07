import logging
from typing import List, Tuple
from .k8s_client import get_k8s_client
from .schemas import WorkloadCreate, WorkloadImageCreate
from .models import Workload, WorkloadImage
from .db import SessionLocal
from datetime import datetime
from sqlalchemy import delete

logger = logging.getLogger(__name__)

def parse_image(image_full: str) -> Tuple[str, str, str]:
    if "@sha256:" in image_full:
        repo, digest = image_full.split("@", 1)
        return repo, digest, image_full
    
    if ":" in image_full:
        parts = image_full.rsplit(":", 1)
        repo = parts[0]
        tag = parts[1]
        if "/" not in tag:
            return repo, tag, image_full
    
    return image_full, "latest", f"{image_full}:latest"

def collect_inventory():
    clients = get_k8s_client()
    workloads: List[WorkloadCreate] = []

    # Lists basic workload types from the cluster
    deps = clients["apps_v1"].list_deployment_for_all_namespaces()
    for item in deps.items:
        workloads.append(_normalize_workload(item, "Deployment"))

    stss = clients["apps_v1"].list_stateful_set_for_all_namespaces()
    for item in stss.items:
        workloads.append(_normalize_workload(item, "StatefulSet"))

    dss = clients["apps_v1"].list_daemon_set_for_all_namespaces()
    for item in dss.items:
        workloads.append(_normalize_workload(item, "DaemonSet"))

    cjs = clients["batch_v1"].list_cron_job_for_all_namespaces()
    for item in cjs.items:
        workloads.append(_normalize_workload(item, "CronJob"))

    _save_inventory(workloads)
    return workloads

def _normalize_workload(item, kind: str) -> WorkloadCreate:
    namespace = item.metadata.namespace
    name = item.metadata.name
    
    desired = 0
    available = 0
    
    if kind == "Deployment":
        desired = item.spec.replicas or 0
        available = item.status.available_replicas or 0
        pod_template = item.spec.template
    elif kind == "StatefulSet":
        desired = item.spec.replicas or 0
        available = item.status.ready_replicas or 0
        pod_template = item.spec.template
    elif kind == "DaemonSet":
        desired = item.status.desired_number_scheduled or 0
        available = item.status.number_ready or 0
        pod_template = item.spec.template
    elif kind == "CronJob":
        desired = 1
        available = 1 if item.status.active else 0
        pod_template = item.spec.job_template.spec.template
    else:
        pod_template = None

    containers = []
    if pod_template:
        for c in pod_template.spec.containers:
            repo, tag, full = parse_image(c.image)
            containers.append(WorkloadImageCreate(
                name=c.name,
                image_full=c.image,
                image_repository=repo,
                image_tag=tag,
                current_tag=tag
            ))

    return WorkloadCreate(
        namespace=namespace,
        name=name,
        kind=kind,
        desired_replicas=desired,
        available_replicas=available,
        labels=item.metadata.labels or {},
        annotations=item.metadata.annotations or {},
        containers=containers
    )

def _save_inventory(workloads: List[WorkloadCreate]):
    db = SessionLocal()
    try:
        for w_data in workloads:
            existing_w = db.query(Workload).filter_by(
                namespace=w_data.namespace, 
                name=w_data.name, 
                kind=w_data.kind
            ).first()
            
            if existing_w:
                existing_w.desired_replicas = w_data.desired_replicas
                existing_w.available_replicas = w_data.available_replicas
                existing_w.labels = w_data.labels
                existing_w.annotations = w_data.annotations
                existing_w.last_observed = datetime.utcnow()
                
                existing_containers = {c.name: c for c in existing_w.containers}
                new_container_names = {c.name for c in w_data.containers}
                
                for c_name in list(existing_containers.keys()):
                    if c_name not in new_container_names:
                        db.delete(existing_containers[c_name])
                
                for c_data in w_data.containers:
                    if c_data.name in existing_containers:
                        c = existing_containers[c_data.name]
                        if c.image_full != c_data.image_full:
                            c.image_full = c_data.image_full
                            c.image_repository = c_data.image_repository
                            c.image_tag = c_data.image_tag
                            c.current_tag = c_data.image_tag
                            c.freshness_status = "unknown"
                    else:
                        new_c = WorkloadImage(**c_data.model_dump())
                        new_c.workload = existing_w
                        db.add(new_c)
            else:
                new_w = Workload(
                    namespace=w_data.namespace,
                    name=w_data.name,
                    kind=w_data.kind,
                    desired_replicas=w_data.desired_replicas,
                    available_replicas=w_data.available_replicas,
                    labels=w_data.labels,
                    annotations=w_data.annotations
                )
                db.add(new_w)
                db.flush()
                for c_data in w_data.containers:
                    new_c = WorkloadImage(**c_data.model_dump())
                    new_c.workload_id = new_w.id
                    db.add(new_c)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to save inventory: {e}")
    finally:
        db.close()

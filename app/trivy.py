import logging
from .k8s_client import get_k8s_client
from .models import Container
from .db import SessionLocal

logger = logging.getLogger(__name__)

def collect_vulnerabilities():
    clients = get_k8s_client()
    try:
        reports = clients["custom_objects"].list_cluster_custom_object(
            group="aquasecurity.github.io",
            version="v1alpha1",
            plural="vulnerabilityreports"
        )
    except Exception as e:
        logger.info("Trivy Operator VulnerabilityReports not found or not accessible")
        return

    db = SessionLocal()
    try:
        # Reset CVE info for all containers first? 
        # Or only those we find reports for.
        # Let's update containers based on reports.
        
        for report in reports.get("items", []):
            labels = report["metadata"].get("labels", {})
            namespace = report["metadata"].get("namespace")
            
            # Trivy Operator labels:
            # trivy-operator.container.name
            # trivy-operator.resource.kind
            # trivy-operator.resource.name
            # trivy-operator.resource.namespace
            
            container_name = labels.get("trivy-operator.container.name")
            resource_kind = labels.get("trivy-operator.resource.kind")
            resource_name = labels.get("trivy-operator.resource.name")
            
            if not (container_name and resource_kind and resource_name):
                continue
            
            summary = report.get("report", {}).get("summary", {})
            
            # Find matching container in our DB
            container = db.query(Container).join(Container.workload).filter(
                Container.name == container_name,
                Container.workload.has(
                    name=resource_name,
                    kind=resource_kind,
                    namespace=namespace
                )
            ).first()
            
            if container:
                container.critical_cve = summary.get("criticalCount", 0)
                container.high_cve = summary.get("highCount", 0)
                container.medium_cve = summary.get("mediumCount", 0)
                container.low_cve = summary.get("lowCount", 0)
                container.unknown_cve = summary.get("unknownCount", 0)
                container.vulnerability_report_name = report["metadata"]["name"]
        
        db.commit()
    except Exception as e:
        logger.error(f"Failed to save vulnerability reports: {e}")
        db.rollback()
    finally:
        db.close()

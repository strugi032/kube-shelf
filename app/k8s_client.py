from kubernetes import client, config
import logging
from .config import settings

logger = logging.getLogger(__name__)

def get_k8s_client():
    try:
        # Check if running in cluster
        config.load_incluster_config()
        logger.info("Loaded in-cluster K8s config")
    except config.ConfigException:
        # Fallback to local kubeconfig if allowed
        if settings.KUBE_IMAGE_INVENTORY_DEV_KUBECONFIG:
            config.load_kube_config()
            logger.info("Loaded local K8s config")
        else:
            logger.error("Could not load K8s config and KUBE_IMAGE_INVENTORY_DEV_KUBECONFIG is False")
            raise Exception("Kubernetes configuration not found")

    return {
        "apps_v1": client.AppsV1Api(),
        "core_v1": client.CoreV1Api(),
        "batch_v1": client.BatchV1Api(),
        "custom_objects": client.CustomObjectsApi(),
    }

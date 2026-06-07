from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "Kubernetes Image Inventory"
    DATABASE_URL: str = "sqlite:///./inventory.db"
    
    # K8s
    KUBE_IMAGE_INVENTORY_DEV_KUBECONFIG: bool = False
    
    # Scan
    SCAN_INTERVAL_SECONDS: int = 900
    
    class Config:
        env_file = ".env"

settings = Settings()

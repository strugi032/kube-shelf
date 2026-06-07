# Sample Inventory Output

| Namespace | Workload | Kind | Image | Status | CVEs (C/H) |
|-----------|----------|------|-------|--------|------------|
| default | frontend | Deployment | nginx:1.25.1 | Outdated (1.27.1) | 0 / 2 |
| auth | redis | StatefulSet | redis:7.2.4 | Current | 0 / 0 |
| kube-system | coredns | Deployment | coredns:v1.10.1 | Current | 1 / 5 |

.PHONY: install test lint run build deploy undeploy port-forward

install:
	pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check .

run:
	KUBE_IMAGE_INVENTORY_DEV_KUBECONFIG=true uvicorn app.main:app --reload

build:
	docker build -t kube-image-inventory .

deploy:
	kubectl apply -k deploy/kubernetes/base

undeploy:
	kubectl delete -k deploy/kubernetes/base

port-forward:
	kubectl port-forward -n kube-image-inventory svc/kube-image-inventory 8000:80

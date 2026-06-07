from app.inventory import parse_image

def test_parse_dockerhub_image():
    repo, tag, full = parse_image("nginx:1.27.1")
    assert repo == "nginx"
    assert tag == "1.27.1"
    assert full == "nginx:1.27.1"

def test_parse_ghcr_image():
    repo, tag, full = parse_image("ghcr.io/strugi/kube-image-inventory:v0.1.0")
    assert repo == "ghcr.io/strugi/kube-image-inventory"
    assert tag == "v0.1.0"

def test_parse_defaults_to_latest():
    repo, tag, full = parse_image("redis")
    assert repo == "redis"
    assert tag == "latest"

def test_parse_digest_image():
    repo, tag, full = parse_image("repo/app@sha256:abcdef123456")
    assert repo == "repo/app"
    assert tag == "sha256:abcdef123456"

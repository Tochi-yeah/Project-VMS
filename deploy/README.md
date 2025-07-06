# Docker Deployment for VMS with libzbar Support

This folder contains the Dockerfile and startup script for deploying the VMS application with required `libzbar` shared library support, resolving `ImportError: Unable to find zbar shared library`.

## 📦 Build and Run Locally

```bash
docker build -t vms-app -f deploy/Dockerfile .
docker run --rm -p 5000:5000 vms-app

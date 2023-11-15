fastpub:
	docker buildx build --build-arg GoArch="amd64" --platform=linux/amd64 -t \
	talkincode/gptservice:latest .
	docker push talkincode/gptservice:latest

arm64:
	docker buildx build --build-arg GoArch="arm64" --platform=linux/arm64 -t \
	talkincode/gptservice:latest-arm64 .
	docker push talkincode/gptservice:latest-arm64


.PHONY: clean build

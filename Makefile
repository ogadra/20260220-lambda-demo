.PHONY: init lint tflint checkov

init:
	direnv allow

lint:
	-$(MAKE) tflint
	-$(MAKE) checkov

tflint:
	tflint --recursive

checkov:
	checkov -d ./vpc-lambda-eip-demo
	checkov -d ./slidev/terraform

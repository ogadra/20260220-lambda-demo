.PHONY: init lint tflint checkov

init:
	direnv allow

lint:
	-$(MAKE) tflint
	-$(MAKE) checkov

tflint:
	tflint --recursive

checkov:
	checkov -d . --framework terraform --compact --quiet

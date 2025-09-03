all: test-plan-coverage-report.txt

test-plan-coverage-report.txt: covered-test-plan-ids.txt spec/Overview.html
	python3 check_coverage.py spec/Overview.html covered-test-plan-ids.txt > test-plan-coverage-report.txt

covered-test-plan-ids.txt: test-plan.md
	grep "## Test ID:" test-plan.md | awk '{print $$4}' > covered-test-plan-ids.txt

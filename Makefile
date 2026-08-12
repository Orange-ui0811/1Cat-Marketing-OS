.PHONY: doctor init up down status logs smoke test package

doctor:
	./bin/1cat doctor

init:
	./bin/1cat init

up:
	./bin/1cat up

down:
	./bin/1cat down

status:
	./bin/1cat status

logs:
	./bin/1cat logs

smoke:
	./bin/1cat smoke

test:
	./scripts/test.sh

package:
	./bin/1cat package all


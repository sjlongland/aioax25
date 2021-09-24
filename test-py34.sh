#!/bin/bash

: ${IMAGE:=python:3.4}
: ${MY_DIR:="$( realpath "$( dirname "$0" )" )"}

set -ex

if [ -z "${_IN_DOCKER}" ]; then
	: ${DOCKER_ARGS=""}

	if [ -e "$( tty )" ]; then
		DOCKER_ARGS="${DOCKER_ARGS} --tty --interactive"
	fi

	exec docker run --rm \
		--volume "${MY_DIR}:/tmp/$( dirname "${MY_DIR}" )" \
		--env RUN_AS=$( id -u ):$( id -g ) \
		--env _IN_DOCKER=y \
		--name "aioax25-py34test-$$" \
		${DOCKER_ARGS} \
		${IMAGE} \
		/bin/bash "/tmp/$( dirname "${MY_DIR}" )/$( basename "$0" )"
fi

if [ "$( id -u )" = 0 ]; then
	# Running as root
	apt-get update
	apt-get install -y gosu virtualenv

	# Drop privileges
	exec gosu ${RUN_AS} /bin/bash "$0"
fi

cd "${MY_DIR}"

# Set up a virtual environment
virtualenv -p python3.4 /tmp/virtualenv
/tmp/virtualenv/bin/pip install pytest==4.6.11 attrs==20.3.0 pytest-cov
/tmp/virtualenv/bin/pip install -r requirements.txt

# Run tests
/tmp/virtualenv/bin/python3.4 -m pytest \
	--cov=aioax25 \
	--cov-report=term-missing \
	--cov-report=html \
	"$@"

# Use the existing image as the base
FROM quantum-microservice:latest

# Define the path to the default circuit file on the host
ARG DEFAULT_CIRCUIT_FILE=test_circuit.qasm

# Define the target directory inside the container
ARG TARGET_DIR=/microservice/circuits/default

# Create the target directory if it doesn't exist
# The WORKDIR in the base image is /microservice, so paths can be relative
RUN mkdir -p circuits/default

# Copy the specified default circuit file from the build context
# into the target directory inside the container
COPY ${DEFAULT_CIRCUIT_FILE} ${TARGET_DIR}/
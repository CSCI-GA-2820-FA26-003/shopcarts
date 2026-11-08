# Image for a NYU Lab development environment
FROM quay.io/rofrano/pipeline-selenium:sp26

ARG USERNAME=vscode
USER root

# Set up the Python development environment
WORKDIR /app
COPY Pipfile Pipfile.lock ./
RUN pipenv install --system --dev --deploy && python -m pip check

# Configuring insecure Docker registry
COPY config/insecure-registry.json /etc/docker/daemon.json 

# Become a regular user for development
USER $USERNAME

# Install user mode tools
COPY .devcontainer/scripts/install-tools.sh /tmp/
RUN cd /tmp && bash ./install-tools.sh

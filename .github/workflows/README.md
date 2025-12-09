# GitHub Actions Workflows

This directory contains automated workflows for maintaining this repository.

## Workflows

### ci.yml

**Purpose**: Validates code quality before merging or deploying.

**Triggers**:
- Push: When code is pushed to `main` or `feature/**` branches
- Pull Request: When PRs are opened or updated targeting `main`

**Process**:
1. Installs Python 3.11 using `uv`
2. Installs project dependencies
3. Runs linter (`ruff check`)
4. Checks code formatting (`ruff format --check`)
5. Runs test suite (`pytest`)

**Quality Gates**:
- All checks must pass for workflow to succeed
- Prevents merging code with linting errors, formatting issues, or failing tests
- Ensures code quality standards are maintained

### build_and_publish.yml

**Purpose**: Builds and publishes Docker images to Docker Hub.

**Triggers**:
- Manual: Via GitHub Actions UI
- Push: When source files change on main branch (after CI passes)

**Process**:
1. Builds Docker image for multiple platforms (linux/amd64, linux/arm64)
2. Publishes to Docker Hub (private repository)
3. Uses Docker layer caching for faster builds
4. Tags images with version information

**Requirements**:
- `DOCKER_USERNAME`: Docker Hub username (GitHub Secret)
- `DOCKER_PASSWORD`: Docker Hub access token (GitHub Secret)

## Configuration

### Required GitHub Secrets

Set these in your repository settings (Settings → Secrets and variables → Actions):

1. **DOCKER_USERNAME**: Your Docker Hub username
2. **DOCKER_PASSWORD**: Your Docker Hub access token (not your password)

To create a Docker Hub access token:
1. Go to Docker Hub → Account Settings → Security
2. Click "New Access Token"
3. Give it a name (e.g., "GitHub Actions")
4. Copy the token and add it as `DOCKER_PASSWORD` secret

## Troubleshooting

### Docker Build Fails

If Docker build fails:
1. Check Docker Hub credentials are correct
2. Verify Docker Hub repository exists and is accessible
3. Check build logs for specific error messages
4. Test Docker build locally: `docker build -t test .`

## Manual Workflow Triggers

You can manually trigger workflows:
1. Go to Actions tab in GitHub
2. Select the workflow
3. Click "Run workflow"
4. Choose branch and click "Run workflow"

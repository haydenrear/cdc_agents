#!/bin/zsh

echo "hello"


docker rm mcp/cdc_agents_test || true
docker rm mcp/cdc_agents || true
docker rm a2a/cdc_agents || true

docker rm cdc_agents_test || true
docker rm mcp_cdc_agents || true
docker rm a2a_cdc_agents || true

#docker build . -f Dockerfile_base -t cdc_agents_base
docker build . -f Dockerfile_testmcp -t mcp/cdc_agents_test
docker build . -f Dockerfile_mcp -t mcp/cdc_agents
docker build . -f Dockerfile_a2a -t a2a/cdc_agents

docker run -v '/Users/hayde/IdeaProjects/python_parent:/home/python_parent/sources' -v 'environment:/home/python_parent/sources/.venv' -v '/var/run/docker.sock:/var/run/docker.sock' -v '/Users/hayde/IdeaProjects/python_parent/packages/cdc_agents/docker.env:/home/python_parent/sources/packages/cdc_agents/.env'  --name cdc_agents_test mcp/cdc_agents_test
#docker run -v '/Users/hayde/IdeaProjects/python_parent:/home/python_parent/sources' -v 'environment:/home/python_parent/sources/.venv' -v '/var/run/docker.sock:/var/run/docker.sock' -v '/Users/hayde/IdeaProjects/python_parent/packages/cdc_agents/docker.env:/home/python_parent/sources/packages/cdc_agents/.env' --name cdc_agents_test  --rm --entrypoint sleep mcp/cdc_agents_test '999999'

#/Users/hayde/.cargo/bin/docker run -i -v /Users/hayde/IdeaProjects/python_parent:/home/python_parent/sources -v environment:/home/python_parent/sources/.venv -v /var/run/docker.sock:/var/run/docker.sock -v /Users/hayde/IdeaProjects/python_parent/packages/cdc_agents/docker.env:/home/python_parent/sources/packages/cdc_agents/.env mcp/cdc_agents

#docker run -v '/Users/hayde/IdeaProjects/python_parent:/home/python_parent/sources' -v 'environment:/home/python_parent/sources/.venv' -v '/var/run/docker.sock:/var/run/docker.sock' -v '/Users/hayde/IdeaProjects/python_parent/packages/cdc_agents/docker.env:/home/python_parent/sources/packages/cdc_agents/.env'  --name mcp_cdc_agents mcp/cdc_agents
#docker run -v '/Users/hayde/IdeaProjects/python_parent:/home/python_parent/sources' -v 'environment:/home/python_parent/sources/.venv' -v '/var/run/docker.sock:/var/run/docker.sock' -v '/Users/hayde/IdeaProjects/python_parent/packages/cdc_agents/docker.env:/home/python_parent/sources/packages/cdc_agents/.env'  --rm --entrypoint sleep mcp/cdc_agents_test '999999'

#docker run -v '/Users/hayde/IdeaProjects/python_parent:/home/python_parent/sources' -v 'environment:/home/python_parent/sources/.venv' -v '/var/run/docker.sock:/var/run/docker.sock' -v '/Users/hayde/IdeaProjects/python_parent/packages/cdc_agents/docker.env:/home/python_parent/sources/packages/cdc_agents/.env'  --name a2a_cdc_agents a2a/cdc_agents
#docker run -v '/Users/hayde/IdeaProjects/python_parent:/home/python_parent/sources' -v 'environment:/home/python_parent/sources/.venv' -v '/var/run/docker.sock:/var/run/docker.sock' -v '/Users/hayde/IdeaProjects/python_parent/packages/cdc_agents/docker.env:/home/python_parent/sources/packages/cdc_agents/.env'  --rm --entrypoint sleep mcp/cdc_agents_test '999999'


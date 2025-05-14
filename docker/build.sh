#!/bin/zsh

echo "hello"


rm -rf build/ || true
mkdir -p build/resources || true
cp ../resources/application.yml application-test.yml
#sed -i -e s/{{gemini_api_key}}/"${GEMINI_API_KEY}"/g application.yml

cp ../resources/application.yml application-mcp.yml
sed -i -e s/SKIP/MCP/g application-mcp.yml

cp ../resources/application.yml application-a2a.yml
sed -i -e s/SKIP/A2A/g application-a2a.yml

cp -r ../src ./build/src
cp -r ../test ./build/test
cp ../pyproject.toml ./build
cp ../uv.lock ./build
cp ../.python-version ./build

cp ../docker.env ./build/.env
cp ../requirements.txt ./requirements.txt

docker rm mcp/cdc_agents_test || true
docker rm mcp/cdc_agents || true
docker rm a2a/cdc_agents || true

docker rm cdc_agents_test || true
docker rm mcp_cdc_agents || true
docker rm a2a_cdc_agents || true

docker build . -f Dockerfile_base -t cdc_agents_base
docker build . -f Dockerfile_testmcp -t mcp/cdc_agents_test
docker build . -f Dockerfile_mcp -t mcp/cdc_agents
docker build . -f Dockerfile_a2a -t a2a/cdc_agents

docker run -v '/Users/hayde/IdeaProjects/drools/python_di:/home/cdc_agents/python_di'  -v '/Users/hayde/IdeaProjects/drools/python_util:/home/cdc_agents/python_util' -v '/Users/hayde/IdeaProjects/drools/drools_py:/home/cdc_agents/drools_py' -v '/Users/hayde/IdeaProjects/ml/integrations/aisuite:/home/ml/integrations/aisuite' -v 'environment:/home/cdc_agents/sources/.venv' -v '/var/run/docker.sock:/var/run/docker.sock' -v './application-test.yml:/home/cdc_agents/sources/resources/application.yml'  --name cdc_agents_test mcp/cdc_agents_test
#docker run -v '/Users/hayde/IdeaProjects/drools/python_di:/home/cdc_agents/python_di'  -v '/Users/hayde/IdeaProjects/drools/python_util:/home/cdc_agents/python_util' -v '/Users/hayde/IdeaProjects/drools/drools_py:/home/cdc_agents/drools_py' -v '/Users/hayde/IdeaProjects/ml/integrations/aisuite:/home/ml/integrations/aisuite' -v 'environment:/home/cdc_agents/sources/.venv' -v '/var/run/docker.sock:/var/run/docker.sock'  -v './application-test.yml:/home/cdc_agents/sources/resources/application.yml'  --rm --entrypoint sleep mcp/cdc_agents_test '999999'

#docker run -v '/Users/hayde/IdeaProjects/drools/python_di:/home/cdc_agents/python_di'  -v '/Users/hayde/IdeaProjects/drools/python_util:/home/cdc_agents/python_util' -v '/Users/hayde/IdeaProjects/drools/drools_py:/home/cdc_agents/drools_py' -v '/Users/hayde/IdeaProjects/ml/integrations/aisuite:/home/ml/integrations/aisuite' -v 'environment:/home/cdc_agents/sources/.venv' -v '/var/run/docker.sock:/var/run/docker.sock' -v './application-mcp.yml:/home/cdc_agents/sources/resources/application.yml' --name mcp_cdc_agents mcp/cdc_agents
#docker run -v '/Users/hayde/IdeaProjects/drools/python_di:/home/cdc_agents/python_di'  -v '/Users/hayde/IdeaProjects/drools/python_util:/home/cdc_agents/python_util' -v '/Users/hayde/IdeaProjects/drools/drools_py:/home/cdc_agents/drools_py' -v '/Users/hayde/IdeaProjects/ml/integrations/aisuite:/home/ml/integrations/aisuite' -v 'environment:/home/cdc_agents/sources/.venv' -v '/var/run/docker.sock:/var/run/docker.sock' -v './application-mcp.yml:/home/cdc_agents/sources/resources/application.yml'  --rm --entrypoint sleep mcp/cdc_agents '999999'

#docker run -v '/Users/hayde/IdeaProjects/drools/python_di:/home/cdc_agents/python_di'  -v '/Users/hayde/IdeaProjects/drools/python_util:/home/cdc_agents/python_util' -v '/Users/hayde/IdeaProjects/drools/drools_py:/home/cdc_agents/drools_py' -v '/Users/hayde/IdeaProjects/ml/integrations/aisuite:/home/ml/integrations/aisuite' -v 'environment:/home/cdc_agents/sources/.venv' -v '/var/run/docker.sock:/var/run/docker.sock' -v './application-a2a.yml:/home/cdc_agents/sources/resources/application.yml' --name a2a_cdc_agents a2a/cdc_agents
#docker run -v '/Users/hayde/IdeaProjects/drools/python_di:/home/cdc_agents/python_di'  -v '/Users/hayde/IdeaProjects/drools/python_util:/home/cdc_agents/python_util' -v '/Users/hayde/IdeaProjects/drools/drools_py:/home/cdc_agents/drools_py' -v '/Users/hayde/IdeaProjects/ml/integrations/aisuite:/home/ml/integrations/aisuite' -v 'environment:/home/cdc_agents/sources/.venv' -v '/var/run/docker.sock:/var/run/docker.sock'  -v './application-a2a.yml:/home/cdc_agents/sources/resources/application.yml'  --rm --entrypoint sleep a2a/cdc_agents '999999'

rm -rf build/ || true
rm *.yml || true
rm *.yml-e || true
rm requirements.txt

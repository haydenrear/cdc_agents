#!/bin/zsh

echo "hello"


rm -rf build/ || true
mkdir -p build/resources || true
cp ../resources/application.yml build/application-docker.yml
cp ../resources/application-test.yml build/application-test.yml
#sed -i -e s/{{gemini_api_key}}/"${GEMINI_API_KEY}"/g build/application-docker.yml

cp -r ../src ./build/src
cp -r ../test ./build/test
cp ../pyproject.toml ./build
cp ../uv.lock ./build
cp ../.python-version ./build

cp build/application-docker.yml ./build/resources/application.yml
cp build/application-test.yml ./build/resources/application-test.yml
cp ../docker.env ./build/.env
cp ../requirements.txt ./requirements.txt

docker rm mcp/cdc_agents_test || true

docker build . -f Dockerfile_testmcp -t mcp/cdc_agents_test

docker run -v '/Users/hayde/IdeaProjects/drools/python_di:/home/cdc_agents/python_di'  -v '/Users/hayde/IdeaProjects/drools/python_util:/home/cdc_agents/python_util' -v '/Users/hayde/IdeaProjects/drools/drools_py:/home/cdc_agents/drools_py' -v '/Users/hayde/IdeaProjects/ml/integrations/aisuite:/home/ml/integrations/aisuite' -v 'environment:/home/cdc_agents/sources/.venv' -v '/var/run/docker.sock:/var/run/docker.sock' --name cdc_agents_test mcp/cdc_agents_test
#docker run -v '/Users/hayde/IdeaProjects/drools/python_di:/home/cdc_agents/python_di'  -v '/Users/hayde/IdeaProjects/drools/python_util:/home/cdc_agents/python_util' -v '/Users/hayde/IdeaProjects/drools/drools_py:/home/cdc_agents/drools_py' -v '/Users/hayde/IdeaProjects/ml/integrations/aisuite:/home/ml/integrations/aisuite' -v 'environment:/home/cdc_agents/sources/.venv' -v '/var/run/docker.sock:/var/run/docker.sock'  --rm --entrypoint sleep mcp/cdc_agents_test '999999'

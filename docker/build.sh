#!/bin/zsh

echo "hello"

cp application-docker-template.yml application-docker.yml

sed -i -e s/{{gemini_api_key}}/"${GEMINI_API_KEY}"/g application-docker.yml

cp -r ../../drools_py/src/drools_py ./drools_py_copied
cp -r ../../python_di/src/python_di ./python_di_copied
cp -r ../../python_util/src/python_util ./python_util_copied
cp -r ../../data/metadata_extractor/src ./metadata_extractor_copied
cp -r ../aisuite ./aisuite_copied
mkdir -p src/model_server || true
cp -r ../src/model_server ./src/model_server
mkdir resources || true
cp application-docker.yml ./resources/application.yml
cp ../docker.env ./docker.env
cp ../requirements-docker.txt ./requirements.txt
FROM python:3.10
RUN mkdir /model_server_home
RUN cd /model_server_home
WORKDIR /model_server_home
COPY ./requirements.txt /model_server_home/requirements.txt
RUN pip install -r requirements.txt
COPY ./src/model_server /model_server_home/
COPY ./drools_py_copied /model_server_home/drools_py
COPY ./python_di_copied /model_server_home/python_di
COPY ./aisuite_copied /model_server_home/aisuite
COPY ./python_util_copied /model_server_home/python_util
COPY ./metadata_extractor_copied /model_server_home/metadata_extractor
COPY ./pasta/pasta /model_server_home/pasta
COPY ./docker.env ./.env
RUN mkdir ./resources
COPY ./application-docker.yml /model_server_home/resources/application.yml
RUN mkdir /model_server_home/work
RUN mkdir /model_server_home/test_work
RUN cd /model_server_home
COPY ./run.sh ./run.sh
CMD ["/bin/bash", "run.sh"]
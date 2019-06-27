FROM python:latest

COPY ./constraints.txt /restore-keyfile/constraints.txt
COPY ./requirements.txt /restore-keyfile/requirements.txt
COPY ./__init__.py /restore-keyfile/__init__.py
COPY ./restore_keyfile.py /restore-keyfile/restore_keyfile.py
VOLUME /restore-keyfile/output

WORKDIR /restore-keyfile
RUN pip install -r requirements.txt -c constraints.txt

VOLUME /output
CMD ./restore_keyfile.py $PRIV_KEY $PASSWD output/keyfile.json


# docker run --rm -v path_to_existing_dir:/restore-keyfile/output --env PRIV_KEY=priv_key --env PASSWD=password restore-keyfile

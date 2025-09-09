FROM python:3.12

RUN mkdir -p /usr/src/app/
WORKDIR /usr/src/app/
COPY . .

# If extra requirements needed
RUN pip install bmstu_oauth  -i https://public:public@projects.iu5.bmstu.ru/repository/pip_all/simple
RUN pip install -r requirements.txt


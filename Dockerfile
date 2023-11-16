# 使用官方的 Python 基础镜像
FROM condaforge/mambaforge:latest

# 设置工作目录
WORKDIR /

# 将项目文件复制到工作目录
COPY apps /
COPY ./main.py /main.py
COPY ./requirements.txt /app/requirements.txt

# 安装项目依赖
RUN pip install --no-cache-dir -r requirements.txt

# 暴露端口
EXPOSE 8700

# 设置启动命令
CMD ["uvicorn","main:app"]
